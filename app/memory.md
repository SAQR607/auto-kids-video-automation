# `app/` — Core Package

## Module Responsibilities

Single Python package implementing the whole pipeline. Root modules are infra/
orchestration; domain work lives in subpackages (`content/`, `audio/`, `render/`,
`qc/`, `youtube/`, `tiktok/`).

Entry chain: `python -m app <cmd>` → `__main__.py` → `cli.py:main()`.

## Current-layer Index

| File | Role |
|---|---|
| `cli.py` | argparse CLI — 14 subcommands (`init doctor status schedule run run-shorts dry-run produce youtube-oauth tiktok-auth youtube-patch snapshot assets bench`); `produce` is the CI entry |
| `pipeline.py` | Orchestration: `_LONG_ORDER` stage list, lazy stage imports, checkpoints, Telegram failure alerts, retry budget, dry-run gating |
| `state.py` | `Stage` enum, `_TRANSITIONS`, `advance_path()`, atomic `Registry` (registry.json); owns the state machine |
| `schedule.py` | Config-driven UTC slots; `plan_due()` joins slots with registry (26 h catch-up) |
| `config.py` | Secrets precedence (env > `.env` > none), profile isolation (`APP_PROFILE`) |
| `groq_client.py` | Groq key-pool failover client with bounded backoff |
| `retry.py` | Bounded retry helpers (exp. backoff + jitter) |
| `doctor.py` | Environment/credential gate (PASS/FAIL/WARN; `--online` opt-in) |
| `telegram_client.py` | Success/failure notifications, sanitized |
| `logging_setup.py` | Logging + secret redaction |

## Submodule Index

| Subpackage | Memory | Role |
|---|---|---|
| `content/` | [content/memory.md](content/memory.md) | Groq generation, prompts, validation, shorts, story memory, universe |
| `audio/` | [audio/memory.md](audio/memory.md) | TTS, master mix, procedural music/SFX |
| `render/` | [render/memory.md](render/memory.md) | Scene compositor, FFmpeg assembly, thumbnail, art assets |
| `qc/` | — | Script QC + video QC PASS/FAIL gates (see [CONTENT_SYSTEM.md](../CONTENT_SYSTEM.md)) |
| `bench/` | — | Quality benchmark suite: golden reference episode → real audio/render stages → objective metrics gated vs `benchmarks/baseline.json` (CI-only via `bench` CLI; see [CONTENT_SYSTEM.md](../CONTENT_SYSTEM.md)) |
| `youtube/` | [youtube/memory.md](youtube/memory.md) | OAuth, resumable upload, verify, metadata, quota taxonomy |
| `tiktok/` | — | Inbox-draft upload for shorts (see [docs/TIKTOK.md](../docs/TIKTOK.md)) |

## Cross-module Contracts

- **Stage function signature**: `(cfg, reg, episode_id, ctx)`; stage functions **never**
  call `transition()` — `pipeline.py` advances state after success.
- **Stage import**: `pipeline._call()` imports lazily; a missing module raises
  `StageUnavailable` (exit 2), so `doctor`/`init`/`schedule` work before a full build exists.
- **State ownership**: only `state.py` mutates the registry transitions; other modules read
  registry entries via `Registry.get/put`.
- **Secrets**: never in config files or logs — via env only, redacted in logs.

## Development Notes

- Keep new infra helpers in this layer (reuse `retry.py`, `logging_setup.py`, `groq_client.py`).
- New pipeline stage: append to `_LONG_ORDER` in `pipeline.py`, add the `Stage` transition
  in `state.py`, and add tests in `tests/`.
- Profile-aware behavior must go through `config.profile()` — do not hardcode profile names
  outside the art backend dispatcher.
