"""Pipeline stage wrappers: RENDERING (long video + thumbnail) and shorts render."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..audio.mix import build_short_audio
from ..config import Config
from ..logging_setup import get_logger
from ..state import Registry
from .thumbnail import render_thumbnail
from .video import render_long_video, render_short_video

log = get_logger("render")


def _base(cfg: Config, episode_id: str) -> Path:
    return Path(cfg.get("paths.state", "state")) / "episodes" / episode_id


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"{path} missing — run earlier stages first")
    return json.loads(path.read_text(encoding="utf-8"))


def render_long(cfg: Config, reg: Registry, episode_id: str, ctx: dict[str, Any]) -> None:
    """Stage RENDERING: compose frames, encode, mux audio, build thumbnail."""
    base = _base(cfg, episode_id)
    package = _load_json(base / "package.json")
    timing = _load_json(base / "audio" / "timing.json")
    sample = ctx.get("sample_sec")
    thumb_dir = Path(cfg.get("paths.workspace", "workspace")) / "thumbnails"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    out = render_long_video(cfg, episode_id, package, timing,
                            cfg.get("paths.state", "state"),
                            sample_sec=sample, thumb_dir=thumb_dir)
    thumb = render_thumbnail(cfg, package, thumb_dir / f"{episode_id}.jpg")
    entry = reg.get(episode_id)
    entry["video_path"] = str(out)
    entry["thumbnail_path"] = str(thumb)
    reg.save()
    log.info("%s rendered: %s (thumb %s)", episode_id, out, thumb)


def render_shorts(cfg: Config, reg: Registry, episode_id: str, ctx: dict[str, Any]) -> None:
    """Renders every pending short (audio first if not yet built)."""
    base = _base(cfg, episode_id)
    timing_path = base / "audio" / "timing.json"
    # Fresh checkout: long-day audio/timing.json does not cross runs — start
    # from an empty contract and rebuild only what this run needs.
    timing = json.loads(timing_path.read_text(encoding="utf-8")) if timing_path.exists() else {"shorts": []}
    entry = reg.get(episode_id)
    shorts = entry.get("shorts", {})
    state_root = cfg.get("paths.state", "state")

    for sid in sorted(shorts):
        status = shorts[sid].get("status")
        if status not in ("ready", "rendering_failed"):
            continue
        index = int(sid.split("_")[-1])
        short_doc = _load_json(Path(shorts[sid]["file"]))
        st = next((s for s in timing.get("shorts", []) if s.get("short_id") == sid), None)
        wav = (base / "audio" / str(st.get("file", ""))) if st else None
        try:
            if st is None or not wav.exists():
                st = build_short_audio(cfg, episode_id, short_doc, index, state_root)
                timing["shorts"] = [s for s in timing.get("shorts", [])
                                    if s.get("short_id") != sid] + [st]
                timing_path.parent.mkdir(parents=True, exist_ok=True)
                timing_path.write_text(json.dumps(timing, indent=2), encoding="utf-8")
            out = render_short_video(cfg, episode_id, short_doc, st, index, state_root,
                                     sample_sec=ctx.get("sample_sec"))
            shorts[sid]["status"] = "rendered"
            shorts[sid]["video_path"] = str(out)
            log.info("%s %s rendered -> %s", episode_id, sid, out)
        except Exception as exc:
            shorts[sid]["status"] = "rendering_failed"
            shorts[sid]["error"] = str(exc)[:300]
            reg.save()
            raise
    reg.save()
