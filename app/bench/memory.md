# `app/bench/` — Quality Benchmark

## Purpose

Objective before/after quality gates for ANY pipeline change. **CI-only**
(`python -m app bench`) — it renders a golden reference episode, so never run
it locally. Fully isolated: state root `workspace/bench/`, production `state/`
is never read/written. No new dependencies (numpy/PIL/soundfile/ffmpeg/faster-whisper).

## Files

| File | Role |
|---|---|
| `reference.py` | Golden episode `bench001`: 3 deterministic probe scenes (no Groq); real production vocabulary (locations/cast/props/fx/cameras/moods) |
| `metrics_video.py` | psnr/ssim (integral-image windows), laplacian sharpness, colorfulness, flicker MAE, phase-correlation pan motion |
| `metrics_audio.py` | loudnorm LUFS/true-peak (JSON block extracted from ffmpeg stderr), speech prominence (RMS dB), WER, TTS RTF; `_parse_loudnorm()` unit-tested |
| `runner.py` | Orchestration, `METRIC_SPECS` gates, baseline compare; prints "do not re-baseline failures" |

## Probe design (why scenes look the way they do)

| Scene | Isolates |
|---|---|
| `sc_probe_static` (no fx, narration) | encoder/tint flicker on top crop — `video.flicker_static_mae` |
| `sc_probe_pan` (pan_l) | background-motion continuity — `pan_frozen_pct` / `pan_jitter_px` measured on a **texture-guided band** (best of rows y=60/200/340 ×360 by horizontal detail; a fixed sky band fakes 100% frozen) |
| `sc_probe_push` (push_in, dusk, fx, 3 chars) | zoom compositing, FX, color spread, muxing |

## Gates + baseline policy

- Baseline: `benchmarks/baseline.json`, committed ONLY by CI dispatch
  (`benchmark.yml` with `update_baseline=true`, `[skip ci]` commit).
- `METRIC_SPECS` in `runner.py` is the source of truth for gates
  (rel = ×baseline, skipped for |base|<1e-6; abs = hard bounds).
- **Never re-baseline to hide a failure.** Abs bounds must leave the current
  baseline passing; tighten them in the SAME change as the improvement they
  measure (loudnorm→LUFS/prominence, sub-pixel camera→pan_frozen abs_max 5).
- Workflow: `.github/workflows/benchmark.yml` — push on `app/**` + dispatch;
  artifact `bench-metrics` (metrics.json). Exit: 0 pass/"NO BASELINE YET", 1 regression.

## Known baseline facts (as of first baseline)

- `pan_frozen_pct=100` WAS the camera rect `//8` quantization + zero-travel
  defect in `app/render/scene.py:_view_rect` — **fixed** (0.90 motion margin,
  float rects, sub-pixel affine, 0.5 px cache quantum). The pan gate was
  tightened to `abs_max 5` in the same commit as the fix (per gate policy).
  Baseline pre-dates the fix until the next `update_baseline` dispatch.
- LUFS −19.37 (no loudnorm yet), prominence 3.17 dB (no ducking yet) —
  improvements expected to move these hard.
