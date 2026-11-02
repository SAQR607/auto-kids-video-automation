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
| `video.py` | FFmpeg assembly: rawvideo rgb24 pipe → per-scene H.264 → concat → mux audio |
| `thumbnail.py` | 1280×720 thumbnail composite from the package `thumbnail_concept` |
| `assets.py` | Builds deterministic PNGs under `assets/` (`python -m app assets`); profile-aware |
| `art/` | Art backends (drawing code) — see [art/memory.md](art/memory.md) |

## Performance Contract

~12k frames/week. Compositing rules (keep frames fast):

- Backgrounds pre-composited and cached per quantized camera rect
  (0.5 px quantum via `_rect_key`; per-layer pieces cached too — slow
  parallax layers repeat their rect across adjacent frames on pans)
- Sprites/props pasted via paste+mask onto RGB; avoid full-frame alpha ops
- Target ≤ ~80 ms/frame on a 4-core CPU (bench gate `perf.render_ms_per_frame` abs_max 80)

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
