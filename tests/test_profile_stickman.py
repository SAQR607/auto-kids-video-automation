"""Profile tests: the 'stickman' channel profile is fully isolated and valid.

Run under APP_PROFILE=stickman via monkeypatch; the default profile must keep
its Fernwood behavior (asserted here by flipping the env back).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import Config, load_config, profile
from app.content.memory import Memory
from app.content.universe import Universe
from app.content.validate import validate_package
from app.render.art.backend import art_module
from app.youtube import metadata as md

ROOT = Path(__file__).resolve().parent.parent
UNIVERSE_DIR = ROOT / "universe_stickman"
CTA_TEXT = ("We post new tales every Sunday, Tuesday and Thursday - "
            "subscribe to catch them!")


@pytest.fixture
def stickman(monkeypatch):
    monkeypatch.setenv("APP_PROFILE", "stickman")
    return load_config()


# ------------------------------------------------------------------ config --

def test_profile_config_loads(stickman):
    assert profile() == "stickman"
    assert stickman.get("channel.name") == "Stickman Stories"
    assert stickman.get("channel.made_for_kids") is False
    assert stickman.get("channel.title_required_phrase") == ""
    assert stickman.get("channel.tag_required") == "stickman"
    assert stickman.get("channel.default_character") == "stik"
    assert stickman.get("content.schema") == "stickman.episode/1"
    assert stickman.get("content.short_schema") == "stickman.short/1"


def test_profile_paths_isolated(stickman):
    assert stickman.get("paths.state") == "state_stickman"
    assert stickman.get("paths.workspace") == "workspace_stickman"
    assert stickman.get("paths.assets") == "assets_stickman"
    assert stickman.get("paths.universe") == "universe_stickman"


def test_profile_schedule(stickman):
    longs = [(s["day"], s["time_utc"]) for s in stickman.get("schedule.long")]
    assert longs == [("sunday", "16:00"), ("tuesday", "16:00"), ("thursday", "16:00")]
    shorts = [(s["day"], s["time_utc"]) for s in stickman.get("schedule.shorts")]
    assert shorts == [("saturday", "19:00")]


def test_profile_duration_and_content_knobs(stickman):
    assert stickman.get("duration.long_min_sec") == 420
    assert stickman.get("duration.long_max_sec") == 540
    assert stickman.get("content.scene_count_min") == 11
    assert stickman.get("content.scene_count_max") == 14
    assert stickman.get("content.scene_chars_max") == 2
    assert stickman.get("content.arc_tokens") == []
    assert stickman.get("content.shorts_per_long") == 2


def test_profile_voices(stickman):
    v = stickman.voices
    assert v["narrator"] == "am_fenrir"
    assert v["stik"] == "am_adam"
    assert v["dot"] == "af_kore"


# ---------------------------------------------------------------- universe --

def test_universe_rules(stickman):
    uni = Universe(universe_dir=UNIVERSE_DIR)
    assert uni.arc_crumbs == {}                      # explicit empty = no arc
    assert "courage" in uni.spines and "Fernwood" not in json.dumps(uni.spines)
    assert uni.cta_text == CTA_TEXT
    assert uni.cta_emotion == "happy"
    assert "Stickman Stories" in uni.writer_system
    assert '"arc_crumb": "always null' in uni.premise_schema
    assert uni.brief.startswith("Write the COMPLETE episode package JSON")
    assert "EXACTLY 13 scene objects" in uni.brief
    assert "| Stickman Stories" in uni.brief
    assert uni.character_ids == ["stik", "dot"]
    assert set(uni.location_ids) == {
        "village_lane", "market_square", "river_dock",
        "workshop_street", "hall_of_columns", "hilltop_road",
    }
    assert set(uni.prop_ids) == {
        "scroll", "oil_lamp", "jug", "basket", "crate",
        "oar", "hammer", "ladder", "lantern", "signpost",
        "rope", "stone",
    }


def test_art_props_cover_universe(stickman):
    props = art_module("props")
    uni = Universe(universe_dir=UNIVERSE_DIR)
    assert set(uni.prop_ids) <= set(props.PROPS)
    assert props.get_prop("rope").size == (320, 320)
    assert props.get_prop("stone").size == (320, 320)


def test_universe_context_block_no_arc(stickman):
    uni = Universe(universe_dir=UNIVERSE_DIR)
    block = uni.context_block(include_arc=False, arc_crumb=None)
    assert "no season mystery" in block
    assert "STICKMAN STORIES WORLD" in block
    assert "no cave, no compass" not in block           # Fernwood arc text absent


def test_prompts_use_profile_text(stickman):
    from app.content.prompts import premise_messages, script_messages

    uni = Universe(universe_dir=UNIVERSE_DIR)
    mem = Memory(ROOT / "state_stickman" / "story_memory")
    premise = {"title": "T", "premise": "P", "learning_spine": "courage",
               "hook": "H", "arc_crumb": None,
               "thumbnail_concept": {"background": "market_square",
                                     "characters": ["stik"], "expression": "curious",
                                     "text": "T"},
               "shorts_moods": ["discovery", "lesson"]}
    pm = premise_messages(uni, mem, episode_id="s01e001", episode_no=1,
                          include_arc=False, arc_crumb=None)
    assert "Stickman Stories" in pm[0]["content"]
    assert "Fernwood" not in pm[0]["content"] + pm[1]["content"]
    assert "always null" in pm[1]["content"]            # premise_schema override

    sm = script_messages(premise, uni, mem, episode_id="s01e001", episode_no=1,
                         include_arc=False, arc_crumb=None)
    user = sm[1]["content"]
    assert "EXACTLY 13 scene objects" in user
    assert CTA_TEXT in user                              # placeholder replaced
    assert "__CTA_TEXT__" not in user
    assert "__EXPRESSIONS__" not in user
    assert '"stickman.episode/1"' in user
    assert "Fernwood" not in sm[0]["content"] + user


# -------------------------------------------------------------------- art --

def test_art_dispatch_profile(stickman):
    chars = art_module("characters")
    locs = art_module("locations")
    props = art_module("props")
    assert chars.SPECIES == ("stik", "dot")
    assert "market_square" in locs.LOCATIONS
    assert "scroll" in props.PROPS
    sp = chars.get_sprite("stik", "walk", "happy", 2)
    assert sp.size == (600, 760)


def test_art_dispatch_default_profile(monkeypatch):
    monkeypatch.delenv("APP_PROFILE", raising=False)
    assert art_module("characters").SPECIES == (
        "juni", "bramble", "marlow", "wren", "willowby", "fern", "pipkin",
    )
    assert art_module("locations").paint_location("hollow_oak_village", "day")


# --------------------------------------------------------------- metadata --

def test_metadata_bodies(stickman):
    assert md.made_for_kids(stickman) is False
    assert md.brand(stickman) == "Stickman Stories"
    assert "bedtime" not in " ".join(md.core_tags(stickman)).lower()
    assert "stickman stories" in [t.lower() for t in md.core_tags(stickman)]
    assert md.short_keyword_phrase(stickman) == "Animated History Story"

    pkg = {"title": "T", "metadata": {"title": "How the Wall Was Built | Stickman Stories",
                                      "description": "An animated history story about a wall.",
                                      "tags": ["animated history", "stickman stories"]}}
    cat = str(stickman.get("channel.youtube_category_id"))   # publish._category_id path
    body = md.long_body(pkg, private=False, category_id=cat, cfg=stickman)
    assert body["snippet"]["categoryId"] == "27"
    assert body["status"]["selfDeclaredMadeForKids"] is False
    assert body["snippet"]["tags"][0] == "animated history"

    short = {"title": "One Wall, One Winter", "dialogue": [{"text": "They built it through the snow."}]}
    sbody = md.short_body(short, private=False, cfg=stickman)
    assert sbody["snippet"]["title"].endswith("| Animated History Story | Stickman Stories")
    assert sbody["status"]["selfDeclaredMadeForKids"] is False


# --------------------------------------------------------------- validate --

def _scene(i: int) -> dict:
    words = "one two three four five six seven eight nine ten"
    return {
        "scene_id": f"sc{i:02d}",
        "location": "market_square",
        "time_of_day": "day",
        "camera": "static",
        "transition_in": "fade",
        "music_mood": "discovery",
        "characters": [
            {"id": "stik", "position": "left", "enter": "onscreen", "state": "idle"},
            {"id": "dot", "position": "right", "enter": "onscreen", "state": "idle"},
        ],
        "dialogue": [
            {"speaker": "stik", "text": words, "emotion": "curious", "action": "points at the map"},
            {"speaker": "dot", "text": words, "emotion": "surprised", "action": "leans closer"},
            {"speaker": "stik", "text": words, "emotion": "determined", "action": "traces the road"},
            {"speaker": "dot", "text": words, "emotion": "happy", "action": "nods along"},
            {"speaker": "stik", "text": words, "emotion": "neutral", "action": "rolls the scroll"},
        ],
        "narration": [{"text": ("Many years ago this busy street connected two distant "
                                "harbors where merchants traded spices cloth and stories "
                                "while the city bells marked every hour of the working day.")}],
        "props": ["scroll"],
        "fx": [],
    }


def _short(i: int, kind: str) -> dict:
    words = "one two three four five six seven eight nine ten eleven twelve"
    return {
        "short_id": f"short_{i}",
        "kind": kind,
        "title": f"Tiny Tale Number {i} Of The Week",
        "location": "hilltop_road",
        "time_of_day": "day",
        "camera": "static",
        "characters": ["stik", "dot"],
        "dialogue": [
            {"speaker": "stik", "text": words, "emotion": "curious", "action": "shields his eyes"},
            {"speaker": "dot", "text": words, "emotion": "amazed", "action": "hops in place"},
            {"speaker": "stik", "text": words, "emotion": "happy", "action": "waves ahead"},
            {"speaker": "dot", "text": words, "emotion": "proud", "action": "puffs up"},
            {"speaker": "stik", "text": words, "emotion": "brave", "action": "steps forward"},
            {"speaker": "dot", "text": words, "emotion": "excited", "action": "races along"},
        ],
        "music_mood": "adventure",
        "duration_target_sec": 34,
    }


def _package() -> dict:
    scenes = [_scene(i) for i in range(1, 14)]
    scenes[-1]["dialogue"][-1] = {
        "speaker": "stik", "text": CTA_TEXT, "emotion": "happy",
        "action": "waves to the camera",
    }
    return {
        "schema": "stickman.episode/1",
        "episode_id": "s01e001",
        "title": "How the Great Road Connected Two Harbors",
        "premise": "Merchants build a road.",
        "learning_spine": "teamwork",
        "duration_target_sec": 480,
        "hook": "the road that changed two harbors",
        "arc_crumb": None,
        "thumbnail_concept": {"background": "market_square",
                              "characters": ["stik", "dot"], "expression": "amazed",
                              "text": "The Great Road"},
        "scenes": scenes,
        "shorts": [_short(1, "discovery"), _short(2, "lesson")],
        "metadata": {
            "title": "How the Great Road Was Built | Stickman Stories",
            "description": ("An animated history story about the road that linked two busy "
                            "harbors, from Stickman Stories. Stickman Stories - animated "
                            "stick-figure retellings of history's greatest stories. New stories "
                            "every Sunday, Tuesday and Thursday; new shorts every Saturday. "
                            "Like and subscribe for more."),
            "tags": ["animated history", "history stories", "animated history videos",
                     "world history", "history explained", "stick figure animation",
                     "stickman stories", "historical stories", "roman roads", "trade routes"],
        },
        "callbacks_available": [],
    }


def test_validate_package_passes(stickman):
    uni = Universe(universe_dir=UNIVERSE_DIR)
    errors = validate_package(_package(), uni, stickman)
    assert errors == []


def test_validate_rejects_fernwood_schema(stickman):
    uni = Universe(universe_dir=UNIVERSE_DIR)
    pkg = _package()
    pkg["schema"] = "fernwood.episode/1"
    errors = validate_package(pkg, uni, stickman)
    assert any("schema must be stickman.episode/1" in e for e in errors)


def test_validate_rejects_fernwood_world(stickman):
    uni = Universe(universe_dir=UNIVERSE_DIR)
    pkg = _package()
    pkg["scenes"][0]["location"] = "hollow_oak_village"
    pkg["scenes"][0]["props"] = ["leaf_cap"]
    errors = validate_package(pkg, uni, stickman)
    assert any("unknown location" in e for e in errors)
    assert any("unknown prop" in e for e in errors)


def test_validate_arc_guard_off_for_profile(stickman):
    # content.arc_tokens = [] for this profile: Fernwood arc words (cave, ...)
    # are NOT banned in ch2 shorts — the guard is intentionally disabled.
    uni = Universe(universe_dir=UNIVERSE_DIR)
    pkg = _package()
    pkg["shorts"][0]["title"] = "The Secret Of The Cave Entrance"
    assert validate_package(pkg, uni, stickman) == []
