"""Entry-boundary transitions (prev-scene blend) + emphasis punch-in.

The incoming scene owns its boundary: the previous scene's last frame is
cross-dissolved / wiped under the new one for 0.6s (no black fades), and
excited/amazed/surprised beats punch-zoom the whole frame 8%.
"""

from __future__ import annotations

from PIL import Image, ImageChops, ImageStat

from app.render import scene as scene_mod
from app.render.scene import _punch, render_frame

W, H = 96, 54
_CFG: dict = {}
_SCENES = {
    "fade": {"scene_id": "s", "location": "hollow_oak_village",
             "time_of_day": "day", "camera": "static", "transition_in": "fade",
             "characters": [], "props": []},
    "cut": {"scene_id": "s", "location": "hollow_oak_village",
            "time_of_day": "day", "camera": "static", "transition_in": "cut",
            "characters": [], "props": []},
    "wipe": {"scene_id": "s", "location": "hollow_oak_village",
             "time_of_day": "day", "camera": "static",
             "transition_in": "wipe_leaves", "characters": [], "props": []},
}
# prev scene's "last frame": a solid color so blends are trivially checkable
PREV_BYTES = Image.new("RGB", (W, H), (10, 200, 30)).tobytes()


def _render(key: str, t: float, prev=None) -> Image.Image:
    return render_frame(_SCENES[key], t, 30.0, _CFG,
                        frame_w=W, frame_h=H, prev=prev)


def _mean_diff(a: Image.Image, b: Image.Image) -> float:
    return ImageStat.Stat(ImageChops.difference(a, b)).mean[0]


def test_dissolve_starts_on_previous_frame():
    out = _render("fade", 0.0, prev=(PREV_BYTES, 30.0))
    assert out.tobytes() == PREV_BYTES  # t=0 -> 100% previous scene


def test_dissolve_ends_on_current_frame():
    prev = _render("fade", 0.0)  # plain frame stands in for the current scene
    blended = _render("fade", 0.59, prev=(PREV_BYTES, 30.0))
    assert _mean_diff(blended, prev) < 6.0  # 98% current, 1.7% prev color


def test_cut_with_prev_is_hard_boundary():
    """transition_in=cut (or prev too short) must not blend at all."""
    plain = _render("cut", 0.0)
    out = _render("cut", 0.0, prev=(PREV_BYTES, 30.0))
    assert out.tobytes() == plain.tobytes()


def test_short_prev_scene_skips_blend():
    plain = _render("fade", 0.0)
    out = _render("fade", 0.0, prev=(PREV_BYTES, 0.8))  # < 1.2s: hard cut
    assert out.tobytes() == plain.tobytes()


def test_wipe_starts_on_previous_and_ends_on_current():
    assert _render("wipe", 0.0, prev=(PREV_BYTES, 30.0)).tobytes() == PREV_BYTES
    plain = _render("wipe", 0.0)
    end = _render("wipe", 0.59, prev=(PREV_BYTES, 30.0))
    assert end.tobytes() == plain.tobytes()  # final wipe step fully reveals


def test_no_prev_is_hard_boundary():
    """Shorts / scene 0 / samples pass prev=None: plain frame, no blend."""
    assert _render("fade", 0.0).size == (W, H)


# --- punch ------------------------------------------------------------------

def test_punch_envelope():
    lines = [{"emotion": "excited", "start": 1.0, "end": 3.0}]
    assert _punch(lines, 0.5) == 0.0          # before the line
    assert abs(_punch(lines, 1.15) - 1.0) < 0.01  # attack peak
    assert _punch(lines, 1.55) == 0.0         # released after 0.55s
    assert 0.0 < _punch(lines, 1.3) < 1.0     # mid-release
    assert _punch([{"emotion": "happy", "start": 1.0}], 1.1) == 0.0
    assert _punch([], 1.0) == 0.0


def test_punch_zooms_the_frame():
    """An emphasis beat must actually change the rendered frame (8% crop)."""
    plain = render_frame(_SCENES["fade"], 0.15, 30.0, _CFG,
                         frame_w=W, frame_h=H)
    excited = render_frame(
        _SCENES["fade"], 0.15, 30.0, _CFG, frame_w=W, frame_h=H,
        lines=[{"speaker": "juni", "text": "nine words of very big news here",
                "emotion": "excited", "start": 0.0, "end": 2.0}])
    assert excited.size == plain.size
    assert _mean_diff(excited, plain) > 1.0  # background visibly rescaled


def test_wipe_mask_reveals_left_to_right_completion():
    """Mask contract: 255 (previous scene) everywhere at step 0, 0 at step 23."""
    m0 = scene_mod._wipe_mask(0.0, (32, 8))
    m1 = scene_mod._wipe_mask(1.0 - 1e-9, (32, 8))
    assert m0.getextrema() == (255, 255)
    assert m1.getextrema() == (0, 0)
