# `app/render/` — Render Stage

## Module Responsibilities

Stages `RENDERING` / shorts render: composite one Pillow frame per (scene, t),
pipe raw frames to FFmpeg (H.264 parts → concat → mux audio), build the 1280×720
thumbnail, and generate committed PNG art assets.

## Current-layer Index

| File | Role |
|---|---|
| `stages.py` | Stage wrappers: `render_long` (video + thumbnail) and shorts render |
| `scene.py` | Scene compositor — one RGB frame per (scene, t) |
| `video.py` | FFmpeg assembly: rawvideo rgb24 pipe → per-scene H.264 → concat → mux audio; frames rendered in a fork worker pool (`_frame_pool`); captures each scene's last frame bytes as `prev` for entry-boundary blends |
| `thumbnail.py` | 1280×720 close-up composite from the package `thumbnail_concept` — big faces, title-trim text, story prop |
| `assets.py` | Builds deterministic PNGs under `assets/` (`python -m app assets`); profile-aware |
| `engine/` | Narrative Stickman Engine driver (stickman profile only): scene plan → `engine-js/` page via the vendored Lemo render tools — see [engine/memory.md](engine/memory.md) |
| `art/` | Art backends (drawing code) — see [art/memory.md](art/memory.md) |

## Performance Contract

~12k frames/week. Compositing rules (keep frames fast):

- Backgrounds pre-composited and cached per quantized camera rect
  (0.5 px quantum via `_rect_key`; per-layer pieces cached too — slow
  parallax layers repeat their rect across adjacent frames on pans)
- Parallax compose (`_composed_bg_layered` → `_layer_piece`): each layer
  premultiplied **once** to RGBa and cropped to alpha bbox **+1 px
  zero-alpha rim** (`_PREM_CACHE`). PIL's RGBA path re-premultiplies the
  whole source per call (~26 ms fixed); the rim is load-bearing for
  exactness — PIL validates samples against the image it is given
  (valid `[-0.5, size-0.5)`, outside → fill) and clamps out-of-range
  indices to the edge row, so a tight crop reads *content* in the
  half-pixel band above the bbox where the full canvas reads zero-alpha
  rows. Transform output is limited to the content's mapped bbox (±1 px),
  coefficients shifted by output origin; base/sky layer is full-frame
  RGB, copied per compose. Any change here must stay pixel-exact vs the
  full-canvas transform (verified A/B: 1.50× on pan, 0 differing px).
- Sprites/props pasted via paste+mask onto RGB; avoid full-frame alpha ops
- Single-process ≤ ~80 ms/frame on a 4-core CPU (profile: majority of
  render wall is PIL `transform`; parallax transforms are RGBa-only and
  output-proportional)

### Parallel frame rendering (`video.py`, landed with abs gate 60)

- `render_long_video` renders frames in a **fork** `ProcessPoolExecutor`
  (`_frame_pool`, workers = `RENDER_WORKERS` or cpu−1, window = workers×2
  in-flight via `_ordered_parallel` — ordered yields, bounded 6 MB results).
- **fork-only**: spawn re-imports `app/__main__.py` (top-level
  `SystemExit(main())`) and fork inherits test monkeypatches; no fork
  (Windows) → sequential fallback, same code path.
- **Pool + warmup (`_warmup` × workers) MUST run before the first
  `_spawn`**: workers forked later inherit the encode pipe's stdin, hold
  it open, ffmpeg never sees EOF → `proc.wait()` deadlock.
- Frames are pure functions → byte-identical output; main process keeps
  the ordered ffmpeg pipe. Shorts (`render_short_video`) still sequential.
- Diagnostics for gate triage: pool log carries `cpus/affinity/loadavg`,
  each worker logs `affinity` and `cpu/wall` ratio (≈1.0 → full core,
  ≈1/N → CPU-starved workers time-sharing).
- Gate: `perf.render_ms_per_frame` abs_max **60** (expected ~35-40 with 3
  workers). For function-level `bench --profile-render` runs set
  `RENDER_WORKERS=1` (otherwise the parent profile only shows orchestration).

## Camera Contract (`scene.py:_view_rect` / `_composed_bg`)

- View window floats; fitted to **0.90 motion margin** of the 2200×1400 bg so
  pans/drift always have travel room (bg is exactly frame-aspect wide — the
  old fit pinned x0=0 and made pan_l/pan_r dead cameras in every episode).
- Uniform margin across camera types: cuts never jump scale; windows never
  exceed bg bounds (no black edges by construction — unit-tested).
- Sampling: one affine (BILINEAR) crop+scale per layer — sub-pixel smooth
  motion; no integer rect snapping, no 8 px cache stalls.
- `tests/test_camera.py` locks: pan travel > 40 px, bounds, aspect, static
  immobility, zoom direction, 0.5 px quantum behavior.

## Development Notes

- FFmpeg is required on PATH (checked by `doctor`); frames are piped, never written per-frame.
- Media (renders, thumbnails) is gitignored — the renderer **auto-regenerates missing
  files** on a fresh checkout instead of failing.
- All Fernwood art builds into committed `assets/`; QC verifies it. **Stickman** is
  code-drawn (edit `art/` code, then `python -m app assets`). The **hand-drawn cast,
  props and locations** load from user art instead: cast/props rebuild from
  `assets/characters_src/` + `assets/props_src/` (quantized); locations are
  **output-only** — `assets/locations/` is the single committed copy, installed from
  the gitignored `*_new/` archive by the root `_install_locations.py` converter
  (not regenerated by the build; it re-saves byte-idempotently). Edit sources or the
  converter, then rebuild. Never hand-edit built asset PNGs.
- Profile-aware art resolution goes through `art/backend.py` (see art memory).

## Editing Pass — **landed 2026-11-13** (all five approved items)

1. **Real dissolves + true cuts** — the incoming scene owns its entry boundary.
   `video.py` captures each scene's last frame bytes and threads
   `(prev_bytes, prev_dur)` as the 13th task-tuple element into
   `render_frame(prev=...)`. For the first `_BOUNDARY_SEC = 0.6 s` of the incoming
   scene: `fade`/`dissolve`/unknown → `Image.blend` cross-dissolve; `wipe_leaves` →
   `_wipe_mask` (edge 1.485→0 across 24 steps, 255 = prev, reveals left-ward) +
   `Image.composite(prev, cur, mask)`. Gates: `prev_dur >= 1.2` else hard cut;
   `transition_in == "cut"` → hard cut; `prev=None` (shorts, scene 0, samples/bench)
   → hard boundary. **Both black fades deleted** (~10 s black/episode was the bug)
   plus now-dead `_black_mask`/`_black_image`. The captured bytes are the EXACT
   frame shown (end card + punch state continuous across the boundary); no re-render.
2. **Faster scene pacing** — content side: see [app/content/memory.md](../content/memory.md)
   (scene_count 17–24, `content.scene_sec_max` 30 s ≈ 68 spoken words, stickman 42).
3. **Title card 4.6 → 2.5 s** (`scene_index == 0 and t < 2.5`, fade-out from 1.7 s).
4. **Camera variety + punch-ins** — `validate.py` rejects 3 consecutive scenes with
   the same camera (brief rule added to BOTH profile briefs); `_punch(lines, t)`
   envelope on `excited/amazed/surprised` (0.15 s attack, release by 0.55 s) →
   whole-frame **8% crop+resize zoom** applied after fx, BEFORE overlays (chars+bg
   scale together, cards stay flat, `_view_rect`/bg caches untouched).
5. **End-card watch-next CTA** — `_end_overlay(..., watch_next)` third line; cfg key
   `channel.watch_next` (set in `config.json` + `config.stickman.json`; empty/absent
   = line hidden). End-card cache key now includes it.

Tests: `tests/test_transitions.py` (dissolve/cut/wipe boundaries, mask contract,
punch envelope + zoom). Visual check done on real scenes (dusk→night dissolve,
wipe reveal, punch, end card).

Thumbnail redesign — **landed 2026-11-12** (its own pass, before editing):
big face close-ups (head-crop bottom-anchored, ONE shared scale per render,
`idle` state so variable action poses can't break the crop), bold yellow
stroked text rule-trimmed to ≤4 words from `package.title` (`_thumb_text`,
no LLM call), story prop from scene 0 bottom-left, expression from the
concept. Gates kept as-is: ref `thumbnail_sharpness` 1398 (floor 814),
`thumbnail_colorfulness` 77.6 (baseline 73.29). Tests:
`tests/test_thumbnail.py`.
