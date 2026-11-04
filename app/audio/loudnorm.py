"""2-pass EBU R128 loudness normalization via ffmpeg's loudnorm filter.

The raw mix lands around -19 LUFS; delivery targets -16 LUFS with true
peak <= -1.5 dBTP (YouTube/TikTok headroom). Two passes:

1. measure  — single-pass loudnorm with ``print_format=json`` (the filter
   only reports accurate stats when it is not applying them);
2. apply    — re-run with the measured values in ``linear=true`` mode, a
   constant gain that preserves the speech/music ratio built by ducking
   (dynamic mode would squash the contrast back down).

ffmpeg is already a hard pipeline dependency (doctor, render pipe, QC) —
no new libraries. The parser lives here; ``app.bench.metrics_audio``
imports it for the loudness gate.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

TARGET_I = -16.0
TARGET_TP = -1.5
TARGET_LRA = 11.0


def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if not exe:
        raise RuntimeError("ffmpeg not found on PATH")
    return exe


def parse_loudnorm(stderr: str) -> dict:
    """Extract the loudnorm JSON block from ffmpeg stderr.

    ffmpeg prints extra text (progress lines, summaries) around the block, so
    locate the flat {"input_i": ...} object explicitly instead of guessing
    offsets — non-greedy up to the first closing brace is safe because
    loudnorm's JSON values are flat scalars.
    """
    m = re.search(r"\{\s*\"input_i\".*?\}", stderr, re.DOTALL)
    if not m:
        raise RuntimeError(f"loudnorm produced no JSON: {stderr[-300:]}")
    return json.loads(m.group(0))


def _num(data: dict, key: str) -> float | None:
    raw = str(data.get(key, "")).strip()
    if raw in ("", "-inf", "inf", "nan"):
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def measure(path: str | Path) -> dict[str, float | None]:
    """Single-pass loudnorm measurement: integrated LUFS, true peak, LRA."""
    out = subprocess.run(
        [_ffmpeg(), "-i", str(path), "-af",
         f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}:print_format=json",
         "-f", "null", "-"],
        capture_output=True, text=True, timeout=300,
    )
    data = parse_loudnorm(out.stderr or "")
    return {
        "lufs_integrated": _num(data, "input_i"),
        "true_peak_db": _num(data, "input_tp"),
        "lra": _num(data, "input_lra"),
        "threshold_db": _num(data, "input_thresh"),
        "target_offset_db": _num(data, "target_offset"),
    }


def normalize(src: str | Path, dst: str | Path, *,
              target_i: float = TARGET_I, target_tp: float = TARGET_TP,
              target_lra: float = TARGET_LRA) -> dict[str, float | None]:
    """Two-pass loudnorm ``src`` -> ``dst`` (may be the same path, atomic).

    Returns the pass-1 measurement (``lufs_integrated`` etc.). A silent or
    unmeasurable input is copied through untouched — normalizing silence
    would only amplify the noise floor.
    """
    import os
    import tempfile

    import soundfile as sf

    src, dst = Path(src), Path(dst)
    m = measure(src)
    needed = ("lufs_integrated", "true_peak_db", "lra", "threshold_db", "target_offset_db")
    if any(m.get(k) is None for k in needed):
        # silence / unmeasurable input: normalizing would only raise the noise floor
        if src != dst:
            shutil.copyfile(src, dst)
        return m

    info = sf.info(str(src))
    af = (
        f"loudnorm=I={target_i}:TP={target_tp}:LRA={target_lra}"
        f":measured_I={m['lufs_integrated']}"
        f":measured_TP={m['true_peak_db']}"
        f":measured_LRA={m['lra']}"
        f":measured_thresh={m['threshold_db']}"
        f":offset={m['target_offset_db']}"
        f":linear=true:print_format=json"
    )
    # same-dir temp + os.replace: ffmpeg cannot read and write one file, and
    # a crash must not leave a half-written master behind
    fd, tmp_name = tempfile.mkstemp(suffix=".wav", dir=str(dst.parent))
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        try:
            subprocess.run(
                [_ffmpeg(), "-y", "-i", str(src), "-af", af,
                 "-ar", str(info.samplerate), "-ac", str(info.channels),
                 "-c:a", "pcm_s16le", str(tmp)],
                capture_output=True, text=True, timeout=600, check=True,
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                f"loudnorm pass 2 failed: {(exc.stderr or '')[-400:]}") from exc
        os.replace(tmp, dst)
    finally:
        tmp.unlink(missing_ok=True)
    return m
