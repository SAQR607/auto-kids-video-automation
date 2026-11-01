# AGENTS.md

## Project

Fernwood Friends — autonomous kids' content pipeline (Groq → Kokoro TTS → Pillow/FFmpeg → QC → YouTube/TikTok; GitHub Actions is production). Run `python -m app <cmd>`; tests: `python -m pytest -q` (all offline/mocked). Production never runs locally.

## Project Memory (required reading before coding)

Detailed context is stored in layered `memory.md` files. **Before writing or changing code, read the memory for the affected module** — do not code blind:

| Memory | Contents |
|---|---|
| [memory.md](memory.md) | Architecture, state machine, profiles, persistence rules, env vars |
| [technology.md](technology.md) | Reusable tech (deps, stdlib HTTP, retry/redaction helpers) — check before adding libraries |
| [app/memory.md](app/memory.md) | Core package: CLI, pipeline stages, state, config |
| [app/content/memory.md](app/content/memory.md) | Groq generation, validation, shorts, story memory |
| [app/audio/memory.md](app/audio/memory.md) | TTS/mix + `timing.json` renderer contract |
| [app/render/memory.md](app/render/memory.md) | Compositor, FFmpeg, asset build |
| [app/render/art/memory.md](app/render/art/memory.md) | Art backends + stickman override pattern |
| [app/youtube/memory.md](app/youtube/memory.md) | OAuth, resumable upload, quota handling |

Locate the relevant memory chain with the skill scripts (avoid broad file reads):

```bash
node C:/Users/SAQR7/.agents/skills/project-memory-system/scripts/find-memory.js <path> --root <project-root>
node C:/Users/SAQR7/.agents/skills/project-memory-system/scripts/get-memory.js <module> --root <project-root>
```

## Tech Reuse First

Before writing code, check `technology.md` and search for existing helpers (`retry.py`, `logging_setup.py`, `groq_client.py`, stdlib `urllib` for HTTP, hand-rolled `.env` loader). Reuse > extend > new. Add new libraries only with strong justification, then update `technology.md`.

## Memory Update Policy

After meaningful code changes, **update only the affected `memory.md` files** (not all):

| Change | Update |
|---|---|
| New/changed stage, CLI, state, config | `app/memory.md` (+ root `memory.md` if cross-module protocol changed) |
| Content generation/validation/shorts | `app/content/memory.md` |
| Audio pipeline or `timing.json` shape | `app/audio/memory.md` (+ `app/render/memory.md` if the contract partner changes) |
| Rendering/art | `app/render/memory.md` / `app/render/art/memory.md` |
| YouTube publishing | `app/youtube/memory.md` |
| New dependency / reusable helper | `technology.md` |
| New subpackage | Create its `memory.md`, add to parent index |

Update timing: when the feature lands (same change), keep entries concise/table-based, remove stale entries, and verify recorded paths still exist.

Memory commands (prompt-style, no slash command needed):

- `/project-memory-system:init` — initialize memory (only if none exists)
- `/project-memory-system:update <file/module>` — update the closest affected `memory.md`
- `/project-memory-system:update all` — full audit of all memory files

## Key Rules

- Secrets never in code/config/logs — env only (see root `memory.md`).
- Stage functions never call `transition()`; the pipeline owns state advancement.
- Deterministic ids/registry: never duplicate an episode entry on retry.
- Art/assets: edit code, then `python -m app assets`; never hand-edit PNGs.
