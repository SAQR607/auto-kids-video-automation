"""Camera view-rect + sub-pixel compositing invariants.

Regression suite for the camera defect where _view_rect pinned x0 to 0
(background exactly frame-aspect wide => bg_w - w == 0), making pan_l/pan_r/
drift-x dead cameras in every episode, and the 8 px cache quantization that
stalled all motion.
"""

import numpy as np

from app.render import scene

BG_W, BG_H = 2200, 1400
VW, VH = 1920, 1080
PARALLAX_K = list(scene._PARALLAX.values())
CAMERAS = ["static", "push_in", "pull_out", "pan_l", "pan_r", "drift"]
PS = [0.0, 0.25, 0.5, 0.75, 1.0]


def test_pan_camera_travels():
    """pan_l must actually move the view window (was pinned at x0=0)."""
    for cam in ("pan_l", "pan_r"):
        for k in PARALLAX_K:
            xs = [scene._view_rect(cam, p, VW, VH, BG_W, BG_H, k)[0] for p in PS]
            assert max(xs) - min(xs) > 40, f"{cam} k={k} travel {max(xs) - min(xs):.1f}px"


def test_rect_always_inside_background():
    """No black edges: window bounds within canvas for every camera/progress."""
    for cam in CAMERAS:
        for k in PARALLAX_K:
            for p in PS:
                x0, y0, x1, y1 = scene._view_rect(cam, p, VW, VH, BG_W, BG_H, k)
                assert x0 >= -1e-6 and y0 >= -1e-6, (cam, k, p, x0, y0)
                assert x1 <= BG_W + 1e-6 and y1 <= BG_H + 1e-6, (cam, k, p, x1, y1)


def test_rect_preserves_aspect():
    ar = VW / VH
    for cam in CAMERAS:
        for k in PARALLAX_K:
            for p in PS:
                x0, y0, x1, y1 = scene._view_rect(cam, p, VW, VH, BG_W, BG_H, k)
                assert abs((x1 - x0) / (y1 - y0) - ar) / ar < 0.01, (cam, k, p)


def test_static_camera_constant():
    """static must not move regardless of progress (encoder-flicker contract)."""
    for k in PARALLAX_K:
        assert scene._view_rect("static", 0.0, VW, VH, BG_W, BG_H, k) == \
            scene._view_rect("static", 1.0, VW, VH, BG_W, BG_H, k), k


def test_push_in_zooms_in():
    """push_in must shrink the window (zoom) between start and end."""
    for k in PARALLAX_K:
        w0 = scene._view_rect("push_in", 0.0, VW, VH, BG_W, BG_H, k)[2] - \
            scene._view_rect("push_in", 0.0, VW, VH, BG_W, BG_H, k)[0]
        w1 = scene._view_rect("push_in", 1.0, VW, VH, BG_W, BG_H, k)[2] - \
            scene._view_rect("push_in", 1.0, VW, VH, BG_W, BG_H, k)[0]
        assert w1 < w0, k


def test_margin_uniform_across_cameras():
    """Every camera fits the same motion margin => cuts never jump scale."""
    s_static = None
    for cam in CAMERAS:
        # window size at p=0.5 varies only via zoom (z), never via pan
        x0, y0, x1, y1 = scene._view_rect(cam, 0.5, VW, VH, BG_W, BG_H, 1.0)
        w, h = x1 - x0, y1 - y0
        if cam in ("static", "pan_l", "pan_r", "drift"):
            if s_static is None:
                s_static = (w, h)
            else:
                assert abs(w - s_static[0]) < 1e-6 and abs(h - s_static[1]) < 1e-6, cam


def test_rect_key_quantum():
    """0.5 px cache quantum: sub-0.5 px motion reuses, beyond it recomposes."""
    a = scene._rect_key((10.0, 10.0, 100.0, 100.0))
    assert scene._rect_key((10.2, 10.1, 100.2, 100.0)) == a
    assert scene._rect_key((10.6, 10.0, 100.0, 100.0)) != a
    # 8 px quantization (the old defect) would have made these equal:
    assert scene._rect_key((10.0, 10.0, 100.0, 100.0)) != \
        scene._rect_key((18.0, 10.0, 100.0, 100.0))


def test_composed_bg_pan_actually_moves():
    """End-to-end: pan_l background differs across the scene and stays RGB."""
    a = scene._composed_bg("glimmer_meadow", "day", "pan_l", 0.0, 320, 180)
    b = scene._composed_bg("glimmer_meadow", "day", "pan_l", 1.0, 320, 180)
    assert a.size == (320, 180) and a.mode == "RGB"
    assert b.mode == "RGB"
    diff = np.abs(np.asarray(a, dtype=np.int16) - np.asarray(b, dtype=np.int16))
    assert diff.mean() > 1.0, f"pan_l produced {diff.mean():.3f} mean abs diff (frozen?)"


def test_composed_bg_static_identical():
    a = scene._composed_bg("glimmer_meadow", "day", "static", 0.0, 320, 180)
    b = scene._composed_bg("glimmer_meadow", "day", "static", 1.0, 320, 180)
    assert np.array_equal(np.asarray(a), np.asarray(b))


# ---------------------------------------------------- perf optimization ----
# Zero-parallax cameras (static/push/pull) transform the pre-flattened
# source once instead of four layers; zoom cameras use a coarser cache
# quantum. Both must be quality-neutral.


def test_rect_key_zoom_camera_coarser():
    """push_in/pull_out quantize coarser than translation cameras."""
    r = (100.0, 100.0, 1000.0, 1000.0)
    # sub-quantum zoom step: <=1 px lateral, <=2 px scale (bucket [999,1001))
    r_zoom_step = (100.4, 100.4, 1000.8, 1000.8)
    # zoom grid: 1 px lateral / 2 px scale -> same key
    assert scene._rect_key(r_zoom_step, "push_in") == scene._rect_key(r, "push_in")
    assert scene._rect_key(r_zoom_step, "pull_out") == scene._rect_key(r, "pull_out")
    # translation grid: 0.5 px -> different key (pan smoothness contract)
    assert scene._rect_key(r_zoom_step, "pan_l") != scene._rect_key(r, "pan_l")
    assert scene._rect_key(r_zoom_step, "static") != scene._rect_key(r, "static")
    # a real zoom step (>2 px scale) still recomposes
    assert scene._rect_key((103.0, 103.0, 1006.0, 1006.0), "push_in") != \
        scene._rect_key(r, "push_in")


def test_zero_parallax_cameras_use_flatten_path():
    """static/push/pull must hit the flattened source (single affine)."""
    scene._FLAT_CACHE.clear()
    scene._BG_CACHE.clear()
    scene._composed_bg("glimmer_meadow", "day", "push_in", 0.3, 320, 180)
    assert ("glimmer_meadow", "day") in scene._FLAT_CACHE, "push_in bypassed flatten"
    scene._FLAT_CACHE.clear()
    scene._BG_CACHE.clear()
    scene._composed_bg("glimmer_meadow", "day", "pan_l", 0.3, 320, 180)
    assert ("glimmer_meadow", "day") not in scene._FLAT_CACHE, "pan_l must stay layered"


def test_flatten_matches_layered_zero_parallax():
    """Flattened compose ~= per-layer compose for push_in (same rect for all
    layers => identical framing; only resample order at alpha edges differs)."""
    a = scene._composed_bg("glimmer_meadow", "day", "push_in", 0.6, 640, 360)
    b = scene._composed_bg_layered("glimmer_meadow", "day", "push_in", 0.6, 640, 360)
    assert a.size == b.size and a.mode == b.mode == "RGB"
    diff = np.abs(np.asarray(a, dtype=np.int16) - np.asarray(b, dtype=np.int16))
    assert diff.mean() < 2.0, f"flatten/layered diverge: mean {diff.mean():.2f}"


def test_flatten_cache_reused():
    """Second call for the same (loc, tod) returns the cached image."""
    scene._FLAT_CACHE.clear()
    a = scene._flattened_source("glimmer_meadow", "day")
    b = scene._flattened_source("glimmer_meadow", "day")
    assert a is b
    assert a.mode == "RGB" and a.size == (2200, 1400)
