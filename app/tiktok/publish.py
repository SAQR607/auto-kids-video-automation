"""Inbox-draft upload via the Content Posting API (video.upload scope).

Flow: POST /v2/post/publish/inbox/video/init/ (FILE_UPLOAD) -> transfer the
file bytes to the returned upload_url (valid 1h). The video then waits in
the creator's TikTok inbox; tapping the notification finishes the post in
the app's editor — no developer audit required for this path.
Limits: max ~5 pending inbox shares / 24h, 6 requests / min per token.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from ..logging_setup import get_logger, redact
from .oauth import ensure_access_token

log = get_logger("tiktok.publish")

INIT_URL = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
# Where the owner lands to finish a queued draft (mobile: TikTok → Inbox).
STUDIO_UPLOAD_URL = "https://www.tiktok.com/tiktokstudio/upload"
TRANSFER_RETRIES = 2


class TikTokError(RuntimeError):
    """Upload failure — surfaced per-short, never breaks the YouTube stage."""


def _http_json(url: str, payload: dict[str, Any], token: str, *, timeout: int = 60) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        snippet = ""
        try:
            snippet = exc.read().decode("utf-8", "replace")[:300]
        except Exception:
            pass
        raise TikTokError(f"init HTTP {exc.code}: {redact(snippet)}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise TikTokError(f"init network error: {redact(str(exc))}") from exc
    err = body.get("error")
    if isinstance(err, dict):
        code, msg = err.get("code"), err.get("message")
        raise TikTokError(f"init api error {code}: {redact(str(msg))[:200]}")
    if err:
        raise TikTokError(f"init api error: {redact(str(err))[:200]}")
    return body


def _transfer_file(upload_url: str, path: Path, *, timeout: int = 600) -> None:
    """Multipart POST of the video to TikTok's upload_url (-F video=@file)."""
    boundary = "----fernwoodtiktok"
    data = path.read_bytes()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="video"; filename="{path.name}"\r\n'
        "Content-Type: video/mp4\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        upload_url, data=body, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    last: Exception | None = None
    for attempt in range(TRANSFER_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if 200 <= resp.status < 300:
                    return
                raise TikTokError(f"transfer HTTP {resp.status}")
        except TikTokError as exc:
            last = exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
        if attempt < TRANSFER_RETRIES:
            log.warning("tiktok transfer attempt %d failed (%s) — retrying", attempt + 1, redact(str(last)))
    raise TikTokError(f"transfer failed: {redact(str(last))[:200]}")


def upload_draft(video_path: Path, title: str, description: str,
                 *, state_dir: str | Path | None = None) -> str:
    """Send one short to the creator's TikTok inbox; returns the publish_id."""
    video_path = Path(video_path)
    if not video_path.exists():
        raise TikTokError(f"video missing: {video_path}")
    token = ensure_access_token(state_dir)
    payload = {
        "post_info": {"title": title, "description": description},
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": video_path.stat().st_size,
        },
        "is_aigc": True,
    }
    body = _http_json(INIT_URL, payload, token)
    data = body.get("data") or {}
    publish_id = str(data.get("publish_id") or "")
    upload_url = str(data.get("upload_url") or "")
    if not upload_url:
        raise TikTokError(f"init returned no upload_url: {redact(str(body))[:200]}")
    _transfer_file(upload_url, video_path)
    log.info("tiktok draft queued: %s (%s)", publish_id or "(no id)", video_path.name)
    return publish_id or upload_url
