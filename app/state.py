"""Episode state machine + persistent registry (§31, §32, §33).

States: PLANNED -> SCRIPTED -> SCRIPT_QC -> AUDIO_READY -> RENDERING ->
        RENDERED -> RENDER_QC -> UPLOADING -> PUBLISHED -> SHORTS_READY ->
        SHORTS_SCHEDULED -> COMPLETE. Any state -> FAILED (bounded retries).

Idempotency: deterministic episode IDs (s01eNNN), one registry entry per
schedule slot — retries and re-runs reuse the same entry, never duplicate.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from enum import Enum
from pathlib import Path
from typing import Any

from .logging_setup import get_logger

log = get_logger("state")


class Stage(str, Enum):
    PLANNED = "PLANNED"
    SCRIPTED = "SCRIPTED"
    SCRIPT_QC = "SCRIPT_QC"
    AUDIO_READY = "AUDIO_READY"
    RENDERING = "RENDERING"
    RENDERED = "RENDERED"
    RENDER_QC = "RENDER_QC"
    UPLOADING = "UPLOADING"
    PUBLISHED = "PUBLISHED"
    SHORTS_READY = "SHORTS_READY"
    SHORTS_SCHEDULED = "SHORTS_SCHEDULED"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


# Allowed forward transitions (FAILED handled separately).
_TRANSITIONS: dict[Stage, set[Stage]] = {
    Stage.PLANNED: {Stage.SCRIPTED},
    Stage.SCRIPTED: {Stage.SCRIPT_QC},
    Stage.SCRIPT_QC: {Stage.AUDIO_READY},
    Stage.AUDIO_READY: {Stage.RENDERING},
    Stage.RENDERING: {Stage.RENDERED},
    Stage.RENDERED: {Stage.RENDER_QC},
    Stage.RENDER_QC: {Stage.UPLOADING},
    Stage.UPLOADING: {Stage.PUBLISHED},
    Stage.PUBLISHED: {Stage.SHORTS_READY},
    Stage.SHORTS_READY: {Stage.SHORTS_SCHEDULED},
    Stage.SHORTS_SCHEDULED: {Stage.COMPLETE},
    Stage.COMPLETE: set(),
    Stage.FAILED: set(),
}

TERMINAL = {Stage.COMPLETE, Stage.FAILED}
# Stage a retry after FAILED should resume from (last good stage before failure).
RESUME_AFTER_FAILURE = {
    Stage.FAILED: Stage.PLANNED,
}


class StateError(Exception):
    pass


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class Registry:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.data: dict[str, Any] = {"version": 1, "counters": {}, "episodes": {}}
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write: tmp file in same dir, then replace.
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh, indent=2, ensure_ascii=False)
            os.replace(tmp, self.path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    # --- episode id assignment (deterministic per slot) ---
    def episode_id_for_slot(self, slot_key: str) -> str:
        """Return the stable episode id for a slot, allocating one on first claim."""
        for ep_id, entry in self.data["episodes"].items():
            if entry.get("slot_key") == slot_key:
                return ep_id
        season = int(self.data["counters"].get("season", 1))
        next_no = int(self.data["counters"].get(f"season_{season}_next", 1))
        ep_id = f"s{season:02d}e{next_no:03d}"
        self.data["counters"][f"season_{season}_next"] = next_no + 1
        self.data["episodes"][ep_id] = {
            "episode_id": ep_id,
            "slot_key": slot_key,
            "stage": Stage.PLANNED.value,
            "attempts": 0,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "title": None,
            "premise": None,
            "youtube_video_id": None,
            "shorts": {},
            "manifest_checksum": None,
            "error": None,
        }
        self.save()
        log.info("registered episode %s for slot %s", ep_id, slot_key)
        return ep_id

    def get(self, episode_id: str) -> dict[str, Any]:
        entry = self.data["episodes"].get(episode_id)
        if entry is None:
            raise StateError(f"Unknown episode id: {episode_id}")
        return entry

    def stage_of(self, episode_id: str) -> Stage:
        return Stage(self.get(episode_id)["stage"])

    def episodes(self) -> dict[str, dict[str, Any]]:
        return self.data["episodes"]

    def transition(self, episode_id: str, to: Stage, **fields: Any) -> None:
        entry = self.get(episode_id)
        current = Stage(entry["stage"])
        if to == Stage.FAILED:
            raise StateError("Use mark_failed() for FAILED")
        if current in TERMINAL:
            raise StateError(f"{episode_id} is terminal ({current.value}); cannot move to {to.value}")
        if to != current and to not in _TRANSITIONS[current]:
            raise StateError(f"Illegal transition {current.value} -> {to.value} for {episode_id}")
        entry["stage"] = to.value
        entry["updated_at"] = now_iso()
        entry["error"] = None
        entry["failed_stage"] = None
        entry.update(fields)
        self.save()
        log.info("episode %s: %s", episode_id, to.value)

    def mark_failed(self, episode_id: str, error: str, *, failed_stage: str | None = None) -> None:
        entry = self.get(episode_id)
        entry["stage"] = Stage.FAILED.value
        entry["attempts"] = int(entry.get("attempts", 0)) + 1
        entry["failed_stage"] = failed_stage or entry.get("failed_stage")
        entry["error"] = error[:500]
        entry["updated_at"] = now_iso()
        self.save()
        log.error("episode %s FAILED (attempt %d): %s", episode_id, entry["attempts"], error[:200])

    def can_retry(self, episode_id: str, max_attempts: int) -> bool:
        entry = self.get(episode_id)
        return entry["stage"] == Stage.FAILED.value and int(entry.get("attempts", 0)) < max_attempts

    def unfail(self, episode_id: str) -> None:
        """Leave FAILED by re-entering the stage that failed (resume point)."""
        entry = self.get(episode_id)
        if entry["stage"] != Stage.FAILED.value:
            return
        resume = entry.get("failed_stage") or Stage.PLANNED.value
        try:
            Stage(resume)
        except ValueError:
            resume = Stage.PLANNED.value
        entry["stage"] = resume
        entry["updated_at"] = now_iso()
        self.save()
        log.info("episode %s resumed at %s (attempt %d)", episode_id, resume, entry.get("attempts", 0))

    def resume_stage(self, episode_id: str) -> Stage:
        """Stage to re-run after a FAILED episode (re-enter pipeline at start of
        the failed stage; content stages are idempotent by checksum)."""
        entry = self.get(episode_id)
        failed = entry.get("failed_stage")
        try:
            return Stage(failed) if failed else Stage.PLANNED
        except ValueError:
            return Stage.PLANNED


def registry_path(cfg_paths_state: str | Path) -> Path:
    return Path(cfg_paths_state) / "registry.json"


def load_registry(state_dir: str | Path) -> Registry:
    reg = Registry(Path(state_dir) / "registry.json")
    return reg
