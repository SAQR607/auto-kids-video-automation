"""Audio metrics: loudness (EBU R128 via ffmpeg), speech prominence, WER, RTF.

Reuses existing project dependencies only (ffmpeg, soundfile, faster-whisper
already in requirements.txt — no new dependencies).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import numpy as np

_EPS = 1e-12


def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if not exe:
        raise RuntimeError("ffmpeg not found on PATH")
    return exe


def loudness(path: str | Path) -> dict[str, float | None]:
    """Single-pass loudnorm measurement: integrated LUFS, true peak, LRA."""
    out = subprocess.run(
        [_ffmpeg(), "-i", str(path), "-af",
         "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True, timeout=300,
    )
    stderr = out.stderr or ""
    start = stderr.rfind("{")
    if start < 0:
        raise RuntimeError(f"loudnorm produced no JSON: {stderr[-300:]}")
    data = json.loads(stderr[start:])

    def num(key: str) -> float | None:
        raw = str(data.get(key, "")).strip()
        if raw in ("", "-inf", "inf", "nan"):
            return None
        try:
            return float(raw)
        except ValueError:
            return None

    return {
        "lufs_integrated": num("input_i"),
        "true_peak_db": num("input_tp"),
        "lra": num("input_lra"),
        "threshold_db": num("input_thresh"),
    }


def speech_prominence(wav_path: str | Path, timing: dict[str, Any]) -> float | None:
    """RMS(speech windows) - RMS(non-speech windows), in dB.

    Speech windows come from timing.json lines (scene start + line offsets),
    dilated slightly; guards the narration-over-music intelligibility level.
    """
    import soundfile as sf

    data, sr = sf.read(str(wav_path), dtype="float32", always_2d=True)
    mono = data.mean(axis=1)
    total = len(mono) / float(sr)

    speech = np.zeros(len(mono), dtype=bool)
    guard = int(0.15 * sr)
    for scene in timing.get("scenes", []):
        s_start = float(scene.get("start", 0.0))
        for line in scene.get("lines", []):
            a = int(max(0.0, s_start + float(line.get("start", 0.0))) * sr)
            b = int(min(total, s_start + float(line.get("end", 0.0))) * sr)
            if b > a:
                speech[max(0, a - guard):min(len(mono), b + guard)] = True

    # exclude the 1 s fades at both ends from either bucket
    fade = int(1.0 * sr)
    speech[:fade] = False
    speech[-fade:] = False
    rest = ~speech
    if speech.sum() < sr or rest.sum() < sr:
        return None

    def db(x: np.ndarray) -> float:
        return 20.0 * float(np.log10(np.sqrt(float(np.mean(x ** 2))) + _EPS))

    return db(mono[speech]) - db(mono[rest])


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def wer(reference: str, hypothesis: str) -> float:
    """Word error rate (Levenshtein over words) — 0.0 = perfect."""
    ref = normalize_text(reference).split()
    hyp = normalize_text(hypothesis).split()
    if not ref:
        return 0.0 if not hyp else 1.0
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, start=1):
        cur = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, start=1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h))
        prev = cur
    return prev[-1] / len(ref)


def transcribe(path: str | Path, seconds: float | None = None) -> str:
    """Whisper tiny transcript (same invocation as app/qc/video_qc.py)."""
    from faster_whisper import WhisperModel

    model = WhisperModel("tiny", device="cpu", compute_type="int8",
                         cpu_threads=int(os.environ.get("WHISPER_THREADS") or 2))
    kwargs: dict[str, Any] = {"beam_size": 1, "language": "en"}
    if seconds:
        kwargs["clip_timestamps"] = [0.0, float(seconds)]
    segments, _ = model.transcribe(str(path), **kwargs)
    return " ".join(seg.text.strip() for seg in segments).strip()


def tts_rtf(texts: list[str], voice: str, speed: float) -> dict[str, float]:
    """Fresh-cache TTS real-time factor for representative lines.

    Uses a throwaway cache dir so the disk cache never masks synthesis cost.
    """
    import tempfile

    from ..audio import tts

    audio_sec = 0.0
    with tempfile.TemporaryDirectory(prefix="bench_tts_") as tmp:
        t0 = time.perf_counter()
        for text in texts:
            samples, sr = tts.synth(text, voice=voice, speed=speed, cache_dir=Path(tmp))
            audio_sec += len(samples) / float(sr)
        wall = time.perf_counter() - t0
    return {
        "wall_sec": round(wall, 3),
        "audio_sec": round(audio_sec, 3),
        "rtf": round(wall / audio_sec, 3) if audio_sec else 0.0,
    }
