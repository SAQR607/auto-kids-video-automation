"""Structural validation of generated content (fail fast, before QC)."""

from __future__ import annotations

import re
from typing import Any

from ..config import Config
from .universe import Universe

# Strict content bans for children 4-8 (STORY_BIBLE) — default profile.
# Overridable per profile via content.banned_patterns (list of regex strings).
_BANNED_PATTERNS = [
    r"\bdanger\b", r"\bscary\b", r"\bmonster\b", r"\bkill\b", r"\bhate\b",
    r"\bstupid\b", r"\bbuy\b", r"\bsubscribe\b", r"\bcomment\b", r"\bdiscount\b",
    r"\bweapon\b", r"\bgun\b", r"\bfight\b", r"\bmean\b", r"\blaugh at\b",
    r"\bshut up\b", r"\bdie\b", r"\bfreak\b", r"\bweirdo\b",
]

# Fernwood season-arc words that shorts must never reference — overridable
# per profile via content.arc_tokens (list; empty = no arc check).
_ARC_TOKEN_PATTERNS = [
    r"cave", r"compass", r"glimmer cave", r"heart[- ]stone", r"root[- ]door",
    r"pebble stack",
]

_DEFAULT_THIN_HINT = (
    "expand the thinnest scenes to 80-95 spoken words each "
    "(5 dialogue lines of 9-11 words + a 35-40 word narration), "
    "then recount the total: "
)


def _banned_re(cfg: Config | None) -> re.Pattern[str]:
    pats = cfg.get("content.banned_patterns") if cfg is not None else None
    if not isinstance(pats, list) or not pats:
        pats = _BANNED_PATTERNS
    return re.compile("|".join(str(p) for p in pats), re.I)


def _arc_re(cfg: Config | None) -> re.Pattern[str] | None:
    pats = cfg.get("content.arc_tokens") if cfg is not None else None
    if pats is None:
        pats = _ARC_TOKEN_PATTERNS
    if not isinstance(pats, list) or not pats:
        return None
    return re.compile("|".join(str(p) for p in pats), re.I)

_DASH_RE = re.compile(r"[\u2010-\u2015\u2212\uFE58\uFE63\u02DC]")


def _norm_cta(s: str) -> str:
    """Canonical form for CTA comparison: models routinely emit non-ASCII
    dash variants (U+2011 etc.) or stray whitespace in the verbatim line."""
    return re.sub(r"\s+", " ", _DASH_RE.sub("-", str(s))).strip()


_WORDS_PER_SEC = 2.4
_SCENE_GAP_SEC = 1.5


def _words(text: str) -> int:
    return len(re.findall(r"\w+", str(text or "")))


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

# The renderer background tint only knows these four; the model sometimes
# invents near-synonyms (dawn/noon/evening/twilight). Mapped back instead of
# failing the script, same rationale as EMOTION_ALIASES.
_TIMES = {"day", "morning", "dusk", "night"}
TIME_ALIASES = {
    "dawn": "morning",
    "early morning": "morning",
    "sunrise": "morning",
    "noon": "day",
    "midday": "day",
    "afternoon": "day",
    "evening": "dusk",
    "sunset": "dusk",
    "twilight": "dusk",
    "nighttime": "night",
    "late night": "night",
}


def normalize_emotions(package: Any, universe: Universe) -> list[str]:
    """Rewrite emotions to manifest expressions and time_of_day to the render
    set (case + alias + neutral/day fallback).

    Returns "old->new" strings for every changed value (empty if none).
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
                tod = str(item.get("time_of_day", "day")).strip().lower()
                if tod not in _TIMES:
                    target = TIME_ALIASES.get(tod, "day")
                    changed.append(f"time_of_day {item.get('time_of_day')}->{target}")
                    item["time_of_day"] = target
                dialogue = item.get("dialogue")
                if isinstance(dialogue, list):
                    for line in dialogue:
                        if isinstance(line, dict):
                            _fix(line)
    return changed


def normalize_metadata_title(package: Any) -> list[str]:
    """Deterministically fit metadata.title into the 70-char cap.

    The writer model reliably overruns (every attempt produced the same
    88-char title), and repair passes cannot be trusted to fix it — trim
    the leading hook segment(s) first (the search phrase + series suffix
    carry the SEO value), fall back to prefix-ellipsis for single-segment
    titles. Returns "old->new" strings for changed values.
    """
    if not isinstance(package, dict):
        return []
    meta = package.get("metadata")
    if not isinstance(meta, dict):
        return []
    title = str(meta.get("title", "")).strip()
    if not title or len(title) <= 70:
        return []
    parts = [p.strip() for p in title.split("|") if p.strip()]
    while len(parts) > 2 and len(" | ".join(parts)) > 70:
        parts.pop(0)
    if len(parts) == 2 and len(" | ".join(parts)) > 70:
        # keep the trailing series suffix; ellipsize the search phrase
        head, tail = parts
        budget = 70 - len(" | " + tail) - 1
        parts = [head[:budget].rstrip() + "\u2026", tail] if budget >= 8 else [tail]
    out = " | ".join(parts)
    if len(out) > 70:
        out = "\u2026" + out[-69:].lstrip()
    if not out or len(out) > 70:
        return []
    meta["title"] = out
    return [f"metadata.title {len(title)}->{len(out)}ch: {out!r}"]


def estimate_long_seconds(package: dict[str, Any]) -> float:
    spoken = 0
    for scene in package.get("scenes", []):
        if not isinstance(scene, dict):
            continue
        for line in scene.get("dialogue", []):
            if isinstance(line, dict):
                spoken += _words(line.get("text", ""))
        for line in scene.get("narration", []):
            if isinstance(line, dict):
                spoken += _words(line.get("text", ""))
    n_scenes = sum(1 for s in package.get("scenes", []) if isinstance(s, dict))
    return round(spoken / _WORDS_PER_SEC + n_scenes * _SCENE_GAP_SEC, 1)


def estimate_short_seconds(short: dict[str, Any]) -> float:
    spoken = sum(_words(l.get("text", "")) for l in short.get("dialogue", []) if isinstance(l, dict))
    return round(spoken / _WORDS_PER_SEC + 2.0, 1)


def validate_premise(p: Any, universe: Universe, *, arc_required: bool,
                     cfg: Config | None = None) -> list[str]:
    errors: list[str] = []
    banned = _banned_re(cfg)
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
    if p["learning_spine"] not in universe.spines:
        errors.append(f"learning_spine '{p['learning_spine']}' not in catalog")
    tc = p.get("thumbnail_concept", {})
    if tc.get("background") not in universe.location_ids:
        errors.append(f"thumbnail background '{tc.get('background')}' unknown location")
    for cid in tc.get("characters", [])[:]:
        if cid not in universe.character_ids:
            errors.append(f"thumbnail character '{cid}' unknown")
    moods = p.get("shorts_moods", [])
    if len(moods) != 2 or len(set(moods)) != 2 or any(m not in universe.short_moods for m in moods):
        errors.append(f"shorts_moods must be 2 different moods from {universe.short_moods}")
    crumb = p.get("arc_crumb")
    if arc_required and not crumb:
        errors.append("arc_crumb required for this episode but missing/null")
    if not arc_required and crumb:
        errors.append("arc_crumb must be null for non-arc episodes")
    if banned.search(str(p.get("premise", "")) + " " + str(p.get("hook", ""))):
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

    banned = _banned_re(cfg)
    arc_re = _arc_re(cfg)
    if pkg["schema"] != str(cfg.get("content.schema", "fernwood.episode/1")):
        errors.append(f"schema must be {cfg.get('content.schema', 'fernwood.episode/1')} (got {pkg['schema']!r})")
    if pkg["learning_spine"] not in universe.spines:
        errors.append(f"learning_spine '{pkg['learning_spine']}' not in catalog")
    if banned.search(" ".join([
        str(pkg.get("title", "")), str(pkg.get("premise", "")), str(pkg.get("hook", ""))
    ])):
        errors.append("banned word in title/premise/hook")

    scenes = pkg.get("scenes", [])
    sc_min = int(cfg.get("content.scene_count_min", 13))
    sc_max = int(cfg.get("content.scene_count_max", 18))
    if not isinstance(scenes, list) or not (sc_min <= len(scenes) <= sc_max):
        errors.append(f"scenes must be {sc_min}-{sc_max} (got {len(scenes) if isinstance(scenes, list) else 'n/a'})")
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
    times = _TIMES

    total_words = 0
    scene_word_counts: list[tuple[str, int]] = []
    for i, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict):
            errors.append(f"scene {i}: not an object ({type(scene).__name__})")
            continue
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
        ch_lo = int(cfg.get("content.scene_chars_min", 2))
        ch_hi = int(cfg.get("content.scene_chars_max", 4))
        if not isinstance(scene_chars, list) or not (ch_lo <= len(scene_chars) <= ch_hi):
            errors.append(f"{tag}: needs {ch_lo}-{ch_hi} characters")
        else:
            for c in scene_chars:
                if not isinstance(c, dict) or c.get("id") not in chars:
                    errors.append(f"{tag}: bad character entry {c!r}")
                    continue
                if c.get("position") not in positions:
                    errors.append(f"{tag}: bad position '{c.get('position')}'")
                if c.get("enter", "onscreen") not in entrances:
                    errors.append(f"{tag}: bad enter '{c.get('enter')}'")
        props_list = scene.get("props", [])
        if not isinstance(props_list, list):
            errors.append(f"{tag}: props must be a list")
            props_list = []
        for prop in props_list:
            if prop not in props:
                errors.append(f"{tag}: unknown prop '{prop}'")
        fx_list = scene.get("fx", [])
        if not isinstance(fx_list, list):
            errors.append(f"{tag}: fx must be a list")
            fx_list = []
        for f in fx_list:
            if f not in fx:
                errors.append(f"{tag}: unknown fx '{f}'")
        dialogue = scene.get("dialogue", [])
        if not isinstance(dialogue, list):
            errors.append(f"{tag}: dialogue must be a list")
            dialogue = []
        narration = scene.get("narration", [])
        if not isinstance(narration, list):
            errors.append(f"{tag}: narration must be a list")
            narration = []
        for line in dialogue:
            if not isinstance(line, dict):
                errors.append(f"{tag}: dialogue line not an object")
                continue
            sp = line.get("speaker", "")
            if sp not in chars:
                errors.append(f"{tag}: unknown speaker '{sp}'")
            if line.get("emotion", "neutral") not in exprs:
                errors.append(f"{tag}: bad emotion '{line.get('emotion')}'")
            w = _words(line.get("text", ""))
            total_words += w
            dw_max = int(cfg.get("content.max_dialogue_words", 14))
            if w > dw_max:
                errors.append(f"{tag}: dialogue line over {dw_max} words ({w})")
            text = str(line.get("text", ""))
            # The parent CTA line is policy-exempt: it addresses grown-ups
            # (docs/YOUTUBE_GROWTH.md §7), so its "subscribe" is not bait.
            if _norm_cta(text) != _norm_cta(universe.cta_text) and banned.search(text):
                errors.append(f"{tag}: banned word in dialogue: {text[:60]!r}")
        for line in narration:
            if not isinstance(line, dict):
                errors.append(f"{tag}: narration line not an object")
                continue
            total_words += _words(line.get("text", ""))
            if banned.search(line.get("text", "")):
                errors.append(f"{tag}: banned word in narration")
        scene_words = sum(_words(l.get("text", "")) for l in dialogue if isinstance(l, dict)) + sum(
            _words(l.get("text", "")) for l in narration if isinstance(l, dict)
        )
        sw_min = int(cfg.get("content.min_scene_words", 40))
        if scene_words < sw_min:
            errors.append(f"{tag}: too sparse ({scene_words} spoken words, need >={sw_min})")
        scene_word_counts.append((str(scene.get("scene_id") or i), scene_words))

    words_min = int(cfg.get("content.words_min", 1100))
    words_max = int(cfg.get("content.words_max", 1450))
    if not (words_min <= total_words <= words_max):
        errors.append(f"total spoken words {total_words} outside {words_min}-{words_max}")
        if total_words < words_min and scene_word_counts:
            thin = sorted(scene_word_counts, key=lambda kv: kv[1])[:6]
            hint = str(cfg.get("content.thin_scene_hint") or _DEFAULT_THIN_HINT)
            errors.append(hint + ", ".join(f"{name}={words}" for name, words in thin))

    # parent CTA: required verbatim as the final scene's last dialogue line
    final = scenes[-1] if isinstance(scenes, list) and scenes else {}
    final_dialogue = final.get("dialogue") if isinstance(final, dict) else None
    last_line = final_dialogue[-1] if isinstance(final_dialogue, list) and final_dialogue else {}
    if not isinstance(last_line, dict):
        last_line = {}
    if _norm_cta(last_line.get("text", "")) != _norm_cta(universe.cta_text):
        errors.append("final scene must end with the parent CTA line (universe.cta_text) "
                      "as its last dialogue entry")
    else:
        on_screen = {c.get("id") for c in final.get("characters", []) if isinstance(c, dict)}
        if last_line.get("speaker") not in on_screen:
            errors.append("CTA speaker must be a character on screen in the final scene")
        if last_line.get("emotion", "neutral") not in exprs:
            errors.append(f"CTA emotion '{last_line.get('emotion')}' not in expression set")
        cta_action = str(last_line.get("action", "")).strip()
        if not cta_action or len(cta_action.split()) > 8:
            errors.append("CTA action must be a short physical action (<=8 words)")
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
    kinds = [s.get("kind") for s in shorts if isinstance(s, dict)]
    if len(kinds) != len(shorts) or len(set(kinds)) != 2 or any(k not in universe.short_moods for k in kinds):
        errors.append(f"shorts kinds must be 2 different from {universe.short_moods}")
    for j, sh in enumerate(shorts, 1):
        stag = f"short {j}"
        if not isinstance(sh, dict):
            errors.append(f"{stag}: not an object ({type(sh).__name__})")
            continue
        if len(str(sh.get("title", ""))) > 40:
            errors.append(f"{stag}: title over 40 chars")
        if sh.get("location") not in locs:
            errors.append(f"{stag}: unknown location")
        if sh.get("camera") not in cam_moves:
            errors.append(f"{stag}: bad camera")
        if sh.get("music_mood") not in moods:
            errors.append(f"{stag}: bad music_mood")
        sh_ch_lo = int(cfg.get("content.shorts_chars_min", 1))
        sh_ch_hi = int(cfg.get("content.shorts_chars_max", 2))
        if not (sh_ch_lo <= len(sh.get("characters", [])) <= sh_ch_hi):
            errors.append(f"{stag}: needs {sh_ch_lo}-{sh_ch_hi} characters")
        for c in sh.get("characters", []):
            if c not in chars:
                errors.append(f"{stag}: unknown character '{c}'")
        lines = sh.get("dialogue", [])
        if not isinstance(lines, list):
            errors.append(f"{stag}: dialogue must be a list")
            lines = []
        sh_l_lo = int(cfg.get("content.shorts_lines_min", 4))
        sh_l_hi = int(cfg.get("content.shorts_lines_max", 6))
        if not (sh_l_lo <= len(lines) <= sh_l_hi):
            errors.append(f"{stag}: needs {sh_l_lo}-{sh_l_hi} dialogue lines")
        sh_text = " ".join(l.get("text", "") for l in lines if isinstance(l, dict)) + " " + str(sh.get("title", ""))
        if banned.search(sh_text):
            errors.append(f"{stag}: banned word")
        if arc_re is not None and arc_re.search(sh_text):
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
    if not isinstance(meta, dict):
        errors.append(f"metadata must be an object (got {type(meta).__name__})")
        meta = {}
    title = str(meta.get("title", ""))
    desc = str(meta.get("description", ""))
    tags = meta.get("tags", [])
    brand_name = str(cfg.get("channel.name") or "Fernwood Friends")
    required_phrase = str(cfg.get("channel.title_required_phrase", "Bedtime Stor"))
    tag_required = str(cfg.get("channel.tag_required", "kids"))
    if not title or len(title) > 70:
        errors.append(f"metadata.title missing or over 70 chars ({len(title)})")
    if brand_name not in title:
        errors.append(f"metadata.title must include '| {brand_name}' (brand last)")
    if required_phrase and required_phrase not in title:
        errors.append(f"metadata.title must follow the search-first formula and include "
                      f"'{required_phrase}' before the '| {brand_name}' suffix")
    if not desc or len(desc) > 500:
        errors.append(f"metadata.description missing or over 500 chars ({len(desc)})")
    if re.search(r"https?://|www\.", desc, re.I):
        errors.append("metadata.description must not contain links")
    if banned.search(desc):
        errors.append("banned word in description")
    if not isinstance(tags, list) or not (8 <= len(tags) <= 15):
        errors.append(f"metadata.tags must be 8-15 (got {len(tags) if isinstance(tags, list) else 'n/a'})")
    if tag_required and not any(tag_required.lower() in str(t).lower() for t in tags):
        errors.append(f"tags must include '{tag_required}'-oriented tag")
    return errors
