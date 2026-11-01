# `app/audio/` — Audio Stage

## Module Responsibilities

Stage `AUDIO_READY` (`stages.build_audio`): TTS every line, add procedural music
beds + SFX, produce scene tracks, a master mix, and the `timing.json` contract
consumed by the video renderer. Also builds the audio for both shorts.

## Current-layer Index

| File | Role |
|---|---|
| `stages.py` | Pipeline stage wrapper (`build_audio`) — orchestrates the modules below for long + shorts |
| `tts.py` | Kokoro TTS via `kokoro-onnx` (quantized ONNX, CPU, disk-cached by line hash) |
| `mix.py` | Stage core: TTS per line + music bed + SFX → scene tracks → master timeline |
| `music.py` | Procedural, royalty-free-by-construction music loops per mood (happy playful calm wonder mystery tender triumph adventure), float32 stereo |
| `sfx.py` | Procedural SFX (44.1 kHz mono), mixed into master at configured gain |

## Output Contract

Under `state/episodes/<id>/audio/`:

| Artifact | Spec |
|---|---|
| `scene_XX.wav` | 44.1 kHz stereo per scene |
| `master.wav` | Full-episode 44.1 kHz stereo mix |
| `timing.json` | **Renderer contract** — scene/line timings; also holds shorts entries |
| `short_N.wav` | Per-short audio (also reflected in `timing.json`) |

## Development Notes

- `timing.json` is a hard contract with `app/render/` — changing its shape requires
  updating the renderer and QC together.
- All audio is 44.1 kHz; keep sample-rate conversions out of the hot path.
- Media is gitignored — the pipeline rebuilds it on a fresh checkout
  (fallback to `AUDIO_READY` when render finds files missing).
- TTS is disk-cached by line content, so re-renders reuse prior synthesis.
