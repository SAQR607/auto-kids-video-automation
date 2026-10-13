"""Publishing stages: upload -> verify -> checkpoint -> Telegram (§47-§51).

Stage funcs never transition (pipeline contract). Resume safety:
- youtube_video_id is checkpointed right after upload, BEFORE verification,
  so a crash during YouTube processing resumes at verify-only — never
  double-uploads.
- Shorts iterate per-short with per-short status checkpoints
  (rendered -> uploaded / upload_failed), so a killed runner resumes exactly
  where it stopped (§32).
- Quota errors are raised un-retried (§49/§50); transient errors get bounded
  backoff inside the resumable upload loop.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from ..config import Config
from ..logging_setup import get_logger, redact
from ..retry import backoff_delay
from ..schedule import channel_totals, next_posting
from ..state import Registry, now_iso
from ..telegram_client import format_stats, format_success_long, format_success_shorts
from .errors import QuotaExceeded, UploadFailed, YouTubeError, classify, is_scope_denied
from .metadata import long_body, short_body
from .oauth import build_service

log = get_logger("youtube.publish")

VERIFY_TRIES = 30
VERIFY_DELAY = 10.0
UPLOAD_TRANSIENT_RETRIES = 5


def _upload(service: Any, path: Path, body: dict, *, label: str) -> str:
    """Resumable upload with bounded transient retries; returns video id."""
    from googleapiclient.http import MediaFileUpload

    request = service.videos().insert(
        part="snippet,status,contentDetails",
        body=body,
        media_body=MediaFileUpload(str(path), chunksize=8 * 1024 * 1024, resumable=True),
    )
    attempts = 0
    while True:
        try:
            progress, response = request.next_chunk()
            if progress is not None:
                log.info("%s upload %.0f%%", label, progress.progress() * 100)
                attempts = 0
            if response is not None:
                vid = response.get("id")
                if not vid:
                    raise UploadFailed(f"{label}: upload response has no video id")
                return vid
        except UploadFailed:
            raise
        except Exception as exc:
            kind = classify(exc)
            if kind == "quota":
                raise QuotaExceeded(f"{label}: YouTube quota exhausted — retrying today is pointless: "
                                    f"{redact(str(exc))[:250]}") from exc
            if kind == "transient" and attempts < UPLOAD_TRANSIENT_RETRIES:
                attempts += 1
                delay = backoff_delay(attempts - 1, base=3.0, cap=60.0)
                log.warning("%s transient upload error (attempt %d/%d): %s — retrying in %.1fs",
                            label, attempts, UPLOAD_TRANSIENT_RETRIES, redact(str(exc)), delay)
                time.sleep(delay)
                continue
            raise UploadFailed(f"{label} upload failed: {redact(str(exc))[:300]}") from exc


def _verify(service: Any, video_id: str, *, tries: int = VERIFY_TRIES,
            delay: float = VERIFY_DELAY, sleep=time.sleep) -> dict:
    """Poll until YouTube reports uploadStatus=processed (verify before recorded).

    A grant carrying only youtube.upload can 403 videos.list (403
    insufficientPermissions). The upload itself already succeeded (insert
    returned the id, checkpointed before this call), so that single error is
    tolerated: we log it and return an empty item — callers fall back to the
    configured privacy. Quota and every other error still propagate.
    """
    for attempt in range(tries):
        try:
            resp = service.videos().list(part="status,snippet", id=video_id).execute()
        except Exception as exc:
            if is_scope_denied(exc):
                log.warning("verify skipped for %s: OAuth grant lacks videos.list scope "
                            "(upload already confirmed by insert response)", video_id)
                return {}
            raise
        items = resp.get("items") or []
        if not items:
            raise YouTubeError(f"video {video_id} not found after upload")
        status = items[0].get("status", {})
        if status.get("uploadStatus") == "processed":
            return items[0]
        if status.get("uploadStatus") == "failed":
            raise YouTubeError(f"YouTube processing FAILED for {video_id}: "
                               f"{status.get('failureReason') or status.get('processingFailureReason') or 'unknown'}")
        if attempt < tries - 1:
            sleep(delay)
    raise YouTubeError(f"video {video_id} not processed after {tries} checks ({tries * delay:.0f}s budget)")


def _set_thumbnail(service: Any, video_id: str, thumb: Path) -> None:
    from googleapiclient.http import MediaFileUpload

    try:
        service.thumbnails().set(
            videoId=video_id, media_body=MediaFileUpload(str(thumb))
        ).execute()
    except Exception as exc:
        if "403" in str(exc):
            raise YouTubeError(
                f"thumbnail set 403 for {video_id}: YouTube only allows custom thumbnails on "
                f"a phone-verified channel — verify at https://www.youtube.com/verify, then "
                f"re-run `python -m app youtube-patch --episode <id>` ({redact(str(exc))[:160]})"
            ) from exc
        raise


def _notify(text: str) -> None:
    """Telegram SUCCESS report — must never break the run (§39)."""
    try:
        from .. import telegram_client

        if not telegram_client.send_message(text):
            log.warning("telegram SUCCESS report returned False")
    except Exception as exc:
        log.warning("telegram SUCCESS report failed: %s", redact(str(exc)))


def _package(base: Path, episode_id: str) -> dict:
    pkg_file = base / "package.json"
    if not pkg_file.exists():
        raise YouTubeError(f"package.json missing for {episode_id}")
    return json.loads(pkg_file.read_text(encoding="utf-8"))


def _category(cfg: Config) -> str:
    return str(cfg.get("channel.youtube_category_id")
               or cfg.get("youtube.category_id") or "1")


def publish_long(cfg: Config, reg: Registry, episode_id: str, ctx: dict[str, Any]) -> None:
    """Stage UPLOADING: resumable upload, verify, thumbnail, SUCCESS alert."""
    base = Path(cfg.get("paths.state", "state")) / "episodes" / episode_id
    entry = reg.get(episode_id)

    if entry.get("youtube_video_id") and entry.get("youtube_verified"):
        log.info("%s already published (%s) — nothing to do", episode_id, entry["youtube_video_id"])
        return
    if ctx.get("dry_run"):
        log.warning("%s DRY RUN — publishing skipped; state resumes at publish on the next real run",
                    episode_id)
        return

    video = Path(entry.get("video_path") or "")
    if not entry.get("video_path") or not video.exists():
        raise YouTubeError(f"rendered video missing: {video or '(unset)'}")

    private = bool(ctx.get("private_test"))
    package = _package(base, episode_id)
    body = long_body(package, private=private, category_id=_category(cfg))

    service = build_service()
    vid = entry.get("youtube_video_id")
    if not vid:
        vid = _upload(service, video, body, label=episode_id)
        entry["youtube_video_id"] = vid
        entry["youtube_uploaded_at"] = now_iso()
        reg.save()
        log.info("%s uploaded -> %s (resuming later verifies only)", episode_id, vid)

    item = _verify(service, vid)
    entry["youtube_verified"] = True
    entry["youtube_privacy"] = (item.get("status", {}).get("privacyStatus")
                                or ("private" if private else "public"))

    thumb = Path(entry.get("thumbnail_path") or "")
    if entry.get("thumbnail_path") and thumb.exists():
        try:
            _set_thumbnail(service, vid, thumb)
        except Exception as exc:
            entry["thumbnail_error"] = redact(str(exc))[:200]
            log.warning("%s thumbnail set failed (non-fatal): %s", episode_id, entry["thumbnail_error"])

    entry["published_at"] = now_iso()
    reg.save()

    meta = package.get("metadata", {})
    _notify(format_success_long(
        episode_id,
        str(meta.get("title", package.get("title", ""))),
        vid,
        str(entry["youtube_privacy"]),
        str(entry.get("script_qc", {}).get("status", "?")),
        str(entry.get("video_qc", {}).get("status", "?")),
    ))
    _notify(format_stats(channel_totals(reg), next_posting(cfg, reg)))
    log.info("%s published: %s (%s)", episode_id, vid, entry["youtube_privacy"])


def patch_published(cfg: Config, reg: Registry, episode_id: str) -> list[str]:
    """Fix thumbnail + description on an ALREADY-published video (youtube-patch).

    Re-renders the thumbnail (story-derived concept — packages may lack a
    generated thumbnail_concept), refreshes snippet title/description/tags
    from the QC-passed package, then uploads the thumbnail. The thumbnail is
    the hard requirement; a scope-denied snippet refresh is reported only —
    the live description comes from the same package and stays intact.
    """
    base = Path(cfg.get("paths.state", "state")) / "episodes" / episode_id
    entry = reg.get(episode_id)
    vid = entry.get("youtube_video_id")
    if not vid:
        raise YouTubeError(f"{episode_id} has no uploaded video id — nothing to patch")
    package = _package(base, episode_id)
    service = build_service()
    results: list[str] = []
    failures: list[str] = []

    try:
        body = long_body(package, private=False)
        service.videos().update(part="snippet", body={"id": vid, "snippet": body["snippet"]}).execute()
        results.append("description/title/tags refreshed from package")
    except Exception as exc:
        if is_scope_denied(exc):
            results.append("snippet refresh skipped: grant lacks videos.update scope "
                           "(live description already matches the package)")
            log.warning("%s videos.update scope-denied: %s", episode_id, redact(str(exc))[:160])
        else:
            failures.append(f"videos.update failed: {redact(str(exc))[:200]}")

    from ..render.thumbnail import render_thumbnail

    thumb_dir = Path(cfg.get("paths.workspace", "workspace")) / "thumbnails"
    thumb = render_thumbnail(cfg, package, thumb_dir / f"{episode_id}.jpg")
    entry["thumbnail_path"] = str(thumb)
    reg.save()
    try:
        _set_thumbnail(service, vid, thumb)
        entry.pop("thumbnail_error", None)
        entry["thumbnail_patched_at"] = now_iso()
        results.append(f"thumbnail set: {thumb}")
    except Exception as exc:
        entry["thumbnail_error"] = redact(str(exc))[:200]
        failures.append(f"thumbnail failed: {entry['thumbnail_error']}")
    reg.save()

    if failures:
        raise YouTubeError(f"{episode_id} patch incomplete — " + "; ".join(failures))
    return results


def publish_shorts(cfg: Config, reg: Registry, episode_id: str, ctx: dict[str, Any]) -> None:
    """Stage COMPLETE: upload every pending short with per-short checkpoints."""
    base = Path(cfg.get("paths.state", "state")) / "episodes" / episode_id
    entry = reg.get(episode_id)
    shorts: dict[str, Any] = dict(entry.get("shorts", {}))

    if ctx.get("dry_run"):
        log.warning("%s DRY RUN — shorts publishing skipped", episode_id)
        return

    ids = [sid for sid in (ctx.get("short_ids") or sorted(shorts)) if sid in shorts]
    pending = [sid for sid in ids if shorts[sid].get("status") in ("rendered", "upload_failed")]
    if not pending:
        log.info("%s no pending shorts to publish", episode_id)
        return

    package = _package(base, episode_id)
    long_title = str(package.get("metadata", {}).get("title", ""))
    category = _category(cfg)
    private = bool(ctx.get("private_test"))
    service = build_service()

    uploaded: list[str] = []
    for sid in pending:
        sh = shorts[sid]
        video = Path(sh.get("video_path") or "")
        if not sh.get("video_path") or not video.exists():
            sh["status"] = "upload_failed"
            sh["error"] = f"video missing: {video or '(unset)'}"
            reg.save()
            raise YouTubeError(f"{episode_id} {sid}: {sh['error']}")
        doc = json.loads(Path(sh["file"]).read_text(encoding="utf-8"))
        body = short_body(doc, private=private, long_title=long_title, category_id=category)
        try:
            vid = sh.get("youtube_video_id")
            if not vid:
                vid = _upload(service, video, body, label=f"{episode_id}/{sid}")
                sh["youtube_video_id"] = vid
                sh["uploaded_at"] = now_iso()
                reg.save()
            _verify(service, vid)
        except Exception as exc:
            sh["status"] = "upload_failed"
            sh["error"] = redact(str(exc))[:300]
            reg.save()
            raise
        sh["status"] = "uploaded"
        sh.pop("error", None)
        reg.save()
        uploaded.append(sid)
        log.info("%s %s uploaded -> %s", episode_id, sid, vid)

    _notify(format_success_shorts(
        episode_id,
        [str(shorts[sid].get("youtube_video_id", "?")) for sid in uploaded],
        len(pending),
    ))
    _notify(format_stats(channel_totals(reg), next_posting(cfg, reg)))
