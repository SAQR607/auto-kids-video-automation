"""Stage RENDER_QC: PASS/FAIL gate on the rendered video (§16).

ffprobe structural checks (container, streams, resolution, fps, duration,
size), ffmpeg loudness sanity, thumbnail sanity, and an optional
faster-whisper transcript spot-check (QC_TRANSCRIBE=1 — keep OFF on weak
local machines; GitHub runners can enable it).

Writes qc/video_qc.json + registry marker; raises VideoQCError on FAIL.
The pipeline bridges RENDERING -> RENDERED -> RENDER_QC after this stage
returns, so no transition happens here.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from ..config import Config, env_bool
from ..logging_setup import get_logger
from ..state import Registry, now_iso

log = get_logger("video_qc")

THUMB_SIZE = (1280, 720)
THUMB_MAX_BYTES = 2 * 1024 * 1024  # YouTube thumbnail limit
SILENCE_FLOOR_DB = -45.0


class VideoQCError(RuntimeError):
    """Video QC FAIL — pipeline marks the episode FAILED."""


def _ffprobe(path: Path) -> dict:
    exe = shutil.which("ffprobe") or shutil.which("ffprobe.exe")
    if not exe:
        raise VideoQCError("ffprobe not found on PATH (install ffmpeg)")
    out = subprocess.run(
        [exe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        capture_output=True, text=True, timeout=60,
    )
    if out.returncode != 0:
        raise VideoQCError(f"ffprobe failed: {(out.stderr or '').strip()[:300]}")
    return json.loads(out.stdout or "{}")


def _volume_db(path: Path) -> float | None:
    exe = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if not exe:
        return None
    out = subprocess.run(
        [exe, "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True, timeout=180,
    )
    m = re.search(r"mean_volume:\s*(-?[\d.]+)\s*dB", out.stderr or "")
    return float(m.group(1)) if m else None


def probe_video(path: Path, *, width: int | None = None, height: int | None = None,
                fps: float | None = None, duration: float | None = None,
                duration_tol: float | None = None, min_bytes: int = 100_000,
                require_audio: bool = True, check_volume: bool = False) -> list[str]:
    """Structural checks on a media file; returns [] when all pass."""
    p = Path(path)
    if not p.exists():
        return [f"missing file: {p}"]
    size = p.stat().st_size
    errors: list[str] = []
    if size < min_bytes:
        errors.append(f"file too small: {size} bytes (< {min_bytes})")
    try:
        data = _ffprobe(p)
    except Exception as exc:
        return errors + [str(exc)]

    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

    if video is None:
        errors.append("no video stream")
    else:
        if video.get("codec_name") != "h264":
            errors.append(f"video codec {video.get('codec_name')!r} != h264")
        if width and int(video.get("width") or 0) != width:
            errors.append(f"width {video.get('width')} != {width}")
        if height and int(video.get("height") or 0) != height:
            errors.append(f"height {video.get('height')} != {height}")
        if fps:
            try:
                num, den = (video.get("r_frame_rate") or "0/1").split("/")
                actual = float(num) / float(den or 1)
                if abs(actual - float(fps)) > 0.51:
                    errors.append(f"fps {actual:.2f} != {fps}")
            except (ValueError, ZeroDivisionError):
                errors.append(f"bad r_frame_rate {video.get('r_frame_rate')!r}")

    if require_audio and audio is None:
        errors.append("no audio stream")
    elif audio and audio.get("codec_name") not in ("aac", "opus", "mp3"):
        errors.append(f"audio codec {audio.get('codec_name')!r} not supported")

    fmt_dur = data.get("format", {}).get("duration") or (video or {}).get("duration")
    try:
        actual_dur = float(fmt_dur)
    except (TypeError, ValueError):
        actual_dur = 0.0
    if duration:
        tol = duration_tol if duration_tol is not None else max(6.0, 0.12 * duration)
        if abs(actual_dur - duration) > tol:
            errors.append(f"duration {actual_dur:.1f}s != expected {duration:.1f}s (±{tol:.0f})")

    if check_volume:
        db = _volume_db(p)
        if db is None:
            errors.append("could not measure audio loudness")
        elif db < SILENCE_FLOOR_DB:
            errors.append(f"audio near silent: {db:.1f} dB")
    return errors


def _check_thumbnail(thumb: Path) -> list[str]:
    if not thumb.exists():
        return [f"thumbnail missing: {thumb}"]
    size = thumb.stat().st_size
    errors: list[str] = []
    if size > THUMB_MAX_BYTES:
        errors.append(f"thumbnail {size} bytes > 2 MB YouTube limit")
    if size < 10_000:
        errors.append(f"thumbnail suspiciously small: {size} bytes")
    try:
        from PIL import Image

        with Image.open(thumb) as im:
            if im.format != "JPEG":
                errors.append(f"thumbnail format {im.format} != JPEG")
            if tuple(im.size) != THUMB_SIZE:
                errors.append(f"thumbnail size {im.size} != {THUMB_SIZE}")
    except Exception as exc:
        errors.append(f"thumbnail unreadable: {exc}")
    return errors


def _transcribe(path: Path, seconds: float) -> str:
    import os

    from faster_whisper import WhisperModel

    model = WhisperModel("tiny", device="cpu", compute_type="int8",
                         cpu_threads=int(os.environ.get("WHISPER_THREADS") or 2))
    segments, _ = model.transcribe(
        str(path), beam_size=1, language="en", clip_timestamps=[0.0, float(seconds)]
    )
    return " ".join(seg.text.strip() for seg in segments).strip()


def check_video(cfg: Config, reg: Registry, episode_id: str, ctx: dict[str, Any]) -> None:
    """Stage RENDER_QC: PASS/FAIL gate; raises VideoQCError on FAIL."""
    base = Path(cfg.get("paths.state", "state")) / "episodes" / episode_id
    entry = reg.get(episode_id)
    video = Path(entry.get("video_path") or (base / "render" / "long.mp4"))

    sample = float(ctx["sample_sec"]) if ctx.get("sample_sec") else None
    expected = sample
    if expected is None:
        timing_file = base / "audio" / "timing.json"
        if timing_file.exists():
            expected = float(json.loads(timing_file.read_text(encoding="utf-8")).get("total") or 0) or None

    width = int(cfg.get("render.width", 1920))
    height = int(cfg.get("render.height", 1080))
    fps = int(cfg.get("render.fps", 24))
    min_bytes = max(50_000, int((expected or 60.0) * 10_000))

    errors = probe_video(
        video, width=width, height=height, fps=fps,
        duration=expected, min_bytes=min_bytes, check_volume=True,
    )
    if not errors:
        thumb = Path(entry.get("thumbnail_path") or (base / "render" / "thumb.jpg"))
        errors.extend(_check_thumbnail(thumb))

    transcript = None
    if not errors and env_bool("QC_TRANSCRIBE", False):
        try:
            transcript = _transcribe(video, min(90.0, expected or 90.0))
            if len(transcript) < 20:
                errors.append(f"transcript too short ({len(transcript)} chars): {transcript[:60]!r}")
        except Exception as exc:
            errors.append(f"transcript check failed: {type(exc).__name__}: {exc}")

    report = {
        "episode_id": episode_id,
        "checked_at": now_iso(),
        "status": "FAIL" if errors else "PASS",
        "video": str(video),
        "expected_duration_sec": expected,
        "sample": sample is not None,
        "transcribed": transcript is not None,
        "errors": errors,
    }
    qc_dir = base / "qc"
    qc_dir.mkdir(parents=True, exist_ok=True)
    (qc_dir / "video_qc.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    entry["video_qc"] = {"status": report["status"], "at": report["checked_at"]}
    reg.save()

    if errors:
        raise VideoQCError(f"video QC failed with {len(errors)} error(s): " + "; ".join(errors))
    log.info("%s video QC PASS (%s, expected %.1fs%s)",
             episode_id, video.name, expected or -1,
             ", transcribed" if transcript is not None else "")
