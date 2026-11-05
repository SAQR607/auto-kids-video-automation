"""Character sprites: deterministic PIL drawing for 7 cast members.

CalArts style (decided 2026-11-05): big heads on bean bodies, oversized
glossy double-highlight eyes, thick rounded outlines (OW=8 silhouette /
OD=5 detail), rosy blush, and cel shading blended through separate
layers (PIL Draw replaces pixels — it cannot alpha-blend).

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

from PIL import Image, ImageChops, ImageDraw

from . import palette as P
from .backend import stickman
from .shapes import (AA, ScaledDraw, aa_layer, capsule, circle, flatten,
                     oval, poly, rrect, wedge)

SIZE = (600, 760)
GROUND = 716
OW = 8    # CalArts chunky silhouette outline
OD = 5    # interior detail outline

# breathing sub-pose: body+head rise/fall, feet stay planted
BREATH = (0, 2, 3, 2)
# walk/run vertical bounce and arm swing per cycle frame (pass frames lift)
_WALK = dict(bob=(0, -4, 0, -4), swing=(16, 0, -16, 0), tail=(1.0, 0.2, -1.0, 0.2))
_RUN = dict(bob=(0, -6, 0, -6), swing=(30, 0, -30, 0), tail=(1.0, 0.2, -1.0, 0.2))

# per-species CalArts proportions (body rx, ry) / (head rx, ry)
_BODY = {"juni": (98, 122), "bramble": (110, 116), "marlow": (94, 124),
         "wren": (92, 112), "willowby": (96, 126), "fern": (90, 120),
         "pipkin": (86, 106)}
_HEAD = {"juni": (122, 110), "bramble": (126, 114), "marlow": (118, 108),
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
_NO_BLUSH = ("sad", "worried", "sleepy")


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
        img = _build(char_id, state, expression, frame, blink=blink, phase=phase)
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


def _shade(img: Image.Image, fn, color: tuple[int, int, int], alpha: int,
           s: int) -> None:
    """Blend `color`@alpha over the region painted by fn, clipped to the
    current silhouette (separate-layer paste — PIL Draw can't blend)."""
    reg = Image.new("L", img.size, 0)
    fn(ScaledDraw(ImageDraw.Draw(reg), s))
    mask = ImageChops.multiply(
        reg, img.getchannel("A").point(lambda v: v * alpha // 255))
    img.paste(Image.new("RGBA", img.size, color), (0, 0), mask)


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
        oval(d, 250, 668, 78, 46, pal["body"], ow=OW)
        oval(d, 350, 668, 78, 46, pal["body"], ow=OW)
        circle(d, 222, 692, 30, P.INK if char_id == "bramble" else pal["dark"], ow=OW)
        circle(d, 378, 692, 30, P.INK if char_id == "bramble" else pal["dark"], ow=OW)
    else:
        for hip, dx, sign in ((hip_l, dx_l, -1), (hip_r, dx_r, 1)):
            knee = (hip[0] + dx * 0.6 + sign * 6, 678)
            foot = (hip[0] + dx + sign * 4, GROUND - 6)
            capsule(d, hip, knee, 36, pal["body"], ow=OW)
            capsule(d, knee, foot, 32, pal["body"], ow=OW)
            oval(d, foot[0] + sign * 8, foot[1] + 8, 30, 15, pal["dark"], ow=OW)

    oval(d, 300, body_cy, body_rx, body_ry, pal["body"], ow=OW)
    oval(d, 300, body_cy + 24, body_rx * 0.66, body_ry * 0.76,
         pal["belly"], ow=OD)

    for sh_x, ang, sign in ((sh_l, arm_l, -1), (sh_r, arm_r, 1)):
        ex, ey = _hand(sh_x, sh_y, ang, sign, pose.hands_up)
        capsule(d, (sh_x, sh_y), (ex, ey), 34, pal["body"], ow=OW)
        circle(d, ex, ey, 24, pal["body"], ow=OW)
        if pose is POSES.get("point") and sign < 0:
            _prop_hand(d, char_id, pose, ex, ey)

    _ears_behind(d, char_id, pal, hx, hy)
    oval(d, hx, hy, head_rx, head_ry, pal["body"], ow=OW)

    # ----- cel shading (before face so features stay crisp)
    _shade(img, lambda sd: sd.ellipse([340, 470, 760, 980], fill=255),
           P.SHADOW[:3], 46, AA)                                  # rim shadow
    _shade(img, lambda sd: sd.ellipse([214, 430, 386, 492], fill=255),
           P.SHADOW[:3], 34, AA)                                  # under-chin
    _shade(img, lambda sd: sd.ellipse([186, 196, 336, 306], fill=255),
           (255, 255, 255), 30, AA)                               # top light

    # ----- markings + face + accessories
    _body_mark(d, char_id, pal, body_cy, body_rx)
    _face_mark(d, char_id, pal, hx, hy)
    _face(d, hx, hy, expression, pose, char_id, blink)
    _accessories(d, char_id, pal, hx, hy, head_rx)
    if pose is POSES.get("carry"):
        _carry_prop(d, char_id, sh_y)
    return flatten(img, SIZE)


def _pal(char_id: str) -> dict[str, str]:
    return {
        "juni": P.JUNI, "bramble": P.BRAMBLE, "marlow": P.MARLOW, "wren": P.WREN,
        "willowby": P.WILLOWBY, "fern": P.FERN, "pipkin": P.PIPkin,
    }[char_id]


# ---------------------------------------------------------------- per-species ---

def _tail(d, cid: str, pal: dict, swing: float) -> None:
    if cid == "juni":
        pts = [(368, 604), (442, 566), (476, 470), (456, 372), (400, 316)]
        for i, (x, y) in enumerate(pts):
            x += swing * 32
            r = (44, 58, 66, 60, 48)[i]
            col = pal["dark"] if i == 4 else pal["body"]
            oval(d, x + i * 4, y, r, r, col, ow=6)
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
    if cid in ("juni", "marlow"):
        for sx in (-1, 1):
            oval(d, hx + sx * 76, hy - 96, 34, 38, pal["body"], ow=OW)
            oval(d, hx + sx * 76, hy - 96, 18, 22, "#E8B4A6", ow=0,
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
    """Markings drawn over head, under face features."""
    if cid == "juni":
        oval(d, hx, hy + 62, 60, 44, pal["belly"], ow=OD)
    elif cid == "bramble":
        oval(d, hx, hy + 18, 62, 92, P.WHITE, ow=OD)                 # white face
        for sx in (-1, 1):                                            # stripes
            capsule(d, (hx + sx * 78, hy - 58), (hx + sx * 96, hy + 56),
                    30, pal["dark"], ow=4)
    elif cid == "marlow":
        oval(d, hx, hy + 64, 62, 42, pal["belly"], ow=OD)
    elif cid == "willowby":
        oval(d, hx, hy + 66, 56, 38, P.WHITE, ow=OD)
    elif cid == "fern":
        oval(d, hx, hy + 64, 52, 38, pal["belly"], ow=OD)
    elif cid == "pipkin":
        oval(d, hx, hy + 62, 46, 34, pal["belly"], ow=OD)
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


def _carry_prop(d, cid, sh_y) -> None:
    """Object held between both raised hands (drawn once, centered)."""
    if cid == "juni":
        oval(d, 300, sh_y - 96, 36, 28, "#C87F3A", ow=5)              # acorn
        oval(d, 300, sh_y - 122, 24, 12, P.JUNI["cap_vein"], ow=4)
    elif cid == "marlow":
        circle(d, 300, sh_y - 94, 18, P.MARLOW["pebble"], ow=4)        # blue pebble


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
            d.arc([ex - 21, eye_y - 6, ex + 21, eye_y + 26], 20, 160,
                  fill=P.INK, width=9)
        elif eyes == "happy" or (eyes == "wink" and sx > 0):
            d.arc([ex - 22, eye_y - 22, ex + 22, eye_y + 24], 195, 345,
                  fill=P.INK, width=10)
        else:
            rx, ry = (33, 38) if eyes == "wide" else (27, 31)
            oval(d, ex, eye_y, rx, ry, P.EYE_WHITE, ow=6)
            pr = 17 if eyes == "wide" else 15
            circle(d, ex + sx * 2, eye_y + 5, pr, P.IRIS, ow=0, outline=P.IRIS)
            circle(d, ex + sx * 2 - 6, eye_y - 3, 7, P.HIGHLIGHT, ow=0,
                   outline=P.HIGHLIGHT)
            circle(d, ex + sx * 2 + 7, eye_y + 13, 3.5, P.HIGHLIGHT, ow=0,
                   outline=P.HIGHLIGHT)

        # brows — thick CalArts dashes floating over big eyes
        by = eye_y - (48 if eyes == "wide" else 44)
        bx0, bx1 = ex - 20, ex + 20
        if brows == "up":
            d.line([(bx0, by - 6), (bx1, by - 11)], fill=P.INK, width=8)
        elif brows == "sad":
            d.line([(bx0, by + 7), (bx1, by - 5)], fill=P.INK, width=8)
        elif brows == "down":
            d.line([(bx0, by - 6), (bx1, by + 5)], fill=P.INK, width=8)
        elif brows == "tilt":
            if sx < 0:
                d.line([(bx0, by - 7), (bx1, by)], fill=P.INK, width=8)
            else:
                d.line([(bx0, by + 3), (bx1, by - 5)], fill=P.INK, width=8)
        else:
            d.line([(bx0, by), (bx1, by)], fill=P.INK, width=8)

    # rosy cheeks (skip the down expressions)
    if expression not in _NO_BLUSH:
        for sx in (-1, 1):
            oval(d, hx + sx * 86, hy + 52, 22, 13, P.BLUSH, ow=0,
                 outline=P.BLUSH)

    if cid == "wren":
        _beak(d, hx, hy, mouth)
        return

    # noses on muzzles (above the mouth)
    if cid == "juni":
        oval(d, hx, hy + 46, 11, 8, P.JUNI["dark"], ow=0, outline=P.JUNI["dark"])
    elif cid == "marlow":
        circle(d, hx, hy + 44, 13, "#2B1A10", ow=0, outline="#2B1A10")
    elif cid == "willowby":
        oval(d, hx, hy + 50, 10, 7, P.WILLOWBY["dark"], ow=0,
             outline=P.WILLOWBY["dark"])
    elif cid == "fern":
        oval(d, hx, hy + 48, 10, 7, P.FERN["dark"], ow=0, outline=P.FERN["dark"])
    elif cid == "pipkin":
        oval(d, hx, hy + 44, 9, 6, P.PIPkin["ear_inner"], ow=0,
             outline=P.PIPkin["ear_inner"])

    my = hy + 84
    mcx = hx
    if mouth == "small":
        d.arc([mcx - 18, my - 8, mcx + 18, my + 12], 20, 160, fill=P.INK, width=7)
    elif mouth == "smile":
        d.arc([mcx - 26, my - 12, mcx + 26, my + 16], 15, 165, fill=P.INK, width=8)
    elif mouth == "frown":
        d.arc([mcx - 24, my + 2, mcx + 24, my + 26], 200, 340, fill=P.INK, width=8)
    elif mouth == "flat":
        d.line([(mcx - 18, my + 6), (mcx + 18, my + 6)], fill=P.INK, width=8)
    elif mouth == "open":
        oval(d, mcx, my + 4, 22, 16, "#5A2E2E", ow=5)
        d.chord([mcx - 15, my + 4, mcx + 15, my + 20], 0, 180, fill="#E88C8C")
    elif mouth == "mid":
        oval(d, mcx, my + 4, 14, 10, "#5A2E2E", ow=4)
    elif mouth == "closed":
        d.line([(mcx - 14, my + 4), (mcx + 14, my + 4)], fill=P.INK, width=7)
    elif mouth == "o":
        circle(d, mcx, my + 4, 14, "#5A2E2E", ow=4)

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


def _accessories(d, cid, pal, hx, hy, head_rx) -> None:
    if cid == "juni":  # leaf cap
        d.chord([hx - 100, hy - 160, hx + 100, hy - 30], 180, 360,
                fill=P.INK, width=0)
        d.chord([hx - 95, hy - 155, hx + 95, hy - 35], 180, 360,
                fill=P.JUNI["cap"])
        d.line([(hx, hy - 150), (hx, hy - 184)], fill=P.INK, width=8)
        oval(d, hx + 6, hy - 190, 22, 11, P.JUNI["cap_vein"], ow=4)
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
