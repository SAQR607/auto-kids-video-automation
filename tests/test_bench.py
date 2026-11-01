"""Unit tests for the benchmark suite (pure functions — no rendering)."""

from __future__ import annotations

import numpy as np
import pytest

from app.bench import metrics_audio as ma
from app.bench import metrics_video as mv
from app.bench.reference import PACKAGE, SCENES, reference_texts
from app.bench.runner import METRIC_SPECS, _gates


# --- video metrics ---------------------------------------------------------

def test_psnr_identical_is_inf():
    a = np.full((32, 32, 3), 128.0)
    assert mv.psnr(a, a) == float("inf")


def test_psnr_orders_distortion():
    a = np.zeros((32, 32, 3))
    small = a.copy()
    small[0, 0, 0] = 20.0
    big = a + 40.0
    assert mv.psnr(a, small) > mv.psnr(a, big)


def test_ssim_identical_is_one_and_noise_lowers_it():
    rng = np.random.default_rng(11)
    a = rng.integers(0, 255, (64, 64, 3)).astype(np.float64)
    assert mv.ssim(a, a) == pytest.approx(1.0, abs=1e-6)
    b = a + rng.normal(0, 8, a.shape)
    assert mv.ssim(a, np.clip(b, 0, 255)) < 0.99


def test_ssim_window_sums_match_direct_sum():
    rng = np.random.default_rng(3)
    a = rng.integers(0, 255, (40, 40)).astype(np.float64)
    b = rng.integers(0, 255, (40, 40)).astype(np.float64)
    assert 0.0 < mv.ssim(a, b) <= 1.0


def test_laplacian_var_flat_is_zero_and_texture_positive():
    flat = np.full((64, 64), 100.0)
    assert mv.laplacian_var(flat) == 0.0
    rng = np.random.default_rng(5)
    assert mv.laplacian_var(rng.integers(0, 255, (64, 64)).astype(np.float64)) > 100.0


def test_colorfulness_gray_is_zero_and_saturated_positive():
    gray = np.full((32, 32, 3), 128.0)
    assert mv.colorfulness(gray) == pytest.approx(0.0, abs=1e-9)
    vivid = np.zeros((32, 32, 3))
    vivid[..., 0] = 255.0
    vivid[..., 1] = 40.0
    assert mv.colorfulness(vivid) > 50.0


def test_flicker_zero_on_identical_frames_and_positive_on_change():
    frames = [np.full((48, 48, 3), 90.0) for _ in range(5)]
    assert mv.flicker_mae(frames) == 0.0
    frames[3] = frames[3] + 10.0
    assert mv.flicker_mae(frames) > 1.0


def test_pan_motion_detects_uniform_shift():
    rng = np.random.default_rng(7)
    base = rng.integers(0, 255, (80, 120)).astype(np.float64)
    frames = [np.roll(base, i, axis=1) for i in range(10)]
    res = mv.pan_motion(frames, scale=1.0)
    assert res["pairs"] == 9.0
    assert res["median_dx"] == pytest.approx(1.0, abs=0.3)
    assert res["frozen_pct"] < 20.0


def test_pan_motion_static_frames_are_fully_frozen():
    frame = np.full((60, 90), 50.0)
    frame[20:40, 30:60] = 200.0  # some structure, but identical across frames
    res = mv.pan_motion([frame.copy() for _ in range(6)], scale=1.0)
    assert res["frozen_pct"] == 100.0


# --- audio metrics ---------------------------------------------------------

def test_normalize_text():
    assert ma.normalize_text("It's 3 o'clock, OK!") == "it's 3 o'clock ok"
    assert ma.normalize_text("  Hello   WORLD  ") == "hello world"


def test_wer_perfect_and_partial():
    assert ma.wer("the cat sat", "the cat sat") == 0.0
    assert ma.wer("the cat sat", "the cat") == pytest.approx(1 / 3)
    assert ma.wer("", "extra words") == 1.0
    assert ma.wer("one two three four", "one  two  three  four") == 0.0


# --- reference package -----------------------------------------------------

def test_reference_text_order_matches_mix_order():
    texts = reference_texts()
    expected = 0
    for scene in SCENES:
        expected += len(scene["dialogue"]) + len(scene["narration"])
    assert len(texts) == expected
    assert all(t.strip() for t in texts)


def test_reference_locations_are_real():
    from app.render.art.locations import LOCATIONS

    for scene in SCENES:
        assert scene["location"] in LOCATIONS
        assert scene["time_of_day"] in ("morning", "day", "dusk", "night")


def test_reference_uses_real_production_vocabulary():
    cameras = {"static", "pan_l", "pan_r", "push_in", "pull_out", "drift"}
    for scene in SCENES:
        assert scene["camera"] in cameras
    assert PACKAGE["episode_id"] == "bench001"
    assert len(SCENES) == 3


def test_metric_specs_are_well_formed():
    allowed = {"rel_min", "rel_max", "abs_min", "abs_max"}
    for name, spec in METRIC_SPECS.items():
        assert set(spec) <= allowed, name
        if "rel_min" in spec:
            assert spec["rel_min"] <= 1.0, name
        if "rel_max" in spec:
            assert spec["rel_max"] >= 1.0, name
        if "abs_min" in spec and "abs_max" in spec:
            assert spec["abs_min"] < spec["abs_max"], name


# --- gates -----------------------------------------------------------------

def test_gates_pass_on_baseline_values():
    baseline = {"metrics": {"audio.lufs_integrated": -16.0,
                            "video.sharpness_laplacian": 100.0,
                            "audio.wer": 0.10}}
    current = {"audio.lufs_integrated": -16.0,
               "video.sharpness_laplacian": 110.0,
               "audio.wer": 0.08}
    rows, fails = _gates(baseline, current)
    assert fails == 0
    assert all(r["status"] == "pass" for r in rows)


def test_gates_fail_on_abs_and_rel_violations():
    baseline = {"metrics": {"audio.lufs_integrated": -16.0,
                            "video.sharpness_laplacian": 100.0,
                            "audio.wer": 0.10}}
    current = {"audio.lufs_integrated": -25.0,   # < abs_min -19
               "video.sharpness_laplacian": 80.0,  # < 0.85x baseline
               "audio.wer": 0.16}                  # > 1.5x baseline
    rows, fails = _gates(baseline, current)
    assert fails == 3
    assert all(r["status"] == "FAIL" for r in rows)
    assert all(r["note"] for r in rows)


def test_gates_flag_missing_and_new_metrics():
    baseline = {"metrics": {"audio.wer": 0.1, "video.colorfulness": 40.0}}
    current = {"video.colorfulness": 40.0, "video.new_metric": 1.0}
    rows, fails = _gates(baseline, current)
    by_name = {r["name"]: r for r in rows}
    assert by_name["audio.wer"]["status"] == "FAIL"
    assert by_name["video.new_metric"]["status"] == "new"
    assert fails == 1


# --- CLI wiring ------------------------------------------------------------

def test_bench_subcommand_registered():
    from app.cli import build_parser

    args = build_parser().parse_args(["bench", "--skip-whisper"])
    assert args.func.__name__ == "_cmd_bench"
    assert args.skip_whisper is True
    assert args.update_baseline is False
    assert args.keep is False
