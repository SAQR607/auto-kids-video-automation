"""Content engine: premise + full episode package via Groq, validated, saved.

Idempotent: a valid package.json short-circuits regeneration (resume-safe).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Callable

from ..config import ROOT, Config, groq_keys
from ..groq_client import GroqClient, extract_json
from ..logging_setup import get_logger
from ..state import Registry, now_iso
from .memory import Memory
from .prompts import premise_messages, repair_messages, script_messages
from .universe import ARC_CRUMBS, Universe
from .validate import normalize_emotions, validate_package, validate_premise

log = get_logger("content")

MAX_CONTENT_REPAIRS = 2


class GenerationError(Exception):
    pass


def _groq(cfg: Config) -> GroqClient:
    g = cfg.get("groq", {})
    keys = [k for k in groq_keys() if not k.strip().upper().startswith("REPLACE")]
    if not keys:
        raise GenerationError("No Groq keys configured")
    return GroqClient(
        keys,
        model=g.get("model", "openai/gpt-oss-20b"),
        max_tokens=int(g.get("max_tokens", 8192)),
        temperature=float(g.get("temperature", 0.8)),
        timeout_sec=int(g.get("timeout_sec", 120)),
        max_attempts=int(g.get("max_attempts_per_call", 6)),
        backoff_base=float(g.get("backoff_base_sec", 2)),
        backoff_max=float(g.get("backoff_max_sec", 60)),
    )


def _episode_number(episode_id: str) -> int:
    m = re.match(r"s\d+e(\d+)", episode_id)
    return int(m.group(1)) if m else 1


def _generate_json(
    groq: GroqClient,
    messages: list[dict[str, str]],
    validator: Callable[[Any], list[str]],
    stage: str,
    max_tokens: int,
    normalize: Callable[[Any], list[str]] | None = None,
) -> dict[str, Any]:
    """One generation stage with bounded repair passes (§25)."""
    last_errors: list[str] = []
    base = messages
    for attempt in range(1 + MAX_CONTENT_REPAIRS):
        raw = groq.chat(messages, temperature=0.5 if attempt else None,
                        max_tokens=max_tokens, reasoning_effort="low")
        try:
            data = extract_json(raw)
        except ValueError as exc:
            last_errors = [f"JSON parse: {exc}"]
            messages = repair_messages(stage, last_errors, raw, base)
            continue
        if normalize:
            changes = normalize(data)
            if changes:
                log.warning("%s: repaired %d invented emotion(s): %s",
                            stage, len(changes), ", ".join(changes[:6]))
        last_errors = validator(data)
        if not last_errors:
            log.info("%s generation ok (attempt %d)", stage, attempt + 1)
            return data
        log.warning("%s validation errors (attempt %d): %s", stage, attempt + 1, last_errors[:5])
        messages = repair_messages(stage, last_errors, raw, base)
    raise GenerationError(f"{stage} failed validation after {1 + MAX_CONTENT_REPAIRS} attempts: {last_errors[:8]}")


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def package_path(cfg: Config, episode_id: str) -> Path:
    return Path(cfg.get("paths.state", "state")) / "episodes" / episode_id / "package.json"


def run_generation(cfg: Config, reg: Registry, episode_id: str, ctx: dict[str, Any]) -> None:
    """Stage SCRIPTED: produce state/episodes/<id>/package.json (idempotent)."""
    universe = Universe()
    memory = Memory(Path(cfg.get("paths.state", "state")) / "story_memory")
    path = package_path(cfg, episode_id)

    if path.exists():
        try:
            pkg = json.loads(path.read_text(encoding="utf-8"))
            errors = validate_package(pkg, universe, cfg)
        except json.JSONDecodeError:
            errors = ["unreadable package.json"]
        if not errors:
            log.info("%s: package already exists and validates — skipping generation", episode_id)
            _update_registry(reg, episode_id, pkg, path)
            return
        log.warning("%s: existing package invalid (%s) — regenerating", episode_id, errors[:3])

    entry = reg.get(episode_id)
    ep_no = _episode_number(episode_id)
    include_arc = ep_no in ARC_CRUMBS
    arc_crumb = ARC_CRUMBS.get(ep_no) if include_arc else None

    groq = _groq(cfg)
    log.info("%s: generating premise (arc=%s)", episode_id, include_arc)
    premise = _generate_json(
        groq,
        premise_messages(
            universe, memory,
            episode_id=episode_id, episode_no=ep_no,
            include_arc=include_arc, arc_crumb=arc_crumb,
        ),
        lambda p: validate_premise(p, universe, arc_required=include_arc),
        "premise",
        max_tokens=1200,
    )

    log.info("%s: generating full script", episode_id)
    package = _generate_json(
        groq,
        script_messages(
            premise, universe, memory,
            episode_id=episode_id, episode_no=ep_no,
            include_arc=include_arc, arc_crumb=arc_crumb,
        ),
        lambda p: validate_package(p, universe, cfg),
        "script",
        max_tokens=5400,
        normalize=lambda p: normalize_emotions(p, universe),
    )
    package["episode_id"] = episode_id
    if include_arc and not package.get("arc_crumb"):
        package["arc_crumb"] = arc_crumb
    if not include_arc:
        package["arc_crumb"] = None

    _atomic_write_json(path, package)
    _update_registry(reg, episode_id, package, path)
    memory.record_episode(episode_id, package)
    log.info(
        "%s: package saved — '%s' (%d scenes, %d shorts)",
        episode_id, package.get("title"), len(package.get("scenes", [])), len(package.get("shorts", [])),
    )


def _update_registry(reg: Registry, episode_id: str, package: dict[str, Any], path: Path) -> None:
    entry = reg.get(episode_id)
    raw = json.dumps(package, sort_keys=True, ensure_ascii=False).encode("utf-8")
    entry["title"] = package.get("title")
    entry["premise"] = package.get("premise")
    entry["learning_spine"] = package.get("learning_spine")
    entry["youtube_title"] = package.get("metadata", {}).get("title")
    entry["manifest_checksum"] = hashlib.sha256(raw).hexdigest()
    entry["updated_at"] = now_iso()
    reg.save()
