"""Scene-directive seam (plan §2): Groq emits JSON scene directives, Python
validates them into scene-plan JSON for engine-js. Groq never writes JS/HTML.

Phase 2 delivers the prompt + schema; the pipeline wiring (profile dispatch to
the engine) lands in Phase 4.
"""

from __future__ import annotations

import re
from typing import Any

# shortcut: mirrors engine-js/engine.js POSES (idle/wave/walk) — extend both
# together when the engine gains a pose.
POSES = ("idle", "wave", "walk")
SCHEMA = "stickman.directives/1"
MAX_ACTORS = 2              # config content.scene_chars_max for stickman
MAX_DURATION_SEC = 120

_SCENE_ID = re.compile(r"^sc\d{2}$")
_BG = re.compile(r"^#[0-9a-fA-F]{6}$")


def directive_messages(package: dict[str, Any], *, bible_version: str) -> list[dict[str, str]]:
    """Prompt: episode package → scene directives (one Groq JSON call)."""
    scenes = []
    for s in package.get("scenes", []):
        if not isinstance(s, dict):
            continue
        words = sum(len(str(d.get("text", "")).split())
                    for d in s.get("dialogue", []) if isinstance(d, dict))
        words += sum(len(str(n.get("text", "")).split())
                     for n in s.get("narration", []) if isinstance(n, dict))
        scenes.append({"scene_id": s.get("scene_id"), "words": words})
    user = f"""Turn this episode into SCENE DIRECTIVES for the stickman engine.

episode title: {package.get('title')}
duration_target_sec: {package.get('duration_target_sec')}
bible_version: {bible_version}
scenes (words = spoken words; duration_sec ≈ words / 2.5 + 1.5):
{scenes}

POSES (only these): {list(POSES)}
RULES:
- ONE minified JSON object: {{"schema":"{SCHEMA}","bible_version":"{bible_version}","scenes":[...]}}.
- Exactly one directive per scene, SAME order and scene_id as above.
- Directive shape: {{"scene_id":"scNN","duration_sec":<s>,"stage":{{"bg":"#RRGGBB"}},"actors":[{{"id":"<char id>","x":<0..1>,"beats":[{{"t":<sec>,"pose":"<pose>"}}]}}]}}
- actors: 1-2 per scene, ids from the script's characters, x = horizontal position 0..1.
- beats: first beat t=0, strictly increasing, every t <= duration_sec; pose from POSES only.
- Stage bg is one flat light color. No gradients, no images, no JavaScript."""
    return [
        {"role": "system", "content":
         "You are a scene planner for a stick-figure animation engine. "
         "Output a single minified JSON object. No markdown, no commentary."},
        {"role": "user", "content": user},
    ]


def _check_unit(value: Any, where: str, errors: list[str]) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= float(value) <= 1:
        errors.append(f"{where} must be a number in 0..1")


def validate_directives(data: Any, *, bible_version: str | None = None) -> list[str]:
    """Validator for the engine-style repair loop: returns [] when the
    directives are a valid scene-plan source."""
    if not isinstance(data, dict):
        return ["directives must be a JSON object"]
    errors: list[str] = []
    if data.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA!r}")
    if bible_version is not None and data.get("bible_version") != bible_version:
        errors.append("bible_version mismatch (visual bible changed since the prompt)")
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        return errors + ["scenes must be a non-empty list"]
    seen: set[str] = set()
    for i, s in enumerate(scenes):
        where = f"scenes[{i}]"
        if not isinstance(s, dict):
            errors.append(f"{where} must be an object")
            continue
        sid = str(s.get("scene_id", ""))
        if not _SCENE_ID.match(sid):
            errors.append(f"{where}.scene_id must match scNN, got {sid!r}")
        elif sid in seen:
            errors.append(f"{where}.scene_id duplicate: {sid}")
        else:
            seen.add(sid)
        dur = s.get("duration_sec")
        if (not isinstance(dur, (int, float)) or isinstance(dur, bool)
                or not 0 < float(dur) <= MAX_DURATION_SEC):
            errors.append(f"{where}.duration_sec must be a number in (0, {MAX_DURATION_SEC}]")
            dur = None
        stage = s.get("stage", {})
        if not isinstance(stage, dict):
            errors.append(f"{where}.stage must be an object")
        elif "bg" in stage and not (isinstance(stage["bg"], str) and _BG.match(stage["bg"])):
            errors.append(f"{where}.stage.bg must be #RRGGBB")
        actors = s.get("actors")
        if not isinstance(actors, list) or not actors:
            errors.append(f"{where}.actors must be a non-empty list")
            continue
        if len(actors) > MAX_ACTORS:
            errors.append(f"{where}.actors: {len(actors)} > {MAX_ACTORS}")
        for j, a in enumerate(actors):
            aw = f"{where}.actors[{j}]"
            if not isinstance(a, dict):
                errors.append(f"{aw} must be an object")
                continue
            if not str(a.get("id") or "").strip():
                errors.append(f"{aw}.id is required")
            _check_unit(a.get("x"), f"{aw}.x", errors)
            beats = a.get("beats")
            if not isinstance(beats, list) or not beats:
                errors.append(f"{aw}.beats must be a non-empty list")
                continue
            prev = -1.0
            for k, b in enumerate(beats):
                bw = f"{aw}.beats[{k}]"
                if not isinstance(b, dict):
                    errors.append(f"{bw} must be an object")
                    continue
                t = b.get("t")
                if not isinstance(t, (int, float)) or isinstance(t, bool) or float(t) < 0:
                    errors.append(f"{bw}.t must be a number >= 0")
                elif float(t) <= prev:
                    errors.append(f"{bw}.t must be strictly increasing")
                else:
                    prev = float(t)
                pose = b.get("pose")
                if pose is not None and pose not in POSES:
                    errors.append(f"{bw}.pose {pose!r} not in {list(POSES)}")
                if "x" in b:
                    _check_unit(b["x"], f"{bw}.x", errors)
            if dur is not None and prev > float(dur):
                errors.append(f"{aw}: last beat t={prev} exceeds duration_sec={dur}")
    return errors


def scene_plan(directive: dict[str, Any], *, seed: int) -> dict[str, Any]:
    """One validated directive → engine plan (engine-js `buildScene` contract)."""
    return {"seed": int(seed), "duration": float(directive["duration_sec"]),
            "stage": dict(directive.get("stage") or {}),
            "actors": [dict(a) for a in directive["actors"]]}
