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
