"""Story memory: canon facts + per-episode continuity (STORY_BIBLE §memory)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..logging_setup import get_logger

log = get_logger("memory")


class Memory:
    def __init__(self, story_dir: Path):
        self.dir = Path(story_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.episodes_dir = self.dir / "episodes"
        self.episodes_dir.mkdir(exist_ok=True)
        self.canon_path = self.dir / "canon.json"
        self.canon: dict[str, Any] = {"facts": [], "callbacks": [], "glimmer_state": {}}
        if self.canon_path.exists():
            try:
                self.canon = json.loads(self.canon_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                log.warning("canon.json unreadable — starting fresh canon")

    # --- reads for prompt context ---
    def recent_episodes(self, limit: int = 3) -> list[dict[str, Any]]:
        files = sorted(self.episodes_dir.glob("*.json"))[-limit:]
        out = []
        for f in files:
            try:
                out.append(json.loads(f.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
        return out

    def used_spines(self, limit: int = 6) -> list[str]:
        return [
            e.get("learning_spine", "")
            for e in self.recent_episodes(limit)
            if e.get("learning_spine")
        ]

    def context_block(self) -> str:
        recent = self.recent_episodes(2)
        lines = ["## STORY MEMORY (continuity — never contradict)"]
        if self.canon.get("facts"):
            lines.append("Canon facts:")
            lines.extend(f"- {f}" for f in self.canon["facts"][-8:])
        if recent:
            lines.append("Recent episodes:")
            for e in recent:
                lines.append(
                    f"- {e.get('episode_id')}: {e.get('title')} (spine: {e.get('learning_spine')})"
                )
                for add in e.get("canon_additions", [])[:4]:
                    lines.append(f"  * {add}")
        spines = self.used_spines(6)
        if spines:
            lines.append(f"Recently used learning spines (do not repeat now): {', '.join(spines)}")
        if not self.canon.get("facts") and not recent:
            lines.append("(empty — this is the first episode)")
        return "\n".join(lines)

    # --- writes after an episode package is produced ---
    def record_episode(self, episode_id: str, package: dict[str, Any]) -> None:
        spine = package.get("learning_spine", "")
        record = {
            "episode_id": episode_id,
            "title": package.get("title"),
            "learning_spine": spine,
            "canon_additions": _derive_additions(package),
            "callbacks_available": package.get("callbacks_available", []),
        }
        path = self.episodes_dir / f"{episode_id}.json"
        path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        for fact in record["canon_additions"]:
            if fact not in self.canon["facts"]:
                self.canon["facts"].append(fact)
        self.canon["facts"] = self.canon["facts"][-60:]  # bounded growth
        self.canon_path.write_text(json.dumps(self.canon, indent=2, ensure_ascii=False), encoding="utf-8")
        log.info("memory updated for %s (%d facts total)", episode_id, len(self.canon["facts"]))


def _derive_additions(package: dict[str, Any]) -> list[str]:
    """Conservative auto-facts: locations visited + explicit continuity notes."""
    additions: list[str] = []
    locs = []
    for scene in package.get("scenes", []):
        loc = scene.get("location")
        if loc and loc not in locs:
            locs.append(loc)
    if locs:
        additions.append(f"visited: {', '.join(locs)}")
    if package.get("arc_crumb"):
        additions.append(f"arc crumb: {package['arc_crumb']}")
    return additions
