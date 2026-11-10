# Auto Video — Fernwood Friends Autonomous Content Pipeline

## Project Overview

Fully automated kids' content system: Groq writes scripts → Kokoro TTS speaks →
Pillow/FFmpeg render 2D animation → QC gates every output → YouTube publishes →
Telegram reports. GitHub Actions is the production computer (~$0/month).
Output: 3 long episodes/week (8–10 min, 1920×1080) + 2 Shorts per long
(25–45 s, 1080×1920), English only, ages 4–8.

> Deep detail lives in root docs — this memory is the fast index.
> [ARCHITECTURE.md](ARCHITECTURE.md) · [OPERATIONS.md](OPERATIONS.md) · [SECURITY.md](SECURITY.md)

## Architecture Summary

Single Python package (`app/`, Python 3.11+ / tested 3.12). Entry:
`python -m app <command>` → `app/cli.py` (14 subcommands; `produce` is the CI entry).

- **State machine** drives episodes: `PLANNED → SCRIPTED → SCRIPT_QC →
  AUDIO_READY → RENDERING → RENDERED → RENDER_QC → UPLOADING → PUBLISHED →
  SHORTS_READY → SHORTS_SCHEDULED → COMPLETE`; any → `FAILED` (bounded retries).
  Enforced by `app/state.py`; orchestrated by `app/pipeline.py` (lazy stage imports,
  checkpoints, Telegram alerts).
- **Idempotency**: deterministic `s01eNNN` ids; one registry entry per schedule slot —
  retries reuse the same episode, never duplicate.
- **Persistence rule**: git carries *state, never bytes*. Committed:
  `state/registry.json`, `state/episodes/*/package.json` + shorts, `state/story_memory/`,
  assets, docs. Ignored: audio, renders, thumbnails, logs, models. Each CI run starts from
  a fresh checkout and rebuilds missing media (fallback to `AUDIO_READY` / short → `ready`).

## Channel Profiles

Selected via `APP_PROFILE` (or CLI `--profile`); isolated config + env + data dirs:

| Profile | Config | Env file | Data dirs |
|---|---|---|---|
| default (Fernwood) | `config/config.json` | `.env` | `state/`, `universe/`, `workspace/`, `assets/`, `logs/` |
| stickman | `config/config.stickman.json` | `.env.stickman` (overrides base) | `state_stickman/`, `universe_stickman/`, `workspace_stickman/`, `assets_stickman/` |

Profile env loads BEFORE `.env` so profile secrets win while shared keys
(e.g. `GROQ_API_KEYS`) still inherit. Art backends switch per profile
(see `app/render/art/memory.md`).

## Submodule Index

| Module | Memory | Role |
|---|---|---|
| `app/` | [app/memory.md](app/memory.md) | Core package: CLI, pipeline, state, schedule, config, LLM client, infra |
| `app/content/` | [app/content/memory.md](app/content/memory.md) | Groq generation, prompts, validation, shorts, story memory, universe |
| `app/audio/` | [app/audio/memory.md](app/audio/memory.md) | TTS, mix, procedural music/SFX, `timing.json` contract |
| `app/render/` | [app/render/memory.md](app/render/memory.md) | Scene compositor, FFmpeg assembly, thumbnail, assets |
| `app/render/art/` | [app/render/art/memory.md](app/render/art/memory.md) | Art backends (Fernwood base + stickman overrides) |
| `app/bench/` | [app/bench/memory.md](app/bench/memory.md) | Quality benchmark: golden reference → metrics → gates vs `benchmarks/baseline.json` (CI-only) |
| `app/youtube/` | [app/youtube/memory.md](app/youtube/memory.md) | OAuth, resumable upload, verify, metadata, quota taxonomy |
| `app/tiktok/` | — (see [docs/TIKTOK.md](docs/TIKTOK.md)) | Inbox-draft upload for shorts (no audit needed) |
| `app/qc/` | — (see [CONTENT_SYSTEM.md](CONTENT_SYSTEM.md)) | Script QC + video QC PASS/FAIL gates |

## Data Directories

| Path | Purpose |
|---|---|
| `state/` | registry.json + per-episode packages + story memory (committed) |
| `universe/` | Human-authored bibles (`*.md`) + `manifest.json` + `prompts/` (copy-paste image-gen prompts; locations first) — source of truth for content |
| `workspace/` | Thumbnails + benchmark scratch (`workspace/bench/`, gitignored) |
| `benchmarks/` | Committed benchmark baseline (`baseline.json` — metric gates) |
| `assets/` | Committed PNG build output (`python -m app assets` re-saves; not the source for user art) + hand-drawn sources `characters_src/`, `props_src/` and output-only `locations/` (user art, NOT regenerable — edit sources/`*_new/` archive + converter `_install_locations.py`, then rebuild) |
| `models/` | Kokoro ONNX model (gitignored, downloaded) |
| `release/` | Snapshot copy of a release (own `.git`) |

## CI Workflows (`.github/workflows/`)

| Workflow | Trigger | Behavior |
|---|---|---|
| `production.yml` | hourly cron `17 * * * *` + dispatch | Runs `produce`, pushes `state/` back; never cancels concurrent runs |
| `production-stickman.yml` | same, stickman profile | Runs the stickman profile pipeline |
| `manual.yml` | dispatch: tests/doctor/status/schedule/snapshot/dry-run | Never publishes |
| `health_check.yml` | daily 07:00 UTC + dispatch | pytest + doctor (read-only) |
| `benchmark.yml` | push (`app/**`) + dispatch (`update_baseline`) | Golden-reference quality benchmark vs `benchmarks/baseline.json`; metrics artifact `bench-metrics`; dispatch can persist a new baseline |

## Environment Variables (names only — values only via env, never in config/git)

- `APP_PROFILE` — channel profile selector
- `GROQ_API_KEYS` — comma-separated key pool (enables failover)
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` — monitoring alerts
- `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN` — publishing
- `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_ACCESS_TOKEN`, `TIKTOK_REFRESH_TOKEN`
- `DRY_RUN`, `LOG_LEVEL`, `QC_TRANSCRIBE` — behavior flags
- `RENDER_WORKERS` — render worker processes (default cpu−1; `1` = sequential)

Secrets precedence: real env (GitHub Secrets) > `.env` file > nothing.
Config files never contain secrets. Logs are redacted
(`app/logging_setup.py`). See [SECURITY.md](SECURITY.md).

## Key Conventions

- **Production never runs locally** — full TTS/renders/end-to-end belong on GitHub Actions.
  Local: code, tests, tiny samples, git.
- All tests offline/mocked: `python -m pytest -q` (`pytest.ini`, `testpaths=tests`).
- Stage functions never call `transition()` — the pipeline owns state advancement.
- Deterministic art: `python -m app assets` is source of truth for built bytes.
  Code-drawn kinds (stickman) regenerate from code; hand-drawn kinds (cast, props,
  locations) rebuild from their committed user-art sources — never hand-edit built PNGs.

## Current Focus (quality push — decisions 2026-11-05)

Goal: improve **characters, sound, editing** → more views + watch time (ages 4–8).

| Area | Status | Decision |
|---|---|---|
| Sound | ✅ **Done** (`01b9a1e`, CI green: −16.15 LUFS, prominence 10.16 dB, TP −1.48) | 2-pass loudnorm + deterministic music ducking (bed −24 dB, duck −8 dB) |
| Characters | 🟢 Wired (2026-11-10) | **Full art-style redesign** — all 7 cast + 20 props + 112 location layers hand-drawn by user; PNG loaders wired (`png_sprites.py`, `props.py`, `locations.py`), art=canon sync for all 7; willowbys block patch baked into `_install_locations.py` — see [app/render/art/memory.md](app/render/art/memory.md) |
| Editing | ⚪ After characters | Real dissolves + true cuts, faster scene pacing, title card 4.6 s → ~2.5 s, camera variety + punch-ins, end-card watch-next CTA — see [app/render/memory.md](app/render/memory.md) |
| Thumbnail | ⚪ With editing | Redesign: bigger faces, excited expressions, bolder text |
| Episode length | ⚪ Content change | Test **5–7 min** (was 480–600 s) — touches `config` + `validate.py` + prompts |
| Shorts | ⚪ Content change | Keep 2/long; improve Shorts hooks (first 2 seconds) |

Order: **characters → editing**; each change tightens its gates in the same commit
(never re-baseline to hide failures). Work starts only after memory notes are in place.
