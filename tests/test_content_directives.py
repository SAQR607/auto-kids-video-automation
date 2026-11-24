"""Scene-directive schema (plan §2 seam): Groq directives → validated
scene-plan JSON for engine-js. Offline, no Groq."""

from __future__ import annotations

from app.content.directives import (
    POSES,
    SCHEMA,
    directive_messages,
    scene_plan,
    validate_directives,
)


def _valid():
    return {
        "schema": SCHEMA,
        "bible_version": "v1",
        "scenes": [
            {"scene_id": "sc01", "duration_sec": 10, "stage": {"bg": "#F3F0EA"},
             "actors": [
                 {"id": "stik", "x": 0.3,
                  "beats": [{"t": 0, "pose": "walk"},
                            {"t": 4, "pose": "idle", "x": 0.4}]},
                 {"id": "dot", "x": 0.7,
                  "beats": [{"t": 0, "pose": "idle"}, {"t": 6, "pose": "wave"}]},
             ]},
            {"scene_id": "sc02", "duration_sec": 8, "stage": {"bg": "#FFFFFF"},
             "actors": [
                 {"id": "stik", "x": 0.5, "beats": [{"t": 0, "pose": "idle"}]},
             ]},
        ],
    }


def test_valid_directives_pass():
    assert validate_directives(_valid(), bible_version="v1") == []


def test_unknown_pose_rejected():
    d = _valid()
    d["scenes"][0]["actors"][0]["beats"][0]["pose"] = "backflip"
    errors = validate_directives(d)
    assert any("pose" in e and "backflip" in e for e in errors)
    assert set(POSES) == {"idle", "wave", "walk"}  # engine-js POSES mirror


def test_non_increasing_beat_times_rejected():
    d = _valid()
    d["scenes"][0]["actors"][0]["beats"][1]["t"] = 0
    assert any("strictly increasing" in e for e in validate_directives(d))


def test_beat_beyond_duration_rejected():
    d = _valid()
    d["scenes"][1]["actors"][0]["beats"][0]["t"] = 99
    assert any("exceeds duration" in e for e in validate_directives(d))


def test_actor_x_out_of_range_rejected():
    d = _valid()
    d["scenes"][0]["actors"][0]["x"] = 1.4
    assert any("0..1" in e for e in validate_directives(d))


def test_schema_and_bible_version_mismatch_rejected():
    d = _valid()
    d["schema"] = "stickman.directives/9"
    d["bible_version"] = "v2"
    errors = validate_directives(d, bible_version="v1")
    assert any("schema" in e for e in errors)
    assert any("bible_version" in e for e in errors)


def test_duplicate_and_bad_scene_ids_rejected():
    d = _valid()
    d["scenes"][1]["scene_id"] = "sc01"
    assert any("duplicate" in e for e in validate_directives(d))
    d["scenes"][1]["scene_id"] = "scene-2"
    assert any("scNN" in e for e in validate_directives(d))


def test_empty_actors_rejected():
    d = _valid()
    d["scenes"][0]["actors"] = []
    assert any("actors" in e for e in validate_directives(d))


def test_too_many_actors_rejected():
    d = _valid()
    d["scenes"][0]["actors"].append({"id": "x", "x": 0.1,
                                     "beats": [{"t": 0, "pose": "idle"}]})
    assert any("> 2" in e for e in validate_directives(d))


def test_scene_plan_matches_engine_contract():
    d = _valid()
    plan = scene_plan(d["scenes"][0], seed=7)
    assert plan["seed"] == 7
    assert plan["duration"] == 10.0
    assert plan["stage"] == {"bg": "#F3F0EA"}
    assert len(plan["actors"]) == 2
    # engine-js buildScene contract: duration > 0, actors non-empty, beats t
    # increasing, pose in POSES (validated above, re-checked structurally here)
    assert plan["duration"] > 0
    for a in plan["actors"]:
        assert isinstance(a["x"], (int, float))
        prev = -1.0
        for b in a["beats"]:
            assert b["t"] > prev
            prev = b["t"]
            assert b["pose"] in POSES


def test_directive_prompt_never_asks_for_code():
    msgs = directive_messages(
        {"title": "Rome", "duration_target_sec": 480,
         "scenes": [{"scene_id": "sc01",
                     "dialogue": [{"text": "look at the great arena"}],
                     "narration": [{"text": "the crowd roared in the stadium"}]}]},
        bible_version="v1")
    text = msgs[0]["content"] + msgs[1]["content"]
    assert SCHEMA in text
    assert "no javascript" in text.lower()
    assert "sc01" in text
