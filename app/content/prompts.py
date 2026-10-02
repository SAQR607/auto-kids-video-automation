"""Prompt builders for premise + full episode package generation."""

from __future__ import annotations

import json
from typing import Any

from .memory import Memory
from .universe import SHORT_MOODS, SPINES, Universe

SYSTEM_WRITER = """You are the head writer of "Fernwood Friends", a gentle animated YouTube series for children ages 4-8 (Made for Kids, English only).
Warm, curious, gently funny — never scary, violent, sarcastic or preachy. One learning spine shown by action, never lectured. Problems resolve inside the episode.
Output a single minified JSON object. No markdown, no commentary."""

PREMISE_SCHEMA = """{
  "title": "max 62 chars, curiosity gap, no spoilers, no episode number",
  "premise": "2-3 sentences: what happens, why it matters to a child",
  "learning_spine": "one of the catalog spines exactly",
  "hook": "the concrete opening question/moment in one sentence",
  "arc_crumb": "required arc line from the brief, or null if none",
  "thumbnail_concept": {
    "background": "location id",
    "characters": ["1-2 character ids"],
    "expression": "expression id",
    "text": "max 5 words"
  },
  "shorts_moods": ["mood1", "mood2"]
}"""


def premise_messages(
    universe: Universe,
    memory: Memory,
    *,
    episode_id: str,
    episode_no: int,
    include_arc: bool,
    arc_crumb: str | None,
) -> list[dict[str, str]]:
    user = f"""Create the PREMISE for a new episode.

episode_id: {episode_id} (season 1, episode {episode_no})
Learning spines (pick one NOT in recent memory): {json.dumps(SPINES)}
Short moods pool (pick 2 DIFFERENT): {json.dumps(SHORT_MOODS)}
Required arc crumb (or null): {json.dumps(arc_crumb)}

{memory.context_block()}

{universe.context_block(include_arc=include_arc, arc_crumb=arc_crumb)}

Return JSON matching EXACTLY this shape (fixed keys):
{PREMISE_SCHEMA}"""
    return [
        {"role": "system", "content": SYSTEM_WRITER},
        {"role": "user", "content": user},
    ]


SCRIPT_BRIEF = """Write the COMPLETE episode package JSON for this premise:

__PREMISE_JSON__

OUTPUT SHAPE (strict):
- scenes array MUST contain EXACTLY 14 scene objects, ids sc01..sc14.
- EXACTLY 5 dialogue lines per scene (each 8-14 words) + EXACTLY 1 narration block of 35-45 words.
- That is 65-115 spoken words per scene, 1150-1400 total. Sparse scenes are rejected.
- Output MINIFIED JSON: one line, no indentation, no newlines outside strings.
- The example shows only ONE scene for style — it is NOT the output size.

EXAMPLE SCENE (style + density):
{"scene_id":"sc03","location":"hollow_oak_village","time_of_day":"day","camera":"static","transition_in":"fade","music_mood":"happy","characters":[{"id":"juni","position":"left","enter":"onscreen","state":"walk"},{"id":"bramble","position":"right","enter":"onscreen","state":"idle"}],"dialogue":[{"speaker":"juni","text":"Bramble! Can you help me lift this heavy acorn cap?","emotion":"excited","action":"tugs the cap"},{"speaker":"bramble","text":"Measure twice, dig once. Let me look it over.","emotion":"neutral","action":"measures with stick"},{"speaker":"juni","text":"It is much too big for the little round door.","emotion":"sad","action":"sighs deeply"},{"speaker":"bramble","text":"Then we make the doorway bigger, you and me.","emotion":"happy","action":"taps the frame"},{"speaker":"juni","text":"Yes! We can do it together, friend.","emotion":"excited","action":"claps paws"}],"narration":[{"text":"Juni huffed and set her leaf cap straight. Bramble smiled and reached for his twig tools. So the two friends began to work, line by careful line, while the village lamps blinked on."}],"props":["tool_belt"],"fx":[]}

FIELD RULES:
- Scene order follows the beat template above; learning spine demonstrated by actions in payoff scenes.
- Each scene: scene_id, location, time_of_day (day/morning/dusk/night), camera, transition_in, music_mood, characters, dialogue, narration, props, fx.
- characters: 2-4 objects {"id": char id, "position": left/center/right/far_left/far_right, "enter": onscreen/enter_left/enter_right, "state": initial sprite state}.
- dialogue entry: {"speaker": char id, "text": "...", "emotion": expression id, "action": "physical action <=8 words"}.
- narration: [{"text": "35-45 words"}].
- props = physical objects ONLY (leaf_cap, map_scroll, lantern, ...) from the props list. fx = visual effects (glimmer_sparkle, leaf_swirl, rain_streak, ripple_ring, dust_motes, lamp_glow, speech_pop, endcard_wave) from the fx list. NEVER put fx ids or location ids in "props".
- Exactly 2 shorts, SELF-CONTAINED for vertical 1080x1920 (no arc references, works without seeing the long):
  {"short_id": "short_1", "kind": "<assigned mood>", "title": "<=40 chars", "location": id,
   "time_of_day": "...", "camera": "...", "characters": ["1-2 ids"],
   "dialogue": [{"speaker": "...", "text": "...", "emotion": "...", "action": "..."}],
   "music_mood": "...", "duration_target_sec": 34}
  EXACTLY 6 dialogue lines each (10-16 words), 60-110 spoken words total per short.
- metadata: {"title": "<=70 chars ending with \\"| Fernwood Friends S1E__\\" (real episode number)",
  "description": "<=500 chars: what happens + series line \\"Fernwood Friends - gentle animated woodland adventures for ages 4-8\\" + schedule line. No links, no subscribe/like/comment words.",
  "tags": ["8-15 tags: kids stories, animated stories for kids, wholesome kids video, ages 4-8, woodland animals, preschool stories, kids animation + episode-specific"]}
- Top-level "title": curiosity title WITHOUT series suffix (<=62 chars).

Return ONLY the JSON with ALL top-level keys:
schema ("fernwood.episode/1"), episode_id, title, premise, learning_spine,
duration_target_sec, hook, arc_crumb (or null), scenes, shorts (exactly 2),
metadata, callbacks_available (<=3 strings or [])."""


def script_messages(
    premise: dict[str, Any],
    universe: Universe,
    memory: Memory,
    *,
    episode_id: str,
    episode_no: int,
    include_arc: bool,
    arc_crumb: str | None,
) -> list[dict[str, str]]:
    brief = SCRIPT_BRIEF.replace("__PREMISE_JSON__", json.dumps(premise, ensure_ascii=False))
    user = f"""{brief}

episode_id to use: {episode_id} (season 1, episode {episode_no})

{memory.context_block()}

{universe.context_block(include_arc=include_arc, arc_crumb=arc_crumb)}"""
    return [
        {"role": "system", "content": SYSTEM_WRITER},
        {"role": "user", "content": user},
    ]


def repair_messages(
    stage: str,
    errors: list[str],
    previous: str,
    base_messages: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Bounded repair pass: same task + explicit error list (§25 bounded retries).

    The previous output is included so errors can be fixed in context (input
    grows, so the repair call uses a reduced max_tokens budget).
    """
    feedback = (
        f"Your previous {stage} output had validation errors:\n- "
        + "\n- ".join(errors[:12])
        + "\n\nReturn the FULL corrected minified JSON object only (no fences, no commentary). "
        "Fix every listed error while keeping the story spirit."
    )
    return base_messages + [
        {"role": "assistant", "content": previous},
        {"role": "user", "content": feedback},
    ]
