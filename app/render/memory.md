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
- Sprites/props pasted via paste+mask onto RGB; avoid full-frame alpha ops
- Target ≤ ~80 ms/frame on a 4-core CPU

## Development Notes

- FFmpeg is required on PATH (checked by `doctor`); frames are piped, never written per-frame.
- Media (renders, thumbnails) is gitignored — the renderer **auto-regenerates missing
  files** on a fresh checkout instead of failing.
- All art is regenerable from code; committed `assets/` is build output, QC verifies it.
  Edit `art/` code, then `python -m app assets` — never hand-edit asset PNGs.
- Profile-aware art resolution goes through `art/backend.py` (see art memory).
