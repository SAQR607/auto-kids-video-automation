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
| `video.py` | FFmpeg assembly: rawvideo rgb24 pipe → per-scene H.264 → concat → mux audio; frames rendered in a fork worker pool (`_frame_pool`) |
| `thumbnail.py` | 1280×720 thumbnail composite from the package `thumbnail_concept` |
| `assets.py` | Builds deterministic PNGs under `assets/` (`python -m app assets`); profile-aware |
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
- All art is regenerable from code; committed `assets/` is build output, QC verifies it.
  Edit `art/` code, then `python -m app assets` — never hand-edit asset PNGs.
- Profile-aware art resolution goes through `art/backend.py` (see art memory).
