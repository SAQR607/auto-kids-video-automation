"""Content package structural validation tests (§14, §42)."""

import json
from pathlib import Path

from app.config import Config
from app.content.universe import CTA_ACTION, CTA_EMOTION, CTA_TEXT, Universe
from app.content.validate import (
    estimate_long_seconds,
    normalize_emotions,
    validate_package,
    validate_premise,
)


def _cfg() -> Config:
    return Config(data=json.loads(Path("config/config.example.json").read_text(encoding="utf-8")),
                  path=Path("config/config.example.json"))


def _uni() -> Universe:
    return Universe()


def _line(words: int = 20) -> str:
    return " ".join(["tiny"] * words)


def _make_valid_package() -> dict:
    scenes = []
    for i in range(1, 15):
        scenes.append({
            "scene_id": f"sc{i:02d}",
            "location": "hollow_oak_village" if i % 2 else "glimmer_meadow",
            "time_of_day": "day",
            "camera": "static" if i % 3 else "push_in",
            "transition_in": "cut" if i == 1 else "fade",
            "music_mood": "happy",
            "characters": [
                {"id": "juni", "position": "left", "enter": "onscreen", "state": "idle"},
                {"id": "wren", "position": "right", "enter": "onscreen", "state": "idle"},
            ],
            "dialogue": [
                {"speaker": "juni", "text": _line(10), "emotion": "happy", "action": "waves tail"},
                {"speaker": "wren", "text": _line(10), "emotion": "curious", "action": "tilts head"},
            ],
            "narration": [{"text": _line(60)}],
            "props": ["map_scroll"],
            "fx": [],
        })
    scenes[13]["dialogue"].append({"speaker": "juni", "text": CTA_TEXT,
                                   "emotion": CTA_EMOTION, "action": CTA_ACTION})
    return {
        "schema": "fernwood.episode/1",
        "episode_id": "s01e001",
        "title": "The Smallest Light",
        "premise": "Juni helps a friend and notices something magical.",
        "learning_spine": "kindness to small things",
        "duration_target_sec": 540,
        "hook": "What is that tiny light in the grass?",
        "arc_crumb": "First Glimmer lights drift over Glimmer Meadow.",
        "scenes": scenes,
        "shorts": [
            {"short_id": "short_1", "kind": "funny", "title": "Marlow's Big Splash",
             "location": "whispering_stream", "time_of_day": "day", "camera": "static",
             "characters": ["marlow", "juni"],
             "dialogue": [
                 {"speaker": "marlow", "text": _line(12), "emotion": "happy", "action": "claps"},
                 {"speaker": "juni", "text": _line(12), "emotion": "excited", "action": "jumps"},
                 {"speaker": "marlow", "text": _line(12), "emotion": "happy", "action": "claps"},
                 {"speaker": "juni", "text": _line(12), "emotion": "curious", "action": "points"},
                 {"speaker": "marlow", "text": _line(12), "emotion": "proud", "action": "nods"},
                 {"speaker": "juni", "text": _line(12), "emotion": "happy", "action": "waves"},
             ],
             "music_mood": "happy", "duration_target_sec": 34},
            {"short_id": "short_2", "kind": "wonder", "title": "A Light Says Hello",
             "location": "glimmer_meadow", "time_of_day": "dusk", "camera": "push_in",
             "characters": ["wren"],
             "dialogue": [
                 {"speaker": "wren", "text": _line(12), "emotion": "surprised", "action": "spreads wings"},
                 {"speaker": "wren", "text": _line(12), "emotion": "curious", "action": "points"},
                 {"speaker": "wren", "text": _line(12), "emotion": "happy", "action": "hops"},
                 {"speaker": "wren", "text": _line(12), "emotion": "curious", "action": "tilts head"},
                 {"speaker": "wren", "text": _line(12), "emotion": "happy", "action": "sings"},
                 {"speaker": "wren", "text": _line(12), "emotion": "proud", "action": "fluffs feathers"},
             ],
             "music_mood": "mystery", "duration_target_sec": 34},
        ],
        "metadata": {
            "title": "A Gentle Bedtime Story About Patience for Kids | Fernwood Friends",
            "description": "A calming bedtime story for kids about patience. A tiny light appears when Juni helps a friend. Fernwood Friends makes gentle animated woodland adventures for ages 4-8. New long stories every Monday, Wednesday and Friday; new shorts every Saturday.",
            "tags": ["bedtime stories for kids", "bedtime stories for toddlers",
                     "calming bedtime stories for kids with relaxing music",
                     "gentle stories for kids", "kids stories", "animated stories for kids",
                     "woodland animals", "ages 4-8", "fernwood friends"],
        },
        "callbacks_available": [],
    }


def test_valid_package_passes():
    errors = validate_package(_make_valid_package(), _uni(), _cfg())
    assert errors == []


def test_validate_requires_parent_cta_line():
    pkg = _make_valid_package()
    pkg["scenes"][13]["dialogue"] = pkg["scenes"][13]["dialogue"][:-1]
    assert any("CTA" in e for e in validate_package(pkg, _uni(), _cfg()))


def test_cta_line_exempt_from_dialogue_word_ban():
    pkg = _make_valid_package()
    assert "subscribe" in CTA_TEXT  # the line the ban list would otherwise reject
    errors = validate_package(pkg, _uni(), _cfg())
    assert not any("banned word" in e for e in errors)


def test_cta_speaker_must_be_on_screen():
    pkg = _make_valid_package()
    pkg["scenes"][13]["dialogue"][-1]["speaker"] = "marlow"
    assert any("CTA speaker" in e for e in validate_package(pkg, _uni(), _cfg()))


def test_cta_text_must_be_verbatim():
    pkg = _make_valid_package()
    pkg["scenes"][13]["dialogue"][-1]["text"] = "Please like and subscribe, everyone!"
    assert any("CTA" in e for e in validate_package(pkg, _uni(), _cfg()))


def test_cta_accepts_unicode_dash_variant():
    pkg = _make_valid_package()
    variant = CTA_TEXT.replace("-", "\u2011")  # non-breaking hyphen, as models emit
    assert variant != CTA_TEXT
    pkg["scenes"][13]["dialogue"][-1]["text"] = variant
    errors = validate_package(pkg, _uni(), _cfg())
    assert not any("banned word" in e or "CTA" in e for e in errors)


def test_cta_accepts_stray_whitespace_variant():
    pkg = _make_valid_package()
    pkg["scenes"][13]["dialogue"][-1]["text"] = "  " + CTA_TEXT.replace(", ", ",   ") + " "
    errors = validate_package(pkg, _uni(), _cfg())
    assert not any("banned word" in e or "CTA" in e for e in errors)


def test_metadata_title_auto_shortened():
    from app.content.validate import normalize_metadata_title

    pkg = _make_valid_package()
    long_title = ("A Wonderfully Calming Bedtime Story About Gentle Patience "
                  "for Kids | Fernwood Friends")
    pkg["metadata"]["title"] = long_title
    assert len(long_title) > 70
    changes = normalize_metadata_title(pkg)
    assert changes
    out = pkg["metadata"]["title"]
    assert len(out) <= 70
    assert "Fernwood Friends" in out
    assert normalize_metadata_title(pkg) == []  # idempotent


def test_metadata_title_short_untouched():
    from app.content.validate import normalize_metadata_title

    pkg = _make_valid_package()
    before = pkg["metadata"]["title"]
    assert normalize_metadata_title(pkg) == []
    assert pkg["metadata"]["title"] == before


def test_title_requires_search_first_formula():
    pkg = _make_valid_package()
    pkg["metadata"]["title"] = "The Smallest Light | Fernwood Friends S1E01"
    errors = validate_package(pkg, _uni(), _cfg())
    assert any("Bedtime Stor" in e for e in errors)


def test_validate_survives_string_scene():
    pkg = _make_valid_package()
    pkg["scenes"][0] = "not a scene"
    errors = validate_package(pkg, _uni(), _cfg())
    assert any("not an object" in e for e in errors)


def test_validate_survives_string_dialogue_line():
    pkg = _make_valid_package()
    pkg["scenes"][0]["dialogue"][0] = "just text"
    errors = validate_package(pkg, _uni(), _cfg())
    assert any("dialogue line not an object" in e for e in errors)


def test_validate_survives_string_dialogue_list():
    pkg = _make_valid_package()
    pkg["scenes"][0]["dialogue"] = "all one string"
    errors = validate_package(pkg, _uni(), _cfg())
    assert any("dialogue must be a list" in e for e in errors)


def test_validate_survives_string_metadata():
    pkg = _make_valid_package()
    pkg["metadata"] = "all wrong"
    errors = validate_package(pkg, _uni(), _cfg())
    assert any("metadata must be an object" in e for e in errors)


def test_estimate_survives_malformed_entries():
    pkg = _make_valid_package()
    pkg["scenes"][1] = "oops"
    pkg["scenes"][2]["dialogue"] = "oops"
    pkg["scenes"][3]["narration"] = "oops"
    assert isinstance(estimate_long_seconds(pkg), float)


def test_low_word_count_names_thinnest_scenes():
    pkg = _make_valid_package()
    for scene in pkg["scenes"]:
        scene["narration"] = [{"text": _line(20)}]
    errors = validate_package(pkg, _uni(), _cfg())
    thin = [e for e in errors if "thinnest scenes" in e]
    assert thin
    assert "sc01=" in thin[0] and "=" in thin[0]
    assert any("total spoken words" in e for e in errors)


def test_script_prompt_embeds_cta_text(tmp_path):
    from app.content.memory import Memory
    from app.content.prompts import script_messages

    msgs = script_messages({"title": "t"}, Universe(), Memory(tmp_path / "story"),
                           episode_id="s01e001", episode_no=1,
                           include_arc=False, arc_crumb=None)
    assert CTA_TEXT in msgs[1]["content"]


def test_bad_emotion_rejected():
    pkg = _make_valid_package()
    pkg["scenes"][0]["dialogue"][0]["emotion"] = "calm"
    assert any("bad emotion" in e for e in validate_package(pkg, _uni(), _cfg()))


def test_normalize_emotions_repairs_invented_words():
    pkg = _make_valid_package()
    pkg["scenes"][0]["dialogue"][0]["emotion"] = "calm"
    pkg["scenes"][1]["dialogue"][1]["emotion"] = "confused"
    pkg["scenes"][2]["dialogue"][0]["emotion"] = "Thoughtful"
    pkg["shorts"][0]["dialogue"][0]["emotion"] = "blorpy"   # unknown -> neutral
    pkg["shorts"][1]["dialogue"][1]["emotion"] = "curious"  # valid -> untouched
    changed = normalize_emotions(pkg, _uni())
    assert pkg["scenes"][0]["dialogue"][0]["emotion"] == "neutral"
    assert pkg["scenes"][1]["dialogue"][1]["emotion"] == "curious"
    assert pkg["scenes"][2]["dialogue"][0]["emotion"] == "curious"
    assert pkg["shorts"][0]["dialogue"][0]["emotion"] == "neutral"
    assert pkg["shorts"][1]["dialogue"][1]["emotion"] == "curious"
    assert len(changed) == 4
    assert validate_package(pkg, _uni(), _cfg()) == []


def test_normalize_repairs_invented_time_of_day():
    pkg = _make_valid_package()
    pkg["scenes"][0]["time_of_day"] = "dawn"
    pkg["scenes"][1]["time_of_day"] = "Evening"
    pkg["shorts"][0]["time_of_day"] = "springtime"  # unknown -> day
    pkg["shorts"][1]["time_of_day"] = "dusk"        # valid -> untouched
    changed = normalize_emotions(pkg, _uni())
    assert pkg["scenes"][0]["time_of_day"] == "morning"
    assert pkg["scenes"][1]["time_of_day"] == "dusk"
    assert pkg["shorts"][0]["time_of_day"] == "day"
    assert pkg["shorts"][1]["time_of_day"] == "dusk"
    assert len(changed) == 3
    assert validate_package(pkg, _uni(), _cfg()) == []


def test_six_line_short_passes_two_line_short_rejected():
    pkg = _make_valid_package()
    assert validate_package(pkg, _uni(), _cfg()) == []
    pkg["shorts"][1]["dialogue"] = pkg["shorts"][1]["dialogue"][:2]
    assert any("4-6 dialogue lines" in e for e in validate_package(pkg, _uni(), _cfg()))


def test_estimate_in_range():
    est = estimate_long_seconds(_make_valid_package())
    assert 480 <= est <= 600


def test_unknown_location_rejected():
    pkg = _make_valid_package()
    pkg["scenes"][0]["location"] = "hogwarts"
    assert any("unknown location" in e for e in validate_package(pkg, _uni(), _cfg()))


def test_banned_word_rejected():
    pkg = _make_valid_package()
    pkg["scenes"][0]["dialogue"][0]["text"] = "that was so scary and dangerous"
    errs = validate_package(pkg, _uni(), _cfg())
    assert any("banned word" in e for e in errs)


def test_three_shorts_rejected():
    pkg = _make_valid_package()
    pkg["shorts"].append(pkg["shorts"][0])
    assert any("exactly 2 shorts" in e for e in validate_package(pkg, _uni(), _cfg()))


def test_same_short_moods_rejected():
    pkg = _make_valid_package()
    pkg["shorts"][1]["kind"] = "funny"
    assert any("different" in e for e in validate_package(pkg, _uni(), _cfg()))


def test_arc_words_in_short_rejected():
    pkg = _make_valid_package()
    pkg["shorts"][0]["dialogue"][0]["text"] = "Let us visit the cave today my friend."
    assert any("season arc" in e for e in validate_package(pkg, _uni(), _cfg()))


def test_link_in_description_rejected():
    pkg = _make_valid_package()
    pkg["metadata"]["description"] = "Watch here https://example.com now friends!"
    assert any("links" in e for e in validate_package(pkg, _uni(), _cfg()))


def test_word_count_bounds_enforced():
    pkg = _make_valid_package()
    pkg["scenes"][0]["narration"] = []
    pkg["scenes"][0]["dialogue"] = []
    assert any("spoken words" in e for e in validate_package(pkg, _uni(), _cfg()))


def test_premise_arc_required():
    uni = _uni()
    base = {"title": "T", "premise": "P", "learning_spine": "patience", "hook": "H",
            "arc_crumb": None,
            "thumbnail_concept": {"background": "glimmer_meadow", "characters": ["juni"],
                                  "expression": "happy", "text": "A LIGHT"},
            "shorts_moods": ["funny", "wonder"]}
    assert validate_premise(base, uni, arc_required=True)  # null crumb -> error
    base["arc_crumb"] = "Some crumb"
    assert validate_premise(base, uni, arc_required=True) == []
    assert validate_premise(base, uni, arc_required=False)  # non-null crumb on non-arc -> error
    base["arc_crumb"] = None
    assert validate_premise(base, uni, arc_required=False) == []
