# `app/content/` — Content Engine

## Module Responsibilities

Turns universe bibles + Groq LLM recipes into validated episode packages
(long + shorts) and maintains story canon for continuity.

## Current-layer Index

| File | Role |
|---|---|
| `engine.py` | Stage `SCRIPTED` entry (`run_generation`): premise → full episode package via Groq, validated, saved. **Idempotent** — a valid `package.json` short-circuits regeneration (resume-safe). Runs the research stage first when `research.enabled` |
| `research.py` | Research stage (stickman, plan §7): topic claim/rotation → stdlib fetch → Groq claim extraction → claim↔evidence gate → `research.json`; blocks via `ResearchError` |
| `directives.py` | Scene-directive seam (plan §2): `directive_messages` prompt + `validate_directives` schema → `scene_plan()` for engine-js. Groq never writes JS/HTML |
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

## Research stage + directives — landed 2026-11-24 (Phase 2)

- **Gating:** `cfg research.enabled` — only `config/config.stickman.json` has it;
  Fernwood configs have no key → zero behavior change (hook sits in
  `run_generation` after `_groq()`, before premise; result flows into
  `script_messages(research=...)` via `research_block`, `None` → byte-identical prompt).
- **Paths:** pool `topics/pool.json` (curated, human-edited, committed);
  rotation record `state_stickman/topics_record.json` — deliberately under state
  because workflows only `git add state_stickman` (a repo-root record would be
  lost every run); per-episode `state*/episodes/<id>/research.json` holds claims +
  ≤250-char excerpts only — never full text/HTML.
- **Evidence gate (§7):** every claim needs ≥2 excerpts from 2 independent sources
  (different publisher AND registrable domain); Wikipedia-derivative sources
  (shingle Jaccard ≥0.8 vs the discovery article) and syndicated duplicates
  (pairwise Jaccard ≥0.8) are dropped; excerpts are mechanical (highest
  content-word-overlap sentence, substring of received bytes, hard cap 250).
  <2 usable sources or a missing link → `ResearchError` → pipeline FAILED +
  Telegram + attempt-budget retries; topic marked `blocked` and never re-issued;
  the same episode re-claims its own topic on retry (idempotent).
- **Rotation:** `claim_topic()` — recorded topics (pending/used/blocked) are never
  handed to another episode; pool exhaustion raises.
- **QC:** additive `_check_claim_coverage` in `qc/script_qc.py` (reads
  `research.json`; absent → no-op) — shared by the QC gate and the generator
  repair loop. `validate_config` requires `research.pool_path` to exist when enabled.
- **Directives (Phase 2 scope = prompt + schema only; pipeline wiring is Phase 4):**
  poses mirrored from `engine-js/engine.js` POSES (`idle/wave/walk`), `scene_plan()`
  emits the `buildScene` contract `{seed, duration, stage, actors}`.
- Tests: `tests/test_content_research.py` (21) + `tests/test_content_directives.py`
  (11); suite 361 → 393 green. Source liveness re-verify at Gate 2 (pool notes).

## Shorts `hook_text` rule — landed 2026-11-18 (retained WIP)

- Each short carries `hook_text` (1–6 words, **different** per short): on-screen cold-open
  caption, emitted by `prompts.py`, enforced in `validate.py` (and therefore also in
  `script_qc`, which runs `validate_package`). Missing/overlong/duplicate → validation error.
- Fixtures set valid values in all three package builders (`tests/qc_fixtures.py`,
  `test_content_validate.py::_make_valid_package`, `test_profile_stickman.py::_short`);
  `test_hook_text_rule_rejects_missing_overlong_and_duplicate` guards QC strength.
