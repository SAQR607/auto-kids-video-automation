"""Loudnorm tests: parser (offline) + two-pass normalize smoke (real ffmpeg)."""

from __future__ import annotations

import shutil

import numpy as np
import pytest

from app.audio import loudnorm

HAS_FFMPEG = bool(shutil.which("ffmpeg") or shutil.which("ffmpeg.exe"))

SAMPLE_JSON = (
    "[Parsed_loudnorm_0 @ 0x55e] {\n"
    '    "input_i" : "-19.37",\n'
    '    "input_tp" : "-0.88",\n'
    '    "input_lra" : "5.40",\n'
    '    "input_thresh" : "-29.60",\n'
    '    "output_i" : "-16.02",\n'
    '    "output_tp" : "-1.49",\n'
    '    "output_lra" : "5.30",\n'
    '    "output_thresh" : "-26.20",\n'
    '    "target_offset" : "0.08"\n'
    "}\n"
    "some trailing progress noise\n"
)


def test_parse_loudnorm_extracts_json_block():
    data = loudnorm.parse_loudnorm("prefix\n" + SAMPLE_JSON)
    assert data["input_i"] == "-19.37"
    assert data["target_offset"] == "0.08"


def test_parse_loudnorm_raises_without_json():
    with pytest.raises(RuntimeError):
        loudnorm.parse_loudnorm("no json here\n")


def test_num_helper_tolerates_nonfinite():
    assert loudnorm._num({"a": "-inf"}, "a") is None
    assert loudnorm._num({"a": "nan"}, "a") is None
    assert loudnorm._num({}, "a") is None
    assert loudnorm._num({"a": "1.5"}, "a") == 1.5


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_normalize_two_pass_hits_targets(tmp_path):
    import soundfile as sf

    sr = 44100
    t = np.arange(sr * 6) / sr
    y = np.stack([0.05 * np.sin(2 * np.pi * 440 * t)] * 2, axis=1).astype(np.float32)
    src = tmp_path / "in.wav"
    dst = tmp_path / "out.wav"
    sf.write(src, y, sr, subtype="PCM_16")

    m = loudnorm.normalize(src, dst)
    assert m["lufs_integrated"] is not None and m["lufs_integrated"] < -3.0

    got = loudnorm.measure(dst)
    assert got["lufs_integrated"] is not None
    assert -16.8 <= got["lufs_integrated"] <= -15.2, got
    assert got["true_peak_db"] is not None and got["true_peak_db"] <= -1.0, got

    info = sf.info(str(dst))
    assert info.samplerate == sr
    assert info.channels == 2
    assert abs(info.duration - 6.0) < 0.05  # duration must not drift


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_normalize_in_place(tmp_path):
    import soundfile as sf

    sr = 44100
    y = (0.05 * np.sin(2 * np.pi * 440 * np.arange(sr * 4) / sr)).astype(np.float32)
    y = np.stack([y, y], axis=1)
    src = tmp_path / "master.wav"
    sf.write(src, y, sr, subtype="PCM_16")

    loudnorm.normalize(src, src)  # same path: temp + atomic replace
    got = loudnorm.measure(src)
    assert got["lufs_integrated"] is not None
    assert -16.8 <= got["lufs_integrated"] <= -15.2, got
    # only the target file remains — the mkstemp temp was replaced/removed
    assert [p.name for p in tmp_path.glob("*.wav")] == ["master.wav"]
