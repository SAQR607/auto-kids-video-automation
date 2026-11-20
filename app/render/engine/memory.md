# `app/render/engine/` — Narrative Stickman Engine Driver

## Module Responsibilities

Python side of the Stickman engine (plan §4 Phase 1): turn a scene-plan dict into
frames/video by driving the pinned Lemo render tools over the `engine-js/` page.
Fernwood's Pillow path (`scene.py`/`video.py`) is untouched and stays authoritative
for that channel.

## Current-layer Index

| File | Role |
|---|---|
| `render.py` | `render_stills(plan, times, out_dir, size)` → `t_<t>.jpg` list; `render_video(plan, out_path, fps, workers, size)` → mp4; plan travels percent-encoded in `?plan=` (stateless → safe for video.mjs's parallel workers) |
| `../../engine-js/` | Engine runtime page: `index.html` (READY/DUR/render contract) + `engine.js` (rig, damped springs, seeded phases, poses idle/wave/walk) |
| `../../vendor/lemo-opuscar/` | Pinned MIT render toolkit (`core/render/{still,video,page,serve,browser}.mjs`), see `VENDOR.md` |

## Contracts

- **Render contract** (vendor `core/render`): page must set `window.READY === true`,
  `window.DUR` (seconds > 0), `window.render(t)`; serve root = `vendor/lemo-opuscar/`;
  `engine-js/` sits outside it → mounted at `/@film/` (absolute `/core/lib.js` still
  resolves to the vendor root).
- **Determinism**: all randomness seeded at scene build; `render(t)` only interpolates
  a precomputed 240 Hz spring table → frame output independent of call order/workers.
  Gate: `tests/test_engine_determinism.py` (same plan twice → identical SHA-256,
  frames must also differ over time; video smoke; skips without node + playwright-core
  + headless shell so Fernwood-only suites stay green).
- **JS deps**: root `package.json` exact `playwright-core` + committed lock, `npm ci`;
  Chromium = `node node_modules/playwright-core/cli.js install chromium-headless-shell`
  (version pinned by the lock; CI caches it under the lock hash).
- **Schema validation** lives in JS for now (`buildScene` throws → pageerror → render
  exits non-zero); the Python `plan.py` schema boundary arrives in a later phase.

## Conventions

- Driver is a thin subprocess wrapper: `node <tool.mjs> <engine-js> … --q plan=…`; no
  shell, `cwd=repo root`, non-zero exit → `RuntimeError` with captured stdout/stderr.
- `render_video` requires ffmpeg on PATH (same as the rest of the pipeline).
- Manual sample: `node vendor/lemo-opuscar/core/render/still.mjs engine-js <t>` uses
  `DEFAULT_PLAN`; outputs to gitignored `engine-js/stills/`, `engine-js/out/`.
- CI: `.github/workflows/engine.yml` (read-only token, actions pinned to SHAs,
  test-only — never publishes, never writes state).
