"""Shorts packages: extract from the long package at SHORTS_READY (§24)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import Config
from ..logging_setup import get_logger
from ..state import Registry
from .engine import package_path

log = get_logger("shorts")

SHORT_SCHEMA = "fernwood.short/1"


def short_path(cfg: Config, episode_id: str, index: int) -> Path:
    return Path(cfg.get("paths.state", "state")) / "episodes" / episode_id / "shorts" / f"short_{index}.json"


def build_short_packages(cfg: Config, reg: Registry, episode_id: str, ctx: dict[str, Any]) -> None:
    """Stage SHORTS_READY: split the episode's 2 shorts into standalone files
    and register their pending statuses (rendered on the shorts day)."""
    pkg_file = package_path(cfg, episode_id)
    if not pkg_file.exists():
        raise FileNotFoundError(f"package.json missing for {episode_id} — generation incomplete")
    package = json.loads(pkg_file.read_text(encoding="utf-8"))
    shorts = package.get("shorts", [])
    if len(shorts) != 2:
        raise ValueError(f"expected 2 shorts in package, found {len(shorts)}")

    statuses: dict[str, dict[str, Any]] = {}
    for i, sh in enumerate(shorts, 1):
        doc = {
            "schema": SHORT_SCHEMA,
            "episode_id": episode_id,
            "short_id": f"short_{i}",
            "title": sh.get("title", ""),
            "kind": sh.get("kind", ""),
            "location": sh.get("location"),
            "time_of_day": sh.get("time_of_day", "day"),
            "camera": sh.get("camera", "static"),
            "characters": sh.get("characters", []),
            "dialogue": sh.get("dialogue", []),
            "music_mood": sh.get("music_mood", "happy"),
            "duration_target_sec": sh.get("duration_target_sec", 34),
            "long_episode_youtube_title": package.get("metadata", {}).get("title", ""),
        }
        path = short_path(cfg, episode_id, i)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
        statuses[f"short_{i}"] = {
            "status": "ready",
            "title": doc["title"],
            "kind": doc["kind"],
            "file": str(path),
        }
        log.info("%s %s ready: '%s' (%s)", episode_id, f"short_{i}", doc["title"], doc["kind"])

    entry = reg.get(episode_id)
    entry["shorts"] = statuses
    reg.save()
