# STORY BIBLE — how a Fernwood episode is built

> Structure, constraints and QC expectations for every script the content
> engine generates. English only. Ages 4–8.

## Episode formats
| format | length | slot | ratio |
|---|---|---|---|
| long | 8–10 min (480–600s, target 540s) | Mon/Wed/Fri | 1 per day |
| short | 25–45s (target 34s) | Tue/Thu/Sat | exactly 2 per long |

## Long episode beat template (540s target)
| # | beat | time | purpose |
|---|---|---|---|
| 1 | Cold open / hook | 0:00–0:45 | question or visual surprise in first 10s |
| 2 | Everyday setup | 0:45–1:30 | who/where today; warm humour |
| 3 | Inciting problem | 1:30–2:45 | mild: lost thing, confusion, plan needed |
| 4 | First try | 2:45–4:15 | enthusiastic attempt — partial, instructive fail |
| 5 | Re-think | 4:15–5:30 | observe, ask Willowby-question, gather facts |
| 6 | Better plan | 5:30–7:15 | teamwork + tool; show process steps |
| 7 | Payoff | 7:15–8:30 | success achieved kindly; learning spine lands |
| 8 | Warm close | 8:30–9:30 | joke callback, friendship beat, Glimmer flicker (arc) |
| 9 | End card wave | 9:30–9:50 | friends wave from the hill / village green |

Rules:
- Hook must pose a concrete question a child can echo back.
- Exactly ONE learning spine per episode (never two).
- Problem resolved INSIDE the episode — no cliffhangers in longs.
- Narration carries transitions; characters carry emotion.
- ≥ 2 main characters in every scene (bible rule); Willowby only asks.
- First 10 seconds contain motion + voice (retention rule).

## Learning spines (rotate; one per episode)
patience · sharing · honesty · asking for help · trying again · listening ·
kindness to small things · keeping promises · courage with care · gratitude ·
including others · caring for nature · telling the truth first · waiting your turn

## Dialogue rules
- Sentences ≤ 10 words for child characters; ≤ 14 for Willowby.
- One idea per line; no stacked instructions.
- Repeat the key learning phrase once (not three times).
- Naming: use each character's name at least once per scene.
- Never: sarcasm at a child's expense, teasing bodies, fear words
  ("danger", "scary", "monster" banned), threats, whining > 2 lines.

## Shorts construction (§24)
Each short is a SELF-CONTAINED 25–45s beat drawn from the long's world:
1. **Hook frame** (0–2s): motion + a visual question. No preamble.
2. **Body** (2–30s): one gag / one discovery / one mini-demonstration.
3. **Button** (30–40s): punchline or warm beat; loopable last frame.
Rules:
- Zero arc knowledge assumed; a viewer who missed the long must enjoy it.
- ≤ 4 dialogue lines total; titles readable without sound.
- Vertical composition: characters in middle 70% (safe zone), faces upper-third.
- The two shorts from one long must differ in mood (e.g. funny + wonder).
- Never reveal the long's ending payoff in a short.

## Mystery-arc crumbs (season 1)
Arc beats (WORLD_BIBLE table) may appear ONLY in the warm-close beat and must
be ≤ 10s. Arc never displaces the learning spine.

## Continuity / story memory
After every episode the engine writes `state/story_memory/episodes/<id>.json`:
```json
{
  "episode_id": "s01e004",
  "canon_additions": ["compass_stone discovered under third stepping stone by Wren"],
  "callbacks_available": ["marlow_lost_pebble", "juni_leaf_cap_gag"],
  "glimmer_state": {"meadow_spots": 3, "cave_hinted": true},
  "relationship_notes": ["Juni trusted Wren's map instead of rushing"]
}
```
`state/story_memory/canon.json` aggregates world facts (never contradicted).

## Script package schema (what generation must output — §14)
```json
{
  "schema": "fernwood.episode/1",
  "episode_id": "s01e005",
  "title": "...",
  "premise": "...",
  "learning_spine": "patience",
  "duration_target_sec": 540,
  "hook": "...",
  "scenes": [
    {
      "scene_id": "sc01",
      "location": "hollow_oak_village",
      "time_of_day": "day",
      "camera": "static",
      "transition_in": "cut",
      "characters": [
        {"id": "juni", "position": "left", "enter": "enter_right", "state": "run"},
        {"id": "wren", "position": "right", "enter": "onscreen", "state": "idle"}
      ],
      "dialogue": [
        {"speaker": "juni", "text": "...", "emotion": "excited", "action": "jumps"}
      ],
      "narration": [{"text": "..."}],
      "props": ["map_scroll"],
      "fx": [],
      "music_mood": "happy"
    }
  ],
  "shorts": [
    {"short_id": "short_1", "kind": "funny", "title": "...", "location": "hollow_oak_village",
     "time_of_day": "day", "camera": "static", "characters": ["juni", "marlow"],
     "dialogue": [{"speaker": "juni", "text": "...", "emotion": "excited", "action": "jumps"}],
     "music_mood": "happy", "duration_target_sec": 34}
  ],
  "metadata": {
    "title": "...", "description": "...", "tags": ["..."],
    "thumbnail_concept": {"background": "glimmer_meadow", "characters": ["juni", "wren"],
                           "expression": "surprised", "text": "THE LOST BELL"}
  }
}
```

## Metadata rules (YouTube)
- Long titles: `<Hook Phrase> | Fernwood Friends S1E04` ≤ 70 chars; curiosity
  gap, no click-bait lies (title must match content QC).
- Shorts titles: ≤ 40 chars, present tense, punchy.
- Description (long): 2-3 kid-safe sentences + episode promise + series line;
  NO links, NO "subscribe" begging (Made-for-Kids rules). ≤ 500 chars.
- Tags: 8–15, mixture of "kids stories", "animated stories for kids" +
  episode specifics; no misleading tags.
- Thumbnails: max 5 words of text; face + emotion; must match the hook.

## Script QC gates (PASS/FAIL — `app.qc.script_qc`)
1. Valid schema + every referenced character/location/prop exists in manifest.
2. Duration estimate within 480–600s (spoken words ≈ 2.4 words/sec).
3. Learning spine present and demonstrated (score ≥ 0.7 via rubric LLM check).
4. Banned-word list clean (fear/violence/commerce/slang).
5. Scene continuity: no location jumps without transition; ≥2 characters/scene.
6. Shorts: 2 present, each 25–45s estimated, different moods, arc-free.
7. Hook within first scene; resolution within episode (no open problem).
8. Title/thumbnail promise matches hook (semantic check score ≥ 0.7).
