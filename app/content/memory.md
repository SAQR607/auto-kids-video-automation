# `app/content/` — Content Engine

## Module Responsibilities

Turns universe bibles + Groq LLM recipes into validated episode packages
(long + shorts) and maintains story canon for continuity.

## Current-layer Index

| File | Role |
|---|---|
| `engine.py` | Stage `SCRIPTED` entry (`run_generation`): premise → full episode package via Groq, validated, saved. **Idempotent** — a valid `package.json` short-circuits regeneration (resume-safe) |
| `prompts.py` | Prompt builders for premise + full episode package generation (recipe: universe → format → shorts → story) |
| `validate.py` | Structural validation of generated packages (fail fast, before QC) |
| `universe.py` | Distils `universe/*.md` bibles + `manifest.json` into a compact writer's brief (Groq request limit ~32 KB, so bibles are not embedded verbatim) |
| `memory.py` | Story memory: canon facts + per-episode continuity (`state/story_memory/`, STORY_BIBLE) — checked during generation to avoid contradictions |
| `shorts.py` | Stage `SHORTS_READY` (`build_short_packages`): extracts the 2 shorts from the long package into standalone docs, status `ready → rendered → uploaded` |

## Key Files

- Output: `state/episodes/<id>/package.json` (+ `shorts/*.json`) — committed state
- Input source of truth: `universe/manifest.json` + `universe/*.md` (human-authored bibles)

## Development Notes

- Generation must stay **deterministic and idempotent**: never regenerate a valid package;
  resume relies on this.
- Bibles in `universe/` are the human source of truth — `universe.py` only distils rules
  for prompts; edit bibles, not hardcoded lists, for new canon.
- Validation here is structural only; editorial/policy rules belong in `app/qc/script_qc.py`.
- Shorts extraction happens at `SHORTS_READY`, not during generation.

## Decided Content Changes (2026-11-05 — NOT started)

- **Episode length test: 5–7 min** (was 480–600 s / target 540). Touches:
  `config/config.json` (+ example/stickman) `duration.*`, `validate.py` duration bounds
  (`long_min/max_sec`) and the word-count window in `prompts.py` (~1100–1450 words /
  80–95 w per scene — must shrink proportionally), script QC duration estimate, and any
  bench reference durations. Completion-rate experiment for ages 4–8.
- **Shorts: keep 2/long, strengthen hooks** — improve the first 2 seconds of each Short
  (prompt-side: stronger cold-open line + on-screen text; `shorts.py` /
  `prompts.py` short recipe). No volume/quota change.

## Editing-pass pacing — **landed 2026-11-13** (excluded the 2 decisions above)

- **Recipe** (`prompts.py` `SCRIPT_BRIEF`, `universe.py` `BEAT_TEMPLATE`, thin hint):
  **EXACTLY 20 scenes**, 4 dialogue lines × 9-11 w + 1 narration of 20-24 w =
  56-68 spoken w/scene (AIM ~62, ~1240 total; hard limits 1100-1450 w / 480-600 s
  unchanged). CTA = final scene's (sc20) **4th** dialogue entry. Briefs also gained
  the camera-variety rule.
- **`validate.py`**: scene_count default **17-24** (`content.scene_count_min/max`);
  per-scene pacing cap `content.scene_sec_max` default **30 s** (est = w/2.4 + 1.5 →
  68 w); camera-variety check — no 3 consecutive scenes with the same camera value
  (fires once per run).
- **`qc/script_qc.py`**: `NARRATION_WORDS` default **(18, 28)**, now cfg-driven
  (`_check_recipe(pkg, cfg)`, `content.narration_words_min/max`) so profiles can
  diverge; dialogue bounds unchanged.
- **Stickman profile**: recipe unchanged (13 scenes / 5 lines / 35-40 w narration);
  `config/config.stickman.json` gains `scene_sec_max: 42` (legacy ~37.7 s scenes
  keep validating) + `narration_words_min/max: 30/50`; brief.md gained the
  camera-variety rule. Its beat template (13 scenes) untouched.
- Fixtures recalibrated: `tests/qc_fixtures.py` + `test_content_validate.py` →
  18 scenes, ≤68 w/scene, 1100+ total.
