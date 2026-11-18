# Vendored subset of Lemo-Opuscar

- **Source:** <https://github.com/lemomo-ai/lemo-opuscar>
- **Pinned commit:** `00a7f9ec99c8686265a8ca4ed9a3fdaaf27ea6f4` (= origin/main HEAD at
  vendoring time, working tree clean)
- **Vendored:** 2026-11-18 under `docs/PLAN-STICKMAN-REVIVAL.md` §2 (approved by owner)
- **Licenses:** MIT (code) and OFL-1.1 (fonts) — see `LICENSE`, `REUSE.toml`,
  `LICENSES/`. Verified byte-identical to the pinned source at copy time.

## What is vendored (MIT code only)

| Path | Purpose |
|---|---|
| `core/lib.js` | shared runtime helpers used by demo pages |
| `core/render/browser.mjs` | Chromium launch config (`EXE`, `ARGS`, GL-loss handling) |
| `core/render/events.mjs` | demo event recording |
| `core/render/page.mjs` | Playwright page pool: open/close demo, size capture |
| `core/render/readcheck.mjs` | page read check |
| `core/render/serve.mjs` | tiny static HTTP server for demo pages |
| `core/render/slot.mjs` | slot/ffmpeg helpers |
| `core/render/still.mjs` | single-frame capture pipeline |
| `core/render/video.mjs` | worker pool → `window.render(t)` → JPEG → ffmpeg pipe |
| `core/fonts/*` | OFL display fonts (`f0`–`f7.woff2`) + `fonts.css` + `OFL.md` |
| `styles/stick-explainer/demo/{index.html,full.js}` | **reference only** — the MIT spring/rig technique our `engine-js/` adapts; never loaded at runtime |

## What is deliberately NOT vendored

- **All `*.md` documentation** — CC BY-NC-4.0, incompatible with redistribution in this
  public repository (the upstream commercial permission covers the film's own project
  files, not adapted docs shared here).
- `.srt`, posters, stills, demo media — CC BY / media licenses; not needed.
- `core/audio/**`, `core/tts/**`, `mux.sh` — we keep our own FFmpeg mix (avoids Lemo's
  ffmpeg-7-sensitive chain).
- `tools/`, `core/render/sheet.py`, `core/render/srt.py` — our driver implements its own
  model-sheet and subtitle generation (`app/render/engine/`).

## Dependencies of the vendored subset

Node ≥ 20 stdlib only, plus `playwright-core` (exact version locked in our
`package-lock.json` per plan §12.4). No other upstream code is required at runtime.

## Update procedure

1. Clone upstream; check out the new commit; review its diff **and** `REUSE.toml` changes.
2. Re-copy the table above with the same exclusions; verify SHA-256 of every file against
   the source (0 mismatches is the bar).
3. Update the pinned commit in this file; run the offline suite and a sample render.
4. Never take `*.md` files from upstream.
