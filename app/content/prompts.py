"""Prompt builders for premise + full episode package generation."""

from __future__ import annotations

import json
from typing import Any

from .memory import Memory
from .universe import Universe

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
Learning spines (pick one NOT in recent memory): {json.dumps(universe.spines)}
Short moods pool (pick 2 DIFFERENT): {json.dumps(universe.short_moods)}
Required arc crumb (or null): {json.dumps(arc_crumb)}
Thumbnail expressions (use exactly one for thumbnail_concept.expression): {json.dumps(universe.manifest.get("expressions", []))}

{memory.context_block()}

{universe.context_block(include_arc=include_arc, arc_crumb=arc_crumb)}

Return JSON matching EXACTLY this shape (fixed keys):
{PREMISE_SCHEMA}"""
    return [
        {"role": "system", "content": universe.writer_system or SYSTEM_WRITER},
        {"role": "user", "content": user},
    ]


SCRIPT_BRIEF = """Write the COMPLETE episode package JSON for this premise:

__PREMISE_JSON__

OUTPUT SHAPE (strict):
- scenes array MUST contain EXACTLY 14 scene objects, ids sc01..sc14.
- EXACTLY 5 dialogue lines per scene (each 9-11 words) + EXACTLY 1 narration block of 35-40 words.
- That is 80-95 spoken words per scene; AIM FOR ~90 words per scene (~1260 total). Hard limits: total 1100-1450 words, estimated duration 480-600s — scripts under ~1150 words are rejected as sparse, so never write thin scenes.
- Output MINIFIED JSON: one line, no indentation, no newlines outside strings.
- The example shows only ONE scene for style — it is NOT the output size.

EXAMPLE SCENE (style — shows ONE scene, not the output size; your real scenes need ALL 5 dialogue lines + full 35-40 word narration):
{"scene_id":"sc03","location":"hollow_oak_village","time_of_day":"day","camera":"static","transition_in":"fade","music_mood":"happy","characters":[{"id":"juni","position":"left","enter":"onscreen","state":"walk"},{"id":"bramble","position":"right","enter":"onscreen","state":"idle"}],"dialogue":[{"speaker":"juni","text":"Bramble! Can you help me lift this heavy acorn cap?","emotion":"excited","action":"tugs the cap"},{"speaker":"bramble","text":"Measure twice, dig once. Let me look it over.","emotion":"neutral","action":"measures with stick"}],"narration":[{"text":"Juni huffed and set her leaf cap straight. Bramble smiled and reached for his twig tools. So the two friends began to work, line by careful line, while the village lamps blinked on."}],"props":["tool_belt"],"fx":[]}

FIELD RULES:
- Scene order follows the beat template above; learning spine shown by actions in payoff scenes.
- Each scene: scene_id, location, time_of_day (EXACTLY one of day/morning/dusk/night — never dawn, noon, evening, twilight), camera, transition_in, music_mood, characters, dialogue, narration, props, fx.
- music_mood MUST be exactly one of the music_moods ids in ALLOWED IDS — never invent one ('endcard', 'credits', 'outro' are NOT valid ids).
- characters: 2-4 objects {"id": char id, "position": left/center/right/far_left/far_right, "enter": onscreen/enter_left/enter_right, "state": initial sprite state}.
- dialogue entry: {"speaker": char id, "text": "9-11 words (hard limits 5-14 — never 2-4 word exclamations like 'Goodnight, valley!')", "emotion": expression id, "action": "physical action <=8 words"}.
- CTA (required, verbatim): the LAST dialogue entry of the FINAL scene (sc14) is exactly {"speaker":"<any character on screen in sc14>","text":"__CTA_TEXT__","emotion":"__CTA_EMOTION__","action":"__CTA_ACTION__"} — it replaces the 5th dialogue line; never reword or omit it.
- sc14 is a NORMAL full scene, NOT a solo end card: EXACTLY 2-4 characters on screen, a regular music_mood from the allowed list, full 5 dialogue lines + 35-40 word narration. The CTA line simply IS its 5th dialogue entry.
- EXPRESSIONS (closed list): __EXPRESSIONS__. emotion MUST be exactly one of these — the sprite sheet has no others. NEVER invent synonyms (calm, confused, thoughtful, angry, scared); one invented emotion rejects the whole script.
- narration: [{"text": "35-40 words"}].
- props = physical objects ONLY from the PROPS list (leaf_cap, map_scroll, lantern, ...). fx = visual effects (glimmer_sparkle, leaf_swirl, ...) from the fx list. NEVER put fx ids, location ids or invented/arc items (heart_stone, compass, cave, ...) in "props" — every prop id must exist in the PROPS list or the script is rejected.
- Exactly 2 shorts, SELF-CONTAINED for vertical 1080x1920 (no arc references, works without seeing the long): shorts must NEVER contain the arc-bible words cave, compass, heart stone, root door or pebble stack — not in dialogue, not in the title.
  {"short_id":"short_1","kind":"<assigned mood>","title":"<=40 chars","location":id,"time_of_day":"day/morning/dusk/night","camera":"...","characters":["EXACTLY 1-2 ids, never 3"],"dialogue":[{"speaker":"...","text":"...","emotion":"expression from EXPRESSIONS","action":"..."}],"music_mood":"...","duration_target_sec":34}
  EXACTLY 6 dialogue lines each (10-16 words), 60-96 spoken words total per short.
- metadata: {"title":"<=70 chars EXACTLY '<Gentle|Calming> Bedtime Story About <2-4 word virtue taken from the learning_spine, e.g. Patience, Quiet Kindness, Asking for Help> for Kids | Fernwood Friends' — search phrase FIRST, brand LAST, never an episode code (no S1E__)","description":"<=500 chars: FIRST sentence uses 'bedtime story for kids' naturally (e.g. 'A calming bedtime story for kids about <virtue> from Fernwood Friends') + what happens + naturally weave in a second search phrase (e.g. bedtime stories for toddlers) + series line Fernwood Friends - gentle animated woodland adventures for ages 4-8 + schedule line exactly 'New long stories every Monday, Wednesday and Friday; new shorts every Saturday.' No links, no subscribe/like/comment words.","tags":["8-12 tags starting with: bedtime stories for kids, bedtime stories for toddlers, calming bedtime stories for kids with relaxing music, gentle stories for kids, kids stories, animated stories for kids, woodland animals, ages 4-8, fernwood friends — plus 0-3 episode-theme tags"]}
- Top-level "title": curiosity title WITHOUT series suffix (<=62 chars).

Return ONLY the JSON with ALL top-level keys:
schema ("fernwood.episode/1"), episode_id, title, premise, learning_spine,
duration_target_sec, hook, arc_crumb (or null), thumbnail_concept (copy the
object from the premise above), scenes, shorts (exactly 2),
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
    brief = (universe.brief or SCRIPT_BRIEF)
    brief = (brief
             .replace("__PREMISE_JSON__", json.dumps(premise, ensure_ascii=False))
             .replace("__EXPRESSIONS__", json.dumps(universe.manifest.get("expressions", [])))
             .replace("__CTA_TEXT__", universe.cta_text)
             .replace("__CTA_EMOTION__", universe.cta_emotion)
             .replace("__CTA_ACTION__", universe.cta_action))
    user = f"""{brief}

episode_id to use: {episode_id} (season 1, episode {episode_no})

{memory.context_block()}

{universe.context_block(include_arc=include_arc, arc_crumb=arc_crumb)}"""
    return [
        {"role": "system", "content": universe.writer_system or SYSTEM_WRITER},
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
    # The free tier's 8000-TPM admission rejects any repair prompt above it —
    # base prompt (~3.7k tok) + a full previous script (~5.5k tok) overflows,
    # making repair structurally impossible. Keep head (title/hook/scenes
    # start) + tail (shorts/metadata) so named errors stay locatable.
    cap = 4000
    if len(previous) > cap:
        half = cap // 2
        previous = (previous[:half]
                    + "\n...[middle truncated to fit the TPM budget]...\n"
                    + previous[-half:])
    return base_messages + [
        {"role": "assistant", "content": previous},
        {"role": "user", "content": feedback},
    ]
