"""Character sprites: deterministic PIL drawing for 7 cast members.

`get_sprite(char_id, state, expression, frame)` -> RGBA 600x760, cached.
States: idle walk run sit talk_closed talk_mid talk_open happy sad surprised
        sleep point carry   (13, binding). Expressions: manifest list (14).
Walk/run use 4-frame cycles (frame 0-3).
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageDraw

from . import palette as P
from .shapes import capsule, circle, new_layer, oval, poly, rrect, wedge

SIZE = (600, 760)
GROUND = 716


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
    "walk": Pose(arm_l=28, arm_r=-28, legs="walk", bob=2, tail=0.15),
    "run": Pose(arm_l=50, arm_r=-50, legs="run", bob=5, tail=0.35),
    "sit": Pose(arm_l=34, arm_r=-34, legs="sit", tail=0.1),
    "talk_closed": Pose(arm_l=30, arm_r=-30, mouth="closed"),
    "talk_mid": Pose(arm_l=34, arm_r=-34, mouth="mid"),
    "talk_open": Pose(arm_l=40, arm_r=-40, mouth="open"),
    "happy": Pose(arm_l=65, arm_r=-65, bob=-5, tail=0.3, mouth="smile", eyes="happy", brows="up"),
    "sad": Pose(arm_l=8, arm_r=-8, bob=4, tail=-0.3, mouth="frown", brows="sad"),
    "surprised": Pose(arm_l=58, arm_r=-58, bob=-3, tail=0.5, mouth="o", eyes="wide", brows="up"),
    "sleep": Pose(arm_l=14, arm_r=-14, bob=3, mouth="closed", eyes="closed"),
    "point": Pose(arm_l=78, arm_r=-12, tail=0.1, mouth="smile"),
    "carry": Pose(arm_l=52, arm_r=-52, hands_up=True, mouth="smile"),
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

_CACHE: dict[tuple[str, str, str, int], Image.Image] = {}


def get_sprite(char_id: str, state: str, expression: str, frame: int = 0) -> Image.Image:
    """Public API — cached, never raises on unknown ids (falls back)."""
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
    key = (char_id, state, expression, frame)
    img = _CACHE.get(key)
    if img is None:
        img = _build(char_id, state, expression, frame)
        _CACHE[key] = img
    return img


# ---------------------------------------------------------------- geometry --

def _walk_shift(state: str, frame: int) -> tuple[int, int]:
    """(left foot dx, right foot dx) per cycle frame."""
    if state == "walk":
        return ((0, 26), (16, 10), (26, 0), (10, -16))[frame][0], ((0, 26), (16, 10), (26, 0), (10, -16))[frame][1]
    if state == "run":
        return ((-30, 34), (-8, 20), (34, -30), (20, -8))[frame]
    return (0, 0)


def _build(char_id: str, state: str, expression: str, frame: int) -> Image.Image:
    pose = POSES[state]
    img, d = new_layer(SIZE)
    pal = _pal(char_id)

    dx_l, dx_r = _walk_shift(state, frame)
    hip_l, hip_r = (255, 636), (345, 636)
    foot_y = GROUND

    # ----- tail (behind everything)
    _tail(d, char_id, pal, pose)

    # ----- legs
    if pose.legs == "sit":
        oval(d, 250, 668, 78, 46, pal["body"])
        oval(d, 350, 668, 78, 46, pal["body"])
        circle(d, 222, 690, 30, P.INK if char_id == "bramble" else pal["dark"])
        circle(d, 378, 690, 30, P.INK if char_id == "bramble" else pal["dark"])
    else:
        for hx, dx, sign in ((hip_l, dx_l, -1), (hip_r, dx_r, 1)):
            knee = (hx[0] + dx * 0.6 + sign * 6, 678)
            foot = (hx[0] + dx + sign * 4, foot_y - 6)
            capsule(d, hx, knee, 34, pal["body"])
            capsule(d, knee, foot, 30, pal["body"])
            oval(d, foot[0] + sign * 8, foot[1] + 6, 26, 14, pal["dark"])

    # ----- body
    body_cy = 548 + pose.bob
    oval(d, 300, body_cy, 116, 132, pal["body"])
    oval(d, 300, body_cy + 22, 78, 96, pal["belly"])
    _body_mark(d, char_id, pal, body_cy)

    # ----- arms
    sh_y = body_cy - 46
    for sh_x, ang, sign in ((196, pose.arm_l, -1), (404, pose.arm_r, 1)):
        import math
        a = math.radians(ang)
        ln = 96
        hx = sh_x + math.sin(a) * ln * sign * (-1 if sign < 0 else -1)
        # angle measured: 0 = straight down; positive = swing away from body
        ex = sh_x + math.sin(math.radians(abs(ang))) * ln * sign
        ey = sh_y + math.cos(math.radians(abs(ang))) * ln
        if pose.hands_up:
            ex, ey = sh_x + sign * 46, sh_y - 66
        capsule(d, (sh_x, sh_y), (ex, ey), 30, pal["body"])
        circle(d, ex, ey, 22, pal["body"])
        _prop_hand(d, char_id, pose, ex, ey)

    # ----- head (ears behind)
    hx, hy, hr = 300, 330 + pose.bob, 116
    _ears_behind(d, char_id, pal, hx, hy, hr)
    _head_shape(d, char_id, pal, hx, hy, hr)
    _face_mark(d, char_id, pal, hx, hy, hr)   # stripes / muzzle / beak base
    _face(d, hx, hy, hr, expression, pose, char_id, pal)
    _accessories(d, char_id, pal, hx, hy, hr, body_cy, sh_y)
    return img


def _pal(char_id: str) -> dict[str, str]:
    return {
        "juni": P.JUNI, "bramble": P.BRAMBLE, "marlow": P.MARLOW, "wren": P.WREN,
        "willowby": P.WILLOWBY, "fern": P.FERN, "pipkin": P.PIPkin,
    }[char_id]


# ---------------------------------------------------------------- per-species ---

def _tail(d: ImageDraw.ImageDraw, cid: str, pal: dict, pose: Pose) -> None:
    swing = pose.tail
    if cid == "juni":
        pts = [(368, 600), (438, 560), (470, 470), (452, 380), (400, 330)]
        for i, (x, y) in enumerate(pts):
            x += swing * 30
            r = (40, 54, 62, 56, 44)[i]
            col = pal["dark"] if i == 4 else pal["body"]
            oval(d, x + i * 4, y, r, r, col)
    elif cid == "bramble":
        capsule(d, (372, 616), (468 + swing * 24, 560), 34, pal["body"])
        oval(d, 476 + swing * 24, 556, 24, 20, P.WHITE)
    elif cid == "marlow":
        capsule(d, (372, 618), (474 + swing * 26, 646), 40, pal["body"])
        oval(d, 486 + swing * 26, 650, 26, 22, pal["dark"])
    elif cid == "wren":
        poly(d, [(372, 600), (452 + swing * 26, 520), (464 + swing * 26, 548), (392, 636)], pal["dark"])
    elif cid == "willowby":
        circle(d, 380 + swing * 20, 624, 34, P.WHITE)
    elif cid == "fern":
        oval(d, 378 + swing * 18, 598, 26, 22, P.WHITE)
    elif cid == "pipkin":
        pts2 = [(372, 626), (426 + swing * 20, 648), (462 + swing * 26, 620), (470 + swing * 26, 584)]
        for i in range(len(pts2) - 1):
            capsule(d, pts2[i], pts2[i + 1], 10, pal["dark"], ow=3)


def _ears_behind(d, cid, pal, hx, hy, hr) -> None:
    if cid in ("juni", "marlow"):
        for sx in (-1, 1):
            ex = hx + sx * 74
            oval(d, ex, hy - 92, 30, 34, pal["body"])
            oval(d, ex, hy - 92, 16, 20, "#E8B4A6")
    elif cid == "bramble":
        for sx in (-1, 1):
            oval(d, hx + sx * 66, hy - 86, 28, 30, pal["dark"])
    elif cid == "willowby":
        capsule(d, (hx - 56, hy - 92), (hx - 74, hy - 226), 34, pal["body"])
        oval(d, hx - 70, hy - 210, 14, 44, "#D8B48F")
        capsule(d, (hx + 56, hy - 96), (hx + 168, hy - 130), 34, pal["body"])
        oval(d, hx + 140, hy - 128, 44, 14, "#D8B48F")
    elif cid == "fern":
        for sx in (-1, 1):
            oval(d, hx + sx * 70, hy - 84, 26, 30, pal["body"])
            oval(d, hx + sx * 70, hy - 84, 13, 17, "#F6E4CC")
    elif cid == "pipkin":
        for sx in (-1, 1):
            circle(d, hx + sx * 76, hy - 96, 48, pal["body"])
            circle(d, hx + sx * 76, hy - 96, 30, P.PIPkin["ear_inner"])


def _head_shape(d, cid, pal, hx, hy, hr) -> None:
    if cid == "wren":
        oval(d, hx, hy, hr - 6, hr - 14, pal["body"])
    else:
        oval(d, hx, hy, hr, hr - 6, pal["body"])


def _face_mark(d, cid, pal, hx, hy, hr) -> None:
    """Markings drawn over head, under face features."""
    if cid == "juni":
        oval(d, hx, hy + 44, 62, 48, pal["belly"])                     # muzzle
    elif cid == "bramble":
        oval(d, hx, hy + 16, 58, 88, P.WHITE)                           # white face base
        for sx in (-1, 1):                                              # badger stripes
            capsule(d, (hx + sx * 74, hy - 52), (hx + sx * 92, hy + 46), 26, pal["dark"])
    elif cid == "marlow":
        oval(d, hx, hy + 46, 66, 44, pal["belly"])
        circle(d, hx, hy + 30, 15, "#2B1A10")
    elif cid == "wren":
        wedge(d, (hx, hy + 74), (hx - 34, hy + 26), (hx + 34, hy + 26), P.WREN["beak"])  # beak down
    elif cid == "willowby":
        oval(d, hx, hy + 52, 54, 40, P.WHITE)
    elif cid == "fern":
        oval(d, hx, hy + 48, 54, 42, pal["belly"])
    elif cid == "pipkin":
        oval(d, hx, hy + 46, 48, 36, pal["belly"])


def _body_mark(d, cid, pal, body_cy) -> None:
    if cid == "bramble":
        rrect(d, (196, body_cy + 44, 404, body_cy + 76), P.BRAMBLE["belt"], radius=10, ow=4)
        rrect(d, (282, body_cy + 46, 318, body_cy + 74), "#E0B84E", radius=6, ow=3)
    elif cid == "wren":
        rrect(d, (208, body_cy - 54, 392, body_cy - 26), P.WREN["scarf"], radius=12, ow=4)
        poly(d, [(360, body_cy - 34), (392, body_cy - 30), (372, body_cy + 40)], P.WREN["scarf"], ow=4)
    elif cid == "willowby":
        poly(d, [(216, body_cy - 78), (268, body_cy + 66), (232, body_cy + 74), (198, body_cy - 60)], P.WILLOWBY["vest"], ow=4)
        poly(d, [(384, body_cy - 78), (332, body_cy + 66), (368, body_cy + 74), (402, body_cy - 60)], P.WILLOWBY["vest"], ow=4)
        for by in (body_cy - 30, body_cy + 8):
            circle(d, 300, by, 7, "#E8C86A", ow=3)
    elif cid == "fern":
        for sx, sy, r in ((-58, -30, 15), (54, -14, 13), (-34, 46, 12), (46, 56, 14)):
            oval(d, 300 + sx, body_cy + sy, r, r - 3, P.FERN["spot"])
    elif cid == "marlow":
        pass


def _prop_hand(d, cid, pose, ex, ey) -> None:
    if cid == "juni" and pose is POSES.get("carry"):
        oval(d, ex, ey - 30, 34, 26, "#C87F3A")   # acorn-ish carried blob
    if cid == "bramble" and pose is POSES.get("point"):
        capsule(d, (ex, ey), (ex + 34, ey - 6), 12, P.BRAMBLE["tool"], ow=3)


# ---------------------------------------------------------------- face --------

def _face(d, hx, hy, hr, expression, pose, cid, pal) -> None:
    fp = dict(FACES[expression])
    if pose.mouth:
        fp["mouth"] = pose.mouth
    if pose.eyes:
        fp["eyes"] = pose.eyes
    if pose.brows:
        fp["brows"] = pose.brows
    eyes = fp.get("eyes", "open")
    mouth = fp.get("mouth", "small")
    brows = fp.get("brows", "flat")

    eye_dx, eye_y = 46, hy + 6
    if cid == "wren":
        eye_dx, eye_y = 52, hy - 6

    for sx in (-1, 1):
        ex = hx + sx * eye_dx
        if eyes == "closed" or eyes == "happy" and False:
            capsule(d, (ex - 16, eye_y), (ex + 16, eye_y), 6, P.INK, ow=2)
        elif eyes == "happy":
            d.arc([ex - 17, eye_y - 15, ex + 17, eye_y + 17], 200, 340, fill=P.INK, width=7)
        elif eyes == "wink" and sx > 0:
            capsule(d, (ex - 16, eye_y), (ex + 16, eye_y), 6, P.INK, ow=2)
        else:
            rx, ry = (17, 21) if eyes != "wide" else (21, 26)
            oval(d, ex, eye_y, rx, ry, P.EYE_WHITE, ow=4)
            circle(d, ex + sx * 2, eye_y + 3, min(rx, ry) - 8, P.IRIS, ow=0, outline=P.IRIS)
            circle(d, ex + sx * 7, eye_y - 6, 5, P.HIGHLIGHT, ow=0, outline=P.HIGHLIGHT)

        # brows
        by = eye_y - (30 if eyes == "wide" else 34)
        bx0, bx1 = ex - 17, ex + 17
        if brows == "up":
            d.line([(bx0, by - 6), (bx1, by - 10)], fill=P.INK, width=6)
        elif brows == "sad":
            d.line([(bx0, by + 6), (bx1, by - 4)], fill=P.INK, width=6)
        elif brows == "down":
            d.line([(bx0, by - 6), (bx1, by + 4)], fill=P.INK, width=6)
        elif brows == "tilt":
            if sx < 0:
                d.line([(bx0, by - 6), (bx1, by)], fill=P.INK, width=6)
            else:
                d.line([(bx0, by + 2), (bx1, by - 4)], fill=P.INK, width=6)
        else:
            d.line([(bx0, by), (bx1, by)], fill=P.INK, width=6)

    # mouth (below muzzle/beak if present)
    my = hy + (66 if cid in ("juni", "marlow", "willowby", "fern", "pipkin") else 54)
    if cid == "wren":
        my = hy + 84
    mcx = hx
    if mouth == "small":
        d.arc([mcx - 20, my - 10, mcx + 20, my + 12], 20, 160, fill=P.INK, width=6)
    elif mouth == "smile":
        d.arc([mcx - 30, my - 14, mcx + 30, my + 18], 15, 165, fill=P.INK, width=7)
    elif mouth == "frown":
        d.arc([mcx - 26, my + 2, mcx + 26, my + 26], 200, 340, fill=P.INK, width=7)
    elif mouth == "flat":
        d.line([(mcx - 20, my + 6), (mcx + 20, my + 6)], fill=P.INK, width=7)
    elif mouth == "open":
        oval(d, mcx, my + 6, 24, 18, "#5A2E2E", ow=4)
        d.chord([mcx - 16, my + 4, mcx + 16, my + 22], 0, 180, fill="#E88C8C")
    elif mouth == "mid":
        oval(d, mcx, my + 6, 16, 11, "#5A2E2E", ow=4)
    elif mouth == "closed":
        d.line([(mcx - 16, my + 6), (mcx + 16, my + 6)], fill=P.INK, width=6)
    elif mouth == "o":
        circle(d, mcx, my + 6, 15, "#5A2E2E", ow=4)

    if cid == "pipkin":
        for sx in (-1, 1):
            for dy in (-6, 6):
                d.line([(hx + sx * 30, my - 6 + dy), (hx + sx * 78, my - 10 + dy * 2)],
                       fill=P.INK, width=3)
    if cid == "marlow":
        for sx in (-1, 1):
            for dy in (-4, 8):
                d.line([(hx + sx * 34, my - 10 + dy), (hx + sx * 84, my - 14 + dy * 2)],
                       fill=P.INK, width=3)


def _accessories(d, cid, pal, hx, hy, hr, body_cy, sh_y) -> None:
    if cid == "juni":  # leaf cap
        d.chord([hx - 96, hy - 148, hx + 96, hy - 20], 180, 360, fill=P.INK, width=0)
        d.chord([hx - 92, hy - 144, hx + 92, hy - 24], 180, 360, fill=P.JUNI["cap"])
        d.line([(hx, hy - 138), (hx, hy - 168)], fill=P.INK, width=7)
        oval(d, hx + 6, hy - 174, 20, 10, P.JUNI["cap_vein"])
    elif cid == "willowby":  # spectacles (rings only — eyes stay visible)
        for sx in (-1, 1):
            cx, cy = hx + sx * 46, hy + 6
            d.ellipse([cx - 34, cy - 34, cx + 34, cy + 34], outline=P.WILLOWBY["metal"], width=6)
        d.line([(hx - 14, hy + 4), (hx + 14, hy + 4)], fill=P.WILLOWBY["metal"], width=6)
        d.line([(hx - 78, hy + 2), (hx - 104, hy - 6)], fill=P.WILLOWBY["metal"], width=5)
        d.line([(hx + 78, hy + 2), (hx + 104, hy - 6)], fill=P.WILLOWBY["metal"], width=5)
    elif cid == "bramble":
        rrect(d, (hx - 84, hy - 118, hx + 84, hy - 96), P.BRAMBLE["belt"], radius=8, ow=4)
    # wren scarf drawn in body_mark; juni cap above
