# Technology Index

Check this file before writing code — reuse existing solutions first.

## Runtime

| Item | Choice | Notes |
|---|---|---|
| Python | 3.11+ (tested on 3.12) | Single package `app/`; entry `python -m app <cmd>` |
| External binary | FFmpeg (must be on PATH) | Checked by `doctor`; encode/concat/mux/probe |

## Runtime dependencies (requirements.txt)

| Library | Version | Purpose | Used in |
|---|---|---|---|
| pillow | ^10 | Frame compositing, thumbnails, PNG assets | `app/render/` |
| numpy | ^1 | Audio/image numerics | `app/audio/`, `app/render/` |
| soundfile | ^0 | WAV read/write (44.1 kHz) | `app/audio/` |
| kokoro-onnx | ^0 | TTS (quantized ONNX, CPU) | `app/audio/tts.py` (model in `models/`, disk-cached) |
| onnxruntime | ^1 | kokoro runtime | same |
| faster-whisper | ^1 | Transcript spot-check in video QC (`QC_TRANSCRIBE=1`) + bench WER | `app/qc/video_qc.py`, `app/bench/` |
| av (PyAV) | `>=11,<19` | **Pin**: PyAV 19 removed `av.open(metadata_errors=…)` still used by faster-whisper → audio decode crashes | transitive (faster-whisper) |
| google-api-python-client | ^2 | YouTube Data API v3 | `app/youtube/` |
| google-auth / google-auth-oauthlib | ^2 / ^1 | OAuth2 (installed-app flow) | `app/youtube/oauth.py` |
| pytest | ^8 | Tests (all offline/mocked) | `tests/` |

## Existing solutions — reuse instead of adding libraries

| Need | Existing solution | Location |
|---|---|---|
| HTTP requests | stdlib `urllib.request` (project does NOT use requests) | `app/telegram_client.py`, `app/tiktok/publish.py` |
| `.env` parsing | Hand-rolled loader (no python-dotenv); never overwrites existing env | `app/config.py:_load_env_file` |
| LLM calls | Groq multi-key pool + bounded backoff + 429/413 Retry-After | `app/groq_client.py` (never call Groq directly) |
| Bounded retry | Exponential backoff + jitter helpers | `app/retry.py` |
| Logging | `get_logger()` + `redact()` secret redaction | `app/logging_setup.py` |
| Config access | `Config.get("dotted.path")` / `require()`; secrets only via env | `app/config.py` |
| Notifications | Telegram success/failure alerts (redacted, never break the run) | `app/telegram_client.py` |
| Health check | `doctor` PASS/FAIL/WARN table (`--online` for network) | `app/doctor.py` |

## Testing

- `pytest` + `pytest.ini` (`pythonpath = .`, `testpaths = tests`, `-q`)
- All offline/mocked; `tests/conftest.py` provides fixtures, `tests/qc_fixtures.py` reused by QC tests
- Run: `python -m pytest -q`

## Rendering conventions

- Frames: Pillow RGB composite → rawvideo rgb24 piped to FFmpeg → H.264 parts → concat → mux audio
- Performance contract: ~12k frames/week; pre-composited backgrounds cached per quantized camera rect; target ≤ ~80 ms/frame (4-core)
- Art backends dispatch per profile (Fernwood base / stickman override) — see `app/render/art/memory.md`

## Version recording rule

Record major/semver ranges (e.g. `^10`); precise versions come from requirements.txt / lock files.
