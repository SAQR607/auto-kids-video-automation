"""Structural validation of generated content (fail fast, before QC)."""

from __future__ import annotations

import re
from typing import Any

from ..config import Config
from .universe import SHORT_MOODS, SPINES, Universe

# Strict content bans for children 4-8 (STORY_BIBLE).
_BANNED_PATTERNS = [
    r"\bdanger\b", r"\bscary\b", r"\bmonster\b", r"\bkill\b", r"\bhate\b",
    r"\bstupid\b", r"\bbuy\b", r"\bsubscribe\b", r"\bcomment\b", r"\bdiscount\b",
    r"\bweapon\b", r"\bgun\b", r"\bfight\b", r"\bmean\b", r"\blaugh at\b",
    r"\bshut up\b", r"\bdie\b", r"\bfreak\b", r"\bweirdo\b",
]
_BANNED_RE = re.compile("|".join(_BANNED_PATTERNS), re.I)

_ARC_TOKENS = re.compile(r"\b(cave|compass|glimmer cave|heart[- ]stone|root[- ]door|pebble stack)\b", re.I)

_WORDS_PER_SEC = 2.4
_SCENE_GAP_SEC = 1.5


def _words(text: str) -> int:
    return len(re.findall(r"\w+", text))


# The sprite expression set is closed; the model sometimes invents near-synonyms
# (calm/confused/thoughtful...). Generation-time repair maps them back instead of
# failing the whole script and re-rolling it (which costs another big Groq call).
EMOTION_ALIASES = {
    "calm": "neutral",
    "relaxed": "neutral",
    "confused": "curious",
    "thinking": "curious",
    "thoughtful": "curious",
    "angry": "worried",
    "mad": "worried",
    "scared": "worried",
    "afraid": "worried",
    "fearful": "worried",
    "crying": "sad",
    "tearful": "sad",
    "joyful": "happy",
    "glad": "happy",
    "playful": "silly",
    "grateful": "proud",
}


def normalize_emotions(package: Any, universe: Universe) -> list[str]:
    """Rewrite emotions to manifest expressions (case + alias + neutral fallback).

    Returns "old->new" strings for every changed line (empty if none).
    """
    exprs = set(universe.manifest.get("expressions", []))
    changed: list[str] = []

    def _fix(line: dict[str, Any]) -> None:
        raw = str(line.get("emotion", "neutral")).strip().lower()
        if raw in exprs:
            if line.get("emotion") != raw:
                line["emotion"] = raw
            return
        target = EMOTION_ALIASES.get(raw, "neutral")
        changed.append(f"{line.get('emotion')}->{target}")
        line["emotion"] = target

    if isinstance(package, dict):
        for group in (package.get("scenes") or [], package.get("shorts") or []):
            for item in group if isinstance(group, list) else []:
                if not isinstance(item, dict):
                    continue
                dialogue = item.get("dialogue")
                if isinstance(dialogue, list):
                    for line in dialogue:
                        if isinstance(line, dict):
                            _fix(line)
    return changed


def estimate_long_seconds(package: dict[str, Any]) -> float:
    spoken = 0
    for scene in package.get("scenes", []):
        for line in scene.get("dialogue", []):
            spoken += _words(line.get("text", ""))
        for line in scene.get("narration", []):
            spoken += _words(line.get("text", ""))
    return round(spoken / _WORDS_PER_SEC + len(package.get("scenes", [])) * _SCENE_GAP_SEC, 1)


def estimate_short_seconds(short: dict[str, Any]) -> float:
    spoken = sum(_words(l.get("text", "")) for l in short.get("dialogue", []))
    return round(spoken / _WORDS_PER_SEC + 2.0, 1)


def validate_premise(p: Any, universe: Universe, *, arc_required: bool) -> list[str]:
    errors: list[str] = []
    if not isinstance(p, dict):
        return ["premise is not a JSON object"]
    for key in ("title", "premise", "learning_spine", "hook", "arc_crumb",
                "thumbnail_concept", "shorts_moods"):
        if key not in p:
            errors.append(f"missing key: {key}")
    if errors:
        return errors
    if len(str(p["title"])) > 62:
        errors.append("title exceeds 62 chars")
    if p["learning_spine"] not in SPINES:
        errors.append(f"learning_spine '{p['learning_spine']}' not in catalog")
    tc = p.get("thumbnail_concept", {})
    if tc.get("background") not in universe.location_ids:
        errors.append(f"thumbnail background '{tc.get('background')}' unknown location")
    for cid in tc.get("characters", [])[:]:
        if cid not in universe.character_ids:
            errors.append(f"thumbnail character '{cid}' unknown")
    moods = p.get("shorts_moods", [])
    if len(moods) != 2 or len(set(moods)) != 2 or any(m not in SHORT_MOODS for m in moods):
        errors.append(f"shorts_moods must be 2 different moods from {SHORT_MOODS}")
    crumb = p.get("arc_crumb")
    if arc_required and not crumb:
        errors.append("arc_crumb required for this episode but missing/null")
    if not arc_required and crumb:
        errors.append("arc_crumb must be null for non-arc episodes")
    if _BANNED_RE.search(str(p.get("premise", "")) + " " + str(p.get("hook", ""))):
        errors.append("banned word in premise/hook")
    return errors


def validate_package(pkg: Any, universe: Universe, cfg: Config) -> list[str]:
    errors: list[str] = []
    if not isinstance(pkg, dict):
        return ["package is not a JSON object"]
    required = ("schema", "episode_id", "title", "premise", "learning_spine",
                "duration_target_sec", "hook", "scenes", "shorts", "metadata")
    for key in required:
        if key not in pkg:
            errors.append(f"missing top-level key: {key}")
    if errors:
        return errors

    if pkg["schema"] != "fernwood.episode/1":
        errors.append(f"schema must be fernwood.episode/1 (got {pkg['schema']!r})")
    if pkg["learning_spine"] not in SPINES:
        errors.append(f"learning_spine '{pkg['learning_spine']}' not in catalog")
    if _BANNED_RE.search(" ".join([
        str(pkg.get("title", "")), str(pkg.get("premise", "")), str(pkg.get("hook", ""))
    ])):
        errors.append("banned word in title/premise/hook")

    scenes = pkg.get("scenes", [])
    if not isinstance(scenes, list) or not (13 <= len(scenes) <= 18):
        errors.append(f"scenes must be 13-18 (got {len(scenes) if isinstance(scenes, list) else 'n/a'})")
        return errors
    if len(str(pkg.get("title", ""))) > 62:
        errors.append("top-level title exceeds 62 chars")

    exprs = set(universe.manifest.get("expressions", []))
    cam_moves = set(universe.manifest.get("camera_moves", []))
    transitions = set(universe.manifest.get("transitions", []))
    positions = set(universe.manifest.get("positions", []))
    entrances = set(universe.manifest.get("entrances", []))
    moods = set(universe.manifest.get("music_moods", []))
    props = set(universe.prop_ids)
    fx = set(universe.manifest.get("fx", []))
    chars = set(universe.character_ids)
    locs = set(universe.location_ids)
    times = {"day", "morning", "dusk", "night"}

    total_words = 0
    for i, scene in enumerate(scenes, 1):
        tag = f"scene {i} ({scene.get('scene_id', '?')})"
        if scene.get("location") not in locs:
            errors.append(f"{tag}: unknown location '{scene.get('location')}'")
        if scene.get("time_of_day") not in times:
            errors.append(f"{tag}: bad time_of_day '{scene.get('time_of_day')}'")
        if scene.get("camera") not in cam_moves:
            errors.append(f"{tag}: bad camera '{scene.get('camera')}'")
        if scene.get("transition_in") not in transitions:
            errors.append(f"{tag}: bad transition '{scene.get('transition_in')}'")
        if scene.get("music_mood") not in moods:
            errors.append(f"{tag}: bad music_mood '{scene.get('music_mood')}'")
        scene_chars = scene.get("characters", [])
        if not isinstance(scene_chars, list) or not (2 <= len(scene_chars) <= 4):
            errors.append(f"{tag}: needs 2-4 characters")
        else:
            for c in scene_chars:
                if not isinstance(c, dict) or c.get("id") not in chars:
                    errors.append(f"{tag}: bad character entry {c!r}")
                    continue
                if c.get("position") not in positions:
                    errors.append(f"{tag}: bad position '{c.get('position')}'")
                if c.get("enter", "onscreen") not in entrances:
                    errors.append(f"{tag}: bad enter '{c.get('enter')}'")
        for prop in scene.get("props", [])[:]:
            if prop not in props:
                errors.append(f"{tag}: unknown prop '{prop}'")
        for f in scene.get("fx", [])[:]:
            if f not in fx:
                errors.append(f"{tag}: unknown fx '{f}'")
        for line in scene.get("dialogue", []):
            sp = line.get("speaker", "")
            if sp not in chars:
                errors.append(f"{tag}: unknown speaker '{sp}'")
            if line.get("emotion", "neutral") not in exprs:
                errors.append(f"{tag}: bad emotion '{line.get('emotion')}'")
            w = _words(line.get("text", ""))
            total_words += w
            if w > 14:
                errors.append(f"{tag}: dialogue line over 14 words ({w})")
            if _BANNED_RE.search(line.get("text", "")):
                errors.append(f"{tag}: banned word in dialogue: {line.get('text', '')[:60]!r}")
        for line in scene.get("narration", []):
            total_words += _words(line.get("text", ""))
            if _BANNED_RE.search(line.get("text", "")):
                errors.append(f"{tag}: banned word in narration")
        scene_words = sum(_words(l.get("text", "")) for l in scene.get("dialogue", [])) + sum(
            _words(l.get("text", "")) for l in scene.get("narration", [])
        )
        if scene_words < 40:
            errors.append(f"{tag}: too sparse ({scene_words} spoken words, need >=40)")

    if not (1100 <= total_words <= 1450):
        errors.append(f"total spoken words {total_words} outside 1100-1450")
    est = estimate_long_seconds(pkg)
    lmin = int(cfg.get("duration.long_min_sec"))
    lmax = int(cfg.get("duration.long_max_sec"))
    if not (lmin <= est <= lmax):
        errors.append(f"estimated duration {est}s outside {lmin}-{lmax}s")

    # shorts
    shorts = pkg.get("shorts", [])
    if not isinstance(shorts, list) or len(shorts) != 2:
        errors.append(f"exactly 2 shorts required (got {len(shorts) if isinstance(shorts, list) else 'n/a'})")
        return errors
    kinds = [s.get("kind") for s in shorts]
    if len(set(kinds)) != 2 or any(k not in SHORT_MOODS for k in kinds):
        errors.append(f"shorts kinds must be 2 different from {SHORT_MOODS}")
    for j, sh in enumerate(shorts, 1):
        stag = f"short {j}"
        if len(str(sh.get("title", ""))) > 40:
            errors.append(f"{stag}: title over 40 chars")
        if sh.get("location") not in locs:
            errors.append(f"{stag}: unknown location")
        if sh.get("camera") not in cam_moves:
            errors.append(f"{stag}: bad camera")
        if sh.get("music_mood") not in moods:
            errors.append(f"{stag}: bad music_mood")
        if not (1 <= len(sh.get("characters", [])) <= 2):
            errors.append(f"{stag}: needs 1-2 characters")
        for c in sh.get("characters", []):
            if c not in chars:
                errors.append(f"{stag}: unknown character '{c}'")
        lines = sh.get("dialogue", [])
        if not (2 <= len(lines) <= 5):
            errors.append(f"{stag}: needs 2-5 dialogue lines")
        sh_text = " ".join(l.get("text", "") for l in lines) + " " + str(sh.get("title", ""))
        if _BANNED_RE.search(sh_text):
            errors.append(f"{stag}: banned word")
        if _ARC_TOKENS.search(sh_text):
            errors.append(f"{stag}: must not reference season arc")
        if str(sh.get("kind")) == "arc":
            errors.append(f"{stag}: arc kind forbidden")
        est_s = estimate_short_seconds(sh)
        smin = int(cfg.get("duration.short_min_sec"))
        smax = int(cfg.get("duration.short_max_sec"))
        if not (smin - 8 <= est_s <= smax + 8):  # pre-audio estimate tolerance
            errors.append(f"{stag}: estimated {est_s}s outside {smin}-{smax}s±8")

    # metadata
    meta = pkg.get("metadata", {})
    title = str(meta.get("title", ""))
    desc = str(meta.get("description", ""))
    tags = meta.get("tags", [])
    if not title or len(title) > 70:
        errors.append(f"metadata.title missing or over 70 chars ({len(title)})")
    if "Fernwood Friends" not in title:
        errors.append("metadata.title must end with | Fernwood Friends S1E##")
    if not desc or len(desc) > 500:
        errors.append(f"metadata.description missing or over 500 chars ({len(desc)})")
    if re.search(r"https?://|www\.", desc, re.I):
        errors.append("metadata.description must not contain links")
    if _BANNED_RE.search(desc):
        errors.append("banned word in description")
    if not isinstance(tags, list) or not (8 <= len(tags) <= 15):
        errors.append(f"metadata.tags must be 8-15 (got {len(tags) if isinstance(tags, list) else 'n/a'})")
    if not any("kids" in str(t).lower() for t in tags):
        errors.append("tags must include kids-oriented tag")
    return errors
