"""Character sprites: deterministic PIL drawing for 7 cast members.

CalArts style (approved direction 2026-11-05, matched to the user's
reference sheet): FLAT color blocking — outline only on the silhouette
and key features (eyes, cap, clothing); interior patches (muzzle, belly,
stripes) are color-on-color with no line. Big heads, oversized white
eyes with solid pupils, thin brows, seamless mitten hands, big feet.
No blush, no shading.

`get_sprite(char_id, state, expression, frame=0, *, blink=False,
phase=0)` -> RGBA 600x760, cached.
States: 13 (binding). Expressions: manifest list (14).
Walk/run use 4-frame cycles (frame 0-3) with per-frame arm swing, body
bob and tail swing. `phase` (0-3) is the slow breathing sub-pose for
non-walk states; `blink` closes the eyes for that call — the renderer
derives both from frame_no (deterministic idle life).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from PIL import Image

from . import palette as P
from . import png_sprites
from .backend import stickman
from .shapes import aa_layer, capsule, circle, flatten, oval, poly, rrect, wedge

SIZE = (600, 760)
GROUND = 716
OW = 8    # CalArts chunky silhouette outline

MOUTH_DARK = "#6B3333"
TONGUE = "#F49AC1"

# breathing sub-pose: body+head rise/fall, feet stay planted
BREATH = (0, 2, 3, 2)
# walk/run vertical bounce and arm swing per cycle frame (pass frames lift)
_WALK = dict(bob=(0, -4, 0, -4), swing=(16, 0, -16, 0), tail=(1.0, 0.2, -1.0, 0.2))
_RUN = dict(bob=(0, -6, 0, -6), swing=(30, 0, -30, 0), tail=(1.0, 0.2, -1.0, 0.2))

# per-species CalArts proportions (body rx, ry) / (head rx, ry)
_BODY = {"juni": (92, 118), "bramble": (110, 116), "marlow": (94, 124),
         "wren": (92, 112), "willowby": (96, 126), "fern": (90, 120),
         "pipkin": (86, 106)}
_HEAD = {"juni": (132, 120), "bramble": (126, 114), "marlow": (118, 108),
         "wren": (114, 110), "willowby": (120, 112), "fern": (116, 108),
         "pipkin": (118, 110)}


@dataclass(frozen=True)
class Pose:
    arm_l: float = 20.0      # degrees, + swings outward
    arm_r: float = -20.0
    legs: str = "stand"      # stand | walk | run | sit
    bob: int = 0
    tail: float = 0.0        # swing
    mouth: str | None = None
    eyes: str | None = None
    brows: str | None = None
    hands_up: bool = False


POSES: dict[str, Pose] = {
    "idle": Pose(),
    "walk": Pose(arm_l=28, arm_r=-28, legs="walk", tail=0.15),
    "run": Pose(arm_l=50, arm_r=-50, legs="run", tail=0.35),
    "sit": Pose(arm_l=34, arm_r=-34, legs="sit", tail=0.1),
    "talk_closed": Pose(arm_l=26, arm_r=-26, mouth="closed"),
    "talk_mid": Pose(arm_l=32, arm_r=-32, mouth="mid"),
    "talk_open": Pose(arm_l=40, arm_r=-40, mouth="open"),
    "happy": Pose(arm_l=70, arm_r=-70, bob=-5, tail=0.3, mouth="smile", eyes="happy", brows="up"),
    "sad": Pose(arm_l=6, arm_r=-6, bob=4, tail=-0.3, mouth="frown", brows="sad"),
    "surprised": Pose(arm_l=64, arm_r=-64, bob=-3, tail=0.5, mouth="o", eyes="wide", brows="up"),
    "sleep": Pose(arm_l=12, arm_r=-12, bob=3, mouth="closed", eyes="closed"),
    "point": Pose(arm_l=80, arm_r=-12, tail=0.1, mouth="smile"),
    "carry": Pose(arm_l=54, arm_r=-54, hands_up=True, mouth="smile"),
}

# expression -> face params
FACES: dict[str, dict] = {
    "neutral": {},
    "happy": dict(eyes="happy", mouth="smile", brows="up"),
    "sad": dict(mouth="frown", brows="sad"),
    "surprised": dict(eyes="wide", mouth="o", brows="up"),
    "curious": dict(brows="tilt", mouth="smile"),
    "excited": dict(eyes="happy", mouth="open", brows="up"),
    "determined": dict(brows="down", mouth="flat"),
    "sleepy": dict(eyes="closed", mouth="small"),
    "proud": dict(brows="up", mouth="smile", eyes="happy"),
    "confident": dict(brows="tilt", mouth="smile"),
    "worried": dict(brows="sad", mouth="small"),
    "silly": dict(eyes="wink", mouth="open"),
    "amazed": dict(eyes="wide", mouth="o", brows="up"),
    "brave": dict(brows="down", mouth="smile"),
}

SPECIES = ("juni", "bramble", "marlow", "wren", "willowby", "fern", "pipkin")

_CACHE: dict[tuple, Image.Image] = {}


def get_sprite(char_id: str, state: str, expression: str, frame: int = 0,
               *, blink: bool = False, phase: int = 0) -> Image.Image:
    """Public API — cached, never raises on unknown ids (falls back)."""
    mod = stickman("characters")
    if mod is not None:
        return mod.get_sprite(char_id, state, expression, frame,
                              blink=blink, phase=phase)
    if char_id not in SPECIES:
        char_id = "juni"
    if state not in POSES:
        state = "idle"
    if expression not in FACES:
        expression = "neutral"
    if state in ("walk", "run"):
        frame %= 4
    else:
        frame = 0
    phase &= 3
    key = (char_id, state, expression, frame, blink, phase)
    img = _CACHE.get(key)
    if img is None:
        # hand-drawn PNG cast members first; None -> procedural PIL build
        img = png_sprites.build(char_id, state, expression, frame, size=SIZE)
        if img is None:
            img = _build(char_id, state, expression, frame, blink=blink,
                         phase=phase)
        _CACHE[key] = img
    return img


# ---------------------------------------------------------------- geometry --

def _walk_shift(state: str, frame: int) -> tuple[int, int]:
    """(left foot dx, right foot dx) per cycle frame."""
    if state == "walk":
        return ((0, 26), (16, 10), (26, 0), (10, -16))[frame]
    if state == "run":
        return ((-30, 34), (-8, 20), (34, -30), (20, -8))[frame]
    return (0, 0)


def _hand(sh_x: float, sh_y: float, ang: float, sign: int,
          hands_up: bool) -> tuple[float, float]:
    """Elbow-free CalArts noodle arm end. ang>0 = outward from body."""
    if hands_up:
        return sh_x + sign * 44, sh_y - 84
    a = math.radians(ang)
    ln = 104
    return sh_x + math.sin(a) * ln * sign, sh_y + math.cos(a) * ln


def _mass(d, pts, radii, color: str, grow: int) -> None:
    """Union of circles drawn as ONE mass (single silhouette, no interior
    seams). `grow` inflates every radius — used to lay an outline pass
    under the colour pass."""
    for (x, y), r in zip(pts, radii):
        rr = r + grow
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=color)


def _mitten(d, p0, p1, arm_w: float, hand_r: float, color: str) -> None:
    """Seamless CalArts mitten limb: one INK pass at width + 2*OW, then
    the colour pass on top — the outline therefore reads only along the
    outer silhouette, never between arm and hand (a separate hand circle
    would draw an interior ring, which the reference does not have).
    `arm_w` = limb thickness, `hand_r` = mitten radius at p1."""
    ink_w = arm_w + 2 * OW
    d.line([p0, p1], fill=P.INK, width=int(ink_w))
    d.ellipse([p0[0] - ink_w / 2, p0[1] - ink_w / 2,
               p0[0] + ink_w / 2, p0[1] + ink_w / 2], fill=P.INK)
    d.ellipse([p1[0] - hand_r - OW, p1[1] - hand_r - OW,
               p1[0] + hand_r + OW, p1[1] + hand_r + OW], fill=P.INK)
    d.line([p0, p1], fill=color, width=int(arm_w))
    d.ellipse([p0[0] - arm_w / 2, p0[1] - arm_w / 2,
               p0[0] + arm_w / 2, p0[1] + arm_w / 2], fill=color)
    d.ellipse([p1[0] - hand_r, p1[1] - hand_r,
               p1[0] + hand_r, p1[1] + hand_r], fill=color)


def _build(char_id: str, state: str, expression: str, frame: int,
           *, blink: bool = False, phase: int = 0) -> Image.Image:
    pose = POSES[state]
    img, d = aa_layer(SIZE)
    pal = _pal(char_id)
    walking = state in ("walk", "run")

    # vertical bob: walk/run bounce per frame; other states breathe
    if walking:
        cyc = _RUN if state == "run" else _WALK
        bob = pose.bob + cyc["bob"][frame]
        swing = cyc["swing"][frame]
        tail_swing = pose.tail * cyc["tail"][frame]
    else:
        bob = pose.bob + BREATH[phase]
        swing = 0.0
        tail_swing = pose.tail
    arm_l = pose.arm_l + swing
    arm_r = pose.arm_r - swing

    dx_l, dx_r = _walk_shift(state, frame)
    hip_l, hip_r = (256, 646), (344, 646)
    body_rx, body_ry = _BODY[char_id]
    head_rx, head_ry = _HEAD[char_id]
    body_cy = 542 + bob
    hx, hy = 300, 310 + bob
    sh_y = body_cy - 58
    sh_l, sh_r = 300 - (body_rx - 2), 300 + (body_rx - 2)

    # ----- silhouette (tail -> legs -> body -> arms -> ears -> head)
    _tail(d, char_id, pal, tail_swing)

    if pose.legs == "sit":
        _mitten(d, (258, 654), (214, 692), 52, 44, pal["body"])
        _mitten(d, (342, 654), (386, 692), 52, 44, pal["body"])
        oval(d, 200, 704, 36, 18,
             P.INK if char_id == "bramble" else pal["dark"], ow=OW)
        oval(d, 400, 704, 36, 18,
             P.INK if char_id == "bramble" else pal["dark"], ow=OW)
    else:
        for hip, dx, sign in ((hip_l, dx_l, -1), (hip_r, dx_r, 1)):
            foot = (hip[0] + dx + sign * 4, GROUND - 6)
            _mitten(d, hip, foot, 44, 40, pal["body"])
            # big dark foot — one rounded mass, silhouette outline only
            oval(d, foot[0] + sign * 10, foot[1] + 10, 36, 18,
                 P.INK if char_id == "bramble" else pal["dark"], ow=OW)

    oval(d, 300, body_cy, body_rx, body_ry, pal["body"], ow=OW)
    oval(d, 300, body_cy + 24, body_rx * 0.66, body_ry * 0.76,
         pal["belly"], ow=0)

    rhand = (sh_r, sh_y)
    for sh_x, ang, sign in ((sh_l, arm_l, -1), (sh_r, arm_r, 1)):
        ex, ey = _hand(sh_x, sh_y, ang, sign, pose.hands_up)
        _mitten(d, (sh_x, sh_y), (ex, ey), 32, 25, pal["body"])
        if sign > 0:
            rhand = (ex, ey)
        if pose is POSES.get("point") and sign < 0:
            _prop_hand(d, char_id, pose, ex, ey)

    _ears_behind(d, char_id, pal, hx, hy)
    oval(d, hx, hy, head_rx, head_ry, pal["body"], ow=OW)

    # ----- markings + face + accessories
    _body_mark(d, char_id, pal, body_cy, body_rx)
    _face_mark(d, char_id, pal, hx, hy)
    _face(d, hx, hy, expression, pose, char_id, blink)
    _accessories(d, char_id, pal, hx, hy, head_rx, head_ry)
    if pose is POSES.get("carry"):
        _carry_prop(d, char_id, *rhand)
    return flatten(img, SIZE)


def _pal(char_id: str) -> dict[str, str]:
    return {
        "juni": P.JUNI, "bramble": P.BRAMBLE, "marlow": P.MARLOW, "wren": P.WREN,
        "willowby": P.WILLOWBY, "fern": P.FERN, "pipkin": P.PIPkin,
    }[char_id]


# ---------------------------------------------------------------- per-species ---

def _tail(d, cid: str, pal: dict, swing: float) -> None:
    if cid == "juni":
        # ONE smooth bushy mass (reference: no bubble chain, no interior
        # lines) — INK silhouette pass first, colour pass over it, then
        # the dark stripe as a colour-on-colour capsule.
        pts = [(372, 612), (438, 572), (476, 476), (452, 376), (398, 322)]
        pts = [(x + swing * 30, y) for x, y in pts]
        radii = (46, 60, 68, 62, 50)
        _mass(d, pts, radii, P.INK, OW)
        _mass(d, pts, radii, pal["body"], 0)
        # dark stripe following the tail's outer curve
        capsule(d, (pts[3][0] + 6, pts[3][1] - 18),
                (pts[4][0] + 4, pts[4][1] + 26), 34, pal["dark"], ow=0)
        oval(d, pts[4][0], pts[4][1], 34, 30, pal["dark"], ow=0)
    elif cid == "bramble":
        capsule(d, (372, 616), (470 + swing * 26, 558), 36, pal["body"], ow=6)
        oval(d, 480 + swing * 26, 554, 26, 22, P.WHITE, ow=6)
    elif cid == "marlow":
        capsule(d, (372, 618), (476 + swing * 28, 648), 44, pal["body"], ow=6)
        oval(d, 490 + swing * 28, 652, 28, 24, pal["dark"], ow=6)
    elif cid == "wren":
        poly(d, [(370, 598), (456 + swing * 28, 512), (470 + swing * 28, 546),
                 (392, 638)], pal["dark"], ow=6)
    elif cid == "willowby":
        circle(d, 382 + swing * 22, 626, 36, P.WHITE, ow=6)
    elif cid == "fern":
        oval(d, 380 + swing * 20, 598, 28, 24, P.WHITE, ow=6)
    elif cid == "pipkin":
        pts2 = [(372, 626), (428 + swing * 22, 650), (464 + swing * 28, 620),
                (474 + swing * 28, 580)]
        for i in range(len(pts2) - 1):
            capsule(d, pts2[i], pts2[i + 1], 11, pal["dark"], ow=4)


def _ears_behind(d, cid, pal, hx, hy) -> None:
    if cid == "juni":
        # must clear the beanie (cap rx ~= 128) or the cap hides them
        for sx in (-1, 1):
            oval(d, hx + sx * 124, hy - 84, 34, 38, pal["body"], ow=OW)
            oval(d, hx + sx * 124, hy - 84, 17, 21, "#E8B4A6", ow=0,
                 outline="#E8B4A6")
    elif cid == "marlow":
        for sx in (-1, 1):
            oval(d, hx + sx * 88, hy - 88, 34, 38, pal["body"], ow=OW)
            oval(d, hx + sx * 88, hy - 88, 17, 21, "#E8B4A6", ow=0,
                 outline="#E8B4A6")
    elif cid == "bramble":
        for sx in (-1, 1):
            oval(d, hx + sx * 70, hy - 90, 30, 32, pal["dark"], ow=OW)
    elif cid == "willowby":
        capsule(d, (hx - 56, hy - 96), (hx - 76, hy - 244), 38, pal["body"], ow=OW)
        oval(d, hx - 72, hy - 226, 15, 46, "#D8B48F", ow=0, outline="#D8B48F")
        capsule(d, (hx + 56, hy - 100), (hx + 178, hy - 138), 38,
                pal["body"], ow=OW)
        oval(d, hx + 150, hy - 136, 46, 15, "#D8B48F", ow=0, outline="#D8B48F")
    elif cid == "fern":
        for sx in (-1, 1):
            oval(d, hx + sx * 72, hy - 88, 28, 32, pal["body"], ow=OW)
            oval(d, hx + sx * 72, hy - 88, 14, 18, "#F6E4CC", ow=0,
                 outline="#F6E4CC")
    elif cid == "pipkin":
        for sx in (-1, 1):
            circle(d, hx + sx * 80, hy - 104, 54, pal["body"], ow=OW)
            circle(d, hx + sx * 80, hy - 104, 34, P.PIPkin["ear_inner"], ow=0,
                   outline=P.PIPkin["ear_inner"])


def _face_mark(d, cid, pal, hx, hy) -> None:
    """Markings drawn over head, under face features. Interior patches
    are colour-on-color with NO outline (silhouette-only line work)."""
    if cid == "juni":
        oval(d, hx, hy + 66, 84, 40, pal["belly"], ow=0)              # big muzzle
    elif cid == "bramble":
        oval(d, hx, hy + 18, 62, 92, P.WHITE, ow=0)                   # white face
        for sx in (-1, 1):                                            # stripes
            capsule(d, (hx + sx * 78, hy - 58), (hx + sx * 96, hy + 56),
                    30, pal["dark"], ow=0)
    elif cid == "marlow":
        oval(d, hx, hy + 64, 62, 42, pal["belly"], ow=0)
    elif cid == "willowby":
        oval(d, hx, hy + 66, 56, 38, P.WHITE, ow=0)
    elif cid == "fern":
        oval(d, hx, hy + 64, 52, 38, pal["belly"], ow=0)
    elif cid == "pipkin":
        oval(d, hx, hy + 62, 46, 34, pal["belly"], ow=0)
    # wren: beak lives in _face (it animates for talk states)


def _body_mark(d, cid, pal, body_cy, body_rx) -> None:
    if cid == "bramble":
        rrect(d, (300 - body_rx + 6, body_cy + 44, 300 + body_rx - 6,
                  body_cy + 78), P.BRAMBLE["belt"], radius=12, ow=4)
        rrect(d, (282, body_cy + 48, 318, body_cy + 76), "#E0B84E",
              radius=6, ow=3)
    elif cid == "wren":
        rrect(d, (206, body_cy - 56, 394, body_cy - 24), P.WREN["scarf"],
              radius=14, ow=4)
        poly(d, [(358, body_cy - 36), (394, body_cy - 30), (372, body_cy + 44)],
             P.WREN["scarf"], ow=4)
    elif cid == "willowby":
        poly(d, [(222, body_cy - 74), (266, body_cy + 64), (234, body_cy + 72),
                 (204, body_cy - 56)], P.WILLOWBY["vest"], ow=4)
        poly(d, [(378, body_cy - 74), (334, body_cy + 64), (366, body_cy + 72),
                 (396, body_cy - 56)], P.WILLOWBY["vest"], ow=4)
        for by in (body_cy - 28, body_cy + 10):
            circle(d, 300, by, 7, "#E8C86A", ow=3)
    elif cid == "fern":
        for sx, sy, r in ((-52, -30, 15), (48, -14, 13), (-30, 46, 12),
                          (42, 56, 14)):
            oval(d, 300 + sx, body_cy + sy, r, r - 3, P.FERN["spot"], ow=0,
                 outline=P.FERN["spot"])


def _prop_hand(d, cid, pose, ex, ey) -> None:
    if cid == "bramble" and pose is POSES.get("point"):
        capsule(d, (ex, ey), (ex + 38, ey - 8), 13, P.BRAMBLE["tool"], ow=4)


def _carry_prop(d, cid, hx: float, hy: float) -> None:
    """Object resting ON the raised right mitten (not floating centered)."""
    if cid == "juni":
        oval(d, hx, hy - 26, 34, 26, "#C87F3A", ow=5)                # acorn
        d.chord([hx - 28, hy - 58, hx + 28, hy - 32], 180, 360,
                fill=P.INK)
        d.chord([hx - 24, hy - 54, hx + 24, hy - 36], 180, 360,
                fill=P.JUNI["cap_vein"])
    elif cid == "marlow":
        circle(d, hx, hy - 24, 18, P.MARLOW["pebble"], ow=4)         # blue pebble


# ---------------------------------------------------------------- face --------

def _face(d, hx, hy, expression, pose, cid, blink) -> None:
    fp = dict(FACES[expression])
    if pose.mouth:
        fp["mouth"] = pose.mouth
    if pose.eyes:
        fp["eyes"] = pose.eyes
    if pose.brows:
        fp["brows"] = pose.brows
    eyes = "closed" if blink else fp.get("eyes", "open")
    mouth = fp.get("mouth", "small")
    brows = fp.get("brows", "flat")

    eye_dx, eye_y = (46, hy - 6) if cid == "wren" else (48, hy + 4)

    for sx in (-1, 1):
        ex = hx + sx * eye_dx
        if eyes == "closed":
            d.arc([ex - 23, eye_y - 6, ex + 23, eye_y + 28], 20, 160,
                  fill=P.INK, width=9)
        elif eyes == "happy" or (eyes == "wink" and sx > 0):
            d.arc([ex - 24, eye_y - 24, ex + 24, eye_y + 26], 195, 345,
                  fill=P.INK, width=10)
        else:
            # big flat white + ONE solid pupil, no highlight (reference)
            rx, ry = (34, 40) if eyes == "wide" else (28, 32)
            oval(d, ex, eye_y, rx, ry, P.EYE_WHITE, ow=7)
            pr = 17 if eyes == "wide" else 17
            circle(d, ex + sx * 2, eye_y + 6, pr, P.IRIS, ow=0,
                   outline=P.IRIS)

        # brows — thin short arcs floating over the big eyes
        by = eye_y - (50 if eyes == "wide" else 46)
        bx0, bx1 = ex - 16, ex + 16
        if brows == "up":
            d.line([(bx0, by - 4), (bx1, by - 8)], fill=P.INK, width=5)
        elif brows == "sad":
            d.line([(bx0, by + 6), (bx1, by - 4)], fill=P.INK, width=5)
        elif brows == "down":
            d.line([(bx0, by - 5), (bx1, by + 4)], fill=P.INK, width=5)
        elif brows == "tilt":
            if sx < 0:
                d.line([(bx0, by - 6), (bx1, by)], fill=P.INK, width=5)
            else:
                d.line([(bx0, by + 3), (bx1, by - 4)], fill=P.INK, width=5)
        else:
            d.line([(bx0, by), (bx1, by)], fill=P.INK, width=5)

    if cid == "wren":
        _beak(d, hx, hy, mouth)
        return

    # mouth sits low on the big muzzle; no nose (reference has none)
    my = hy + 72 if cid == "juni" else hy + 84
    mcx = hx
    if mouth == "small":
        d.arc([mcx - 18, my - 8, mcx + 18, my + 12], 20, 160, fill=MOUTH_DARK, width=7)
    elif mouth == "smile":
        d.arc([mcx - 30, my - 14, mcx + 30, my + 18], 15, 165,
              fill=MOUTH_DARK, width=8)
    elif mouth == "frown":
        d.arc([mcx - 26, my + 2, mcx + 26, my + 28], 200, 340,
              fill=MOUTH_DARK, width=8)
    elif mouth == "flat":
        d.line([(mcx - 20, my + 6), (mcx + 20, my + 6)], fill=MOUTH_DARK, width=8)
    elif mouth == "open":
        oval(d, mcx, my + 6, 26, 20, MOUTH_DARK, ow=0)
        d.chord([mcx - 18, my + 6, mcx + 18, my + 26], 0, 180, fill=TONGUE)
    elif mouth == "mid":
        oval(d, mcx, my + 6, 15, 11, MOUTH_DARK, ow=0)
    elif mouth == "closed":
        d.line([(mcx - 15, my + 4), (mcx + 15, my + 4)], fill=MOUTH_DARK, width=7)
    elif mouth == "o":
        oval(d, mcx, my + 6, 15, 17, MOUTH_DARK, ow=0)

    # whiskers
    if cid == "pipkin":
        for sx in (-1, 1):
            for dy in (-6, 6):
                d.line([(hx + sx * 30, my - 8 + dy), (hx + sx * 80, my - 12 + dy * 2)],
                       fill=P.INK, width=4)
    if cid == "marlow":
        for sx in (-1, 1):
            for dy in (-4, 8):
                d.line([(hx + sx * 34, my - 12 + dy), (hx + sx * 86, my - 16 + dy * 2)],
                       fill=P.INK, width=4)


def _beak(d, hx, hy, mouth: str) -> None:
    """Wren's beak IS her mouth: closed wedge, open = dark gap + 2 halves."""
    top, apex = hy + 38, hy + 90
    if mouth in ("open", "o"):
        poly(d, [(hx - 34, top), (hx + 34, top), (hx, apex + 8)], "#5A2E2E", ow=0)
        poly(d, [(hx - 36, top), (hx + 36, top), (hx, top + 26)],
             P.WREN["beak"], ow=5)                                   # upper
        poly(d, [(hx - 30, apex - 16), (hx + 30, apex - 16), (hx, apex + 10)],
             P.WREN["beak"], ow=5)                                   # lower
    elif mouth == "mid":
        poly(d, [(hx - 32, top), (hx + 32, top), (hx, apex - 14)], "#5A2E2E", ow=0)
        poly(d, [(hx - 35, top), (hx + 35, top), (hx, top + 22)],
             P.WREN["beak"], ow=5)
    else:
        wedge(d, (hx, apex), (hx - 36, top), (hx + 36, top),
              P.WREN["beak"], ow=6)


def _accessories(d, cid, pal, hx, hy, head_rx, head_ry) -> None:
    if cid == "juni":  # leaf cap — full beanie covering the crown
        rx = head_rx * 0.97
        cap_bot = hy - 54                 # brim line, clear of the brows
        cap_top = hy - head_ry - 48       # overshoots the crown

        def _dome(inset: int, color: str) -> None:
            y0 = cap_top + inset
            y1 = 2 * (cap_bot - inset) - y0   # chord flat edge = centre
            d.chord([hx - rx + inset, y0, hx + rx - inset, y1],
                    180, 360, fill=color)

        _dome(0, P.INK)
        _dome(6, P.JUNI["cap"])
        rrect(d, (hx - rx, cap_bot - 24, hx + rx, cap_bot + 8),
              P.JUNI["cap"], radius=12, ow=OW)
        d.line([(hx, cap_top + 8), (hx + 2, cap_top - 28)],
               fill=P.INK, width=8)
        oval(d, hx + 8, cap_top - 36, 24, 12, P.JUNI["cap_vein"], ow=4)
    elif cid == "willowby":  # spectacles (rings only — eyes stay visible)
        for sx in (-1, 1):
            cx, cy = hx + sx * 48, hy + 4
            d.ellipse([cx - 38, cy - 38, cx + 38, cy + 38],
                      outline=P.WILLOWBY["metal"], width=7)
        d.line([(hx - 12, hy + 2), (hx + 12, hy + 2)],
               fill=P.WILLOWBY["metal"], width=7)
        for sx in (-1, 1):
            d.line([(hx + sx * 84, hy), (hx + sx * (head_rx + 4), hy - 10)],
                   fill=P.WILLOWBY["metal"], width=6)
    elif cid == "bramble":
        rrect(d, (hx - 88, hy - 114, hx + 88, hy - 88), P.BRAMBLE["belt"],
              radius=9, ow=4)
