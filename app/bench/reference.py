"""Golden reference episode: fixed content, real cast — identity preserved.

Deterministic by construction (no Groq): metric deltas across runs reflect
pipeline changes only. Content mirrors production scene structure (same
locations, characters, props, fx, cameras, moods, voices) so the benchmark
exercises the real compositing/audio code paths.

Probe design (why the scenes look the way they do):
  sc_probe_static — camera static, no fx, narration only: frames are pixel
      stable, so the flicker metric isolates encoder/tint instability.
  sc_probe_pan    — camera pan_l, dialogue + narration, no fx: measures
      background-motion continuity (quantization stepping) on the top crop.
  sc_probe_push   — camera push_in, dusk, fx sparkle, 3 characters: covers
      zoom compositing, FX overlay, color spread (colorfulness) and muxing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REFERENCE_ID = "bench001"

SCENES: list[dict[str, Any]] = [
    {
        "scene_id": "sc_probe_static",
        "location": "glimmer_meadow",
        "time_of_day": "morning",
        "camera": "static",
        "transition_in": "fade",
        "music_mood": "calm",
        "characters": [
            {"id": "juni", "position": "center", "enter": "onscreen", "state": "idle"},
            {"id": "bramble", "position": "right", "enter": "onscreen", "state": "idle"},
        ],
        "dialogue": [],
        "narration": [
            {"text": "The morning sun settled over Glimmer Meadow as Juni and Bramble "
                     "watched the valley wake, listening to the soft breeze comb through "
                     "the tall grass."}
        ],
        "props": [],
        "fx": [],
    },
    {
        "scene_id": "sc_probe_pan",
        "location": "hollow_oak_village",
        "time_of_day": "morning",
        "camera": "pan_l",
        "transition_in": "cut",
        "music_mood": "happy",
        "characters": [
            {"id": "juni", "position": "center", "enter": "onscreen", "state": "idle"},
            {"id": "willowby", "position": "left", "enter": "onscreen", "state": "idle"},
            {"id": "bramble", "position": "right", "enter": "onscreen", "state": "idle"},
        ],
        "dialogue": [
            {"speaker": "juni", "text": "Willowby, did you hear the bell tree chiming at dawn?",
             "emotion": "curious", "action": "looks up"},
            {"speaker": "willowby", "text": "I did, young one. It rings when the valley "
             "learns something new.", "emotion": "curious", "action": "nods slowly"},
            {"speaker": "bramble", "text": "Then let us find what the valley learned today!",
             "emotion": "excited", "action": "hops in place"},
            {"speaker": "juni", "text": "Maybe the pebbles from yesterday have a story to tell.",
             "emotion": "amazed", "action": "points ahead"},
        ],
        "narration": [
            {"text": "The three friends walked beneath the great oak, past lantern posts and "
                     "window boxes, following the bell tree's gentle song toward the square."}
        ],
        "props": ["leaf_cap"],
        "fx": [],
    },
    {
        "scene_id": "sc_probe_push",
        "location": "glimmer_meadow",
        "time_of_day": "dusk",
        "camera": "push_in",
        "transition_in": "fade",
        "music_mood": "discovery",
        "characters": [
            {"id": "juni", "position": "center", "enter": "onscreen", "state": "idle"},
            {"id": "bramble", "position": "left", "enter": "onscreen", "state": "idle"},
            {"id": "marlow", "position": "right", "enter": "onscreen", "state": "idle"},
        ],
        "dialogue": [
            {"speaker": "marlow", "text": "The sky is turning violet over the pebbles.",
             "emotion": "curious", "action": "adjusts spectacles"},
            {"speaker": "bramble", "text": "Sparkles are waking up again, just like last night.",
             "emotion": "amazed", "action": "clutches twig_staff"},
            {"speaker": "juni", "text": "Let us watch together until the first star appears.",
             "emotion": "happy", "action": "sits down"},
        ],
        "narration": [
            {"text": "Dusk painted the meadow in warm violet as the friends settled side by "
                     "side, waiting for the sky to sprinkle its first silver star."}
        ],
        "props": ["blue_pebble", "leaf_cap"],
        "fx": ["glimmer_sparkle"],
    },
]

PACKAGE: dict[str, Any] = {
    "schema": "fernwood.episode/1",
    "episode_id": REFERENCE_ID,
    "title": "Benchmark Reference: Morning in Glimmer Meadow",
    "premise": "Fixed reference episode for automated quality benchmarking.",
    "learning_spine": "curiosity and kindness",
    "duration_target_sec": 55,
    "hook": "Juni and Bramble listen to the valley wake.",
    "arc_crumb": None,
    "thumbnail_concept": {
        "background": "glimmer_meadow",
        "characters": ["fern", "juni"],
        "expression": "curious",
        "text": "Bench Probe",
    },
    "scenes": SCENES,
    "metadata": {
        "title": "Benchmark Reference | Fernwood Friends",
        "description": "Internal benchmark reference episode (not published).",
        "tags": ["benchmark"],
    },
    "callbacks_available": [],
}


def reference_texts() -> list[str]:
    """Expected speech texts in audio order (per scene: dialogue, then narration)
    — must mirror audio/mix.py `_scene_speech` ordering for WER."""
    texts: list[str] = []
    for scene in SCENES:
        texts.extend(d.get("text", "") for d in scene.get("dialogue", []))
        texts.extend(n.get("text", "") for n in scene.get("narration", []))
    return [t for t in texts if t.strip()]


def write_reference(state_root: Path) -> Path:
    """Write package.json into the isolated bench state root."""
    base = Path(state_root) / "episodes" / REFERENCE_ID
    base.mkdir(parents=True, exist_ok=True)
    pkg_file = base / "package.json"
    pkg_file.write_text(json.dumps(PACKAGE, indent=2, ensure_ascii=False), encoding="utf-8")
    return pkg_file
