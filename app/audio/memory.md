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
| `mix.py` | Stage core: TTS per line + music bed + SFX → scene tracks → master timeline (bed gain −24 dB, −8 dB duck during lines) |
| `loudnorm.py` | 2-pass EBU R128 loudnorm (measure → normalize) via ffmpeg JSON on stderr; atomic temp+`os.replace`, silence passthrough; targets −16 LUFS / −1.5 dBTP / LRA 11 |
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
- **Mastering**: `build_long_audio`/`build_short_audio` finish with
  `loudnorm.normalize` (2-pass, −16 LUFS / −1.5 dBTP) — the bench gates
  (`lufs_integrated`, `true_peak_db`) measure exactly this output.
- **Ducking**: music bed is attenuated `music.duck_db` (default −8 dB) around
  line marks via `_duck_envelope` (attack 0.12 s / release 0.40 s, lead 0.10 s
  / tail 0.30 s module constants) — deterministic from marks, no audio detector.
  Bed default is `music.bed_gain_db` −24 (was −16: music nearly as loud as voice).
- Config keys are read with `.get()` defaults (`app/audio/mix.py`); no schema
  validation, but keep `config/config.json`, `config.example.json`,
  `config.stickman.json` in sync.
