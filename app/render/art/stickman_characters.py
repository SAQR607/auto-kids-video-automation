"""Stickman cast sprites: deterministic PIL line-art for the stickman profile.

Contract mirrors art/characters.py: get_sprite(char_id, state, expression,
frame) -> RGBA 600x760, GROUND=716, cached. Two forms:
  - "stik"  — the solo hero: classic stick figure with a red scarf
              (distinct silhouette via accessory, not color).
  - "dot"   — the small companion: round-bodied dot character with stub limbs.
Unknown ids fall back to the hero. Poses (13) and expression keys (14) are
kept identical to the Fernwood set so manifests/validation stay interchangeable.
"""

from __future__ import annotations

import math
from typing import Any

from PIL import Image, ImageDraw

from .shapes import capsule, circle, new_layer, oval

SIZE = (600, 760)
GROUND = 716

INK = "#1E1B18"
SKIN = "#FFFFFF"
SCARF = "#C4453D"

HERO = "stik"
SMALL_IDS = {"dot"}
SPECIES = (HERO, "dot")

# pose name -> joint plan. Arm angles in degrees from vertical (+ = outward).
POSES: dict[str, dict[str, Any]] = {
    "idle": {"arm_l": 16, "arm_r": -16, "legs": "stand", "bob": 0},
    "walk": {"arm_l": 26, "arm_r": -26, "legs": "walk", "bob": 3},
    "run": {"arm_l": 52, "arm_r": -52, "legs": "run", "bob": 7},
    "sit": {"arm_l": 34, "arm_r": -34, "legs": "sit", "bob": 0},
    "talk_closed": {"arm_l": 30, "arm_r": -30, "mouth": "closed"},
    "talk_mid": {"arm_l": 36, "arm_r": -36, "mouth": "mid"},
    "talk_open": {"arm_l": 42, "arm_r": -42, "mouth": "open"},
    "happy": {"arm_l": 70, "arm_r": -70, "bob": -6, "mouth": "smile", "eyes": "happy"},
    "sad": {"arm_l": 8, "arm_r": -8, "bob": 5, "mouth": "frown", "brows": "sad"},
    "surprised": {"arm_l": 60, "arm_r": -60, "bob": -4, "mouth": "o", "eyes": "wide"},
    "sleep": {"arm_l": 12, "arm_r": -12, "bob": 4, "mouth": "closed", "eyes": "closed"},
    "point": {"arm_l": 82, "arm_r": -10, "mouth": "smile"},
    "carry": {"arm_l": 55, "arm_r": -55, "hands_up": True, "mouth": "smile"},
}

# expression key -> face params (same keys as Fernwood FACES)
FACES: dict[str, dict[str, str]] = {
    "neutral": {},
    "happy": {"eyes": "happy", "mouth": "smile"},
    "sad": {"mouth": "frown", "brows": "sad"},
    "surprised": {"eyes": "wide", "mouth": "o"},
    "curious": {"brows": "tilt", "mouth": "smile"},
    "excited": {"eyes": "happy", "mouth": "open"},
    "determined": {"brows": "down", "mouth": "flat"},
    "sleepy": {"eyes": "closed", "mouth": "small"},
    "proud": {"brows": "up", "eyes": "happy", "mouth": "smile"},
    "confident": {"brows": "tilt", "mouth": "smile"},
    "worried": {"brows": "sad", "mouth": "small"},
    "silly": {"eyes": "wink", "mouth": "open"},
    "amazed": {"eyes": "wide", "mouth": "o"},
    "brave": {"brows": "down", "mouth": "smile"},
}

_CACHE: dict[tuple[str, str, str, int], Image.Image] = {}


def get_sprite(char_id: str, state: str, expression: str, frame: int = 0) -> Image.Image:
    """Public API — cached, never raises on unknown ids (falls back)."""
    if char_id not in SPECIES:
        char_id = HERO
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


# ------------------------------------------------------------------ hero ----

def _hero(state: str, expression: str, frame: int) -> Image.Image:
    pose = POSES[state]
    face = dict(FACES[expression])
    for k in ("mouth", "eyes", "brows"):
        if pose.get(k):
            face[k] = str(pose[k])

    img, d = new_layer(SIZE)
    bob = int(pose.get("bob", 0))
    sitting = str(pose.get("legs", "stand")) == "sit"

    # skeleton anchors (hero)
    hx, hy, hr = 300, 128 + bob, 62            # head
    neck = (300, hy + hr)                       # 190+bob
    shoulder = (300, neck[1] + 24)              # 214+bob
    hip = (300, 560 + bob) if sitting else (300, 430 + bob)

    if sitting:
        # thighs forward, shins down — readable seated silhouette
        for kx in (232, 368):
            capsule(d, hip, (kx, 650), 16, SKIN)
            capsule(d, (kx, 650), (kx, GROUND), 16, SKIN)
    else:
        ll, lr = _legs(hip, str(pose.get("legs", "stand")), frame, bob)
        capsule(d, hip, ll, 16, SKIN)
        capsule(d, hip, lr, 16, SKIN)

    # torso (back to front)
    capsule(d, neck, hip, 24, SKIN)

    # arms
    hands_up = bool(pose.get("hands_up"))
    if hands_up:
        hand_l = (shoulder[0] - 74, shoulder[1] - 92 + bob)
        hand_r = (shoulder[0] + 74, shoulder[1] - 92 + bob)
    else:
        hand_l = _arm(shoulder, float(pose["arm_l"]), 150)
        hand_r = _arm(shoulder, float(pose["arm_r"]), 150)
    capsule(d, shoulder, hand_l, 16, SKIN)
    capsule(d, shoulder, hand_r, 16, SKIN)

    # scarf (silhouette accessory) — drawn over the neck
    capsule(d, (hx - 46, hy + hr + 6), (hx + 46, hy + hr + 6), 22, SCARF)
    tail_dx = {"walk": 26, "run": 44}.get(state, 14)
    capsule(d, (hx - 40, hy + hr + 10), (hx - 40 - tail_dx, hy + hr + 44), 14, SCARF)

    # head (over neck)
    circle(d, hx, hy, hr, SKIN)
    _face(d, hx, hy, hr, face)
    return img


def _arm(shoulder: tuple[int, int], deg: float, length: float) -> tuple[float, float]:
    rad = math.radians(deg)
    return shoulder[0] + math.sin(rad) * length, shoulder[1] + math.cos(abs(rad)) * length * 0.72 + 20


def _legs(hip: tuple[int, int], style: str, frame: int, bob: int) -> tuple[tuple, tuple]:
    x, y = hip
    if style == "stand":
        return (x - 34, GROUND), (x + 34, GROUND)
    if style == "walk":
        strides = ((-42, 30), (-16, 16), (30, -42), (16, -16))
        dl, dr = strides[frame]
        return (x + dl, GROUND), (x + dr, GROUND)
    if style == "run":
        strides = ((-70, 54), (-34, 30), (54, -70), (30, -34))
        dl, dr = strides[frame]
        # back leg pushes off (knee up implied by shorter y), front leg reaches
        return (x + dl, GROUND), (x + dr, GROUND - 26)
    if style == "sit":
        # hip drops, knees forward: approximate with bent-leg stubs to a seat
        return (x - 60, GROUND - 96), (x + 40, GROUND)
    return (x - 34, GROUND), (x + 34, GROUND)


def _face(d: ImageDraw.ImageDraw, hx: int, hy: int, hr: int, face: dict[str, str]) -> None:
    ex, ey = hx, hy - 6
    eye_dx = hr * 0.38
    eyes = face.get("eyes", "")
    brows = face.get("brows", "")
    mouth = face.get("mouth", "")

    # eyes
    if eyes == "closed":
        d.line([(ex - eye_dx - 14, ey), (ex - eye_dx + 14, ey)], fill=INK, width=7)
        d.line([(ex + eye_dx - 14, ey), (ex + eye_dx + 14, ey)], fill=INK, width=7)
    elif eyes == "happy":
        for sx in (-eye_dx, eye_dx):
            d.arc([ex + sx - 15, ey - 14, ex + sx + 15, ey + 12], 190, 350, fill=INK, width=7)
    elif eyes == "wide":
        for sx in (-eye_dx, eye_dx):
            circle(d, ex + sx, ey, 15, SKIN, ow=6, outline=INK)
            circle(d, ex + sx, ey, 6, INK, ow=0, outline=INK)
    elif eyes == "wink":
        d.line([(ex - eye_dx - 13, ey), (ex - eye_dx + 13, ey)], fill=INK, width=7)
        circle(d, ex + eye_dx, ey, 8, INK, ow=0, outline=INK)
    else:
        for sx in (-eye_dx, eye_dx):
            circle(d, ex + sx, ey, 8, INK, ow=0, outline=INK)

    # brows
    bw = 26
    if brows == "up":
        d.line([(ex - eye_dx - bw, ey - 34), (ex - eye_dx + bw, ey - 40)], fill=INK, width=6)
        d.line([(ex + eye_dx - bw, ey - 40), (ex + eye_dx + bw, ey - 34)], fill=INK, width=6)
    elif brows == "sad":
        d.line([(ex - eye_dx - bw, ey - 40), (ex - eye_dx + bw, ey - 32)], fill=INK, width=6)
        d.line([(ex + eye_dx - bw, ey - 32), (ex + eye_dx + bw, ey - 40)], fill=INK, width=6)
    elif brows == "down":
        d.line([(ex - eye_dx - bw, ey - 32), (ex - eye_dx + bw, ey - 42)], fill=INK, width=6)
        d.line([(ex + eye_dx - bw, ey - 42), (ex + eye_dx + bw, ey - 32)], fill=INK, width=6)
    elif brows == "tilt":
        d.line([(ex - eye_dx - bw, ey - 38), (ex - eye_dx + bw, ey - 44)], fill=INK, width=6)
        d.line([(ex + eye_dx - bw, ey - 36), (ex + eye_dx + bw, ey - 30)], fill=INK, width=6)

    # mouth
    my = hy + hr * 0.45
    if mouth == "smile":
        d.arc([ex - 30, my - 18, ex + 30, my + 18], 15, 165, fill=INK, width=7)
    elif mouth == "frown":
        d.arc([ex - 26, my - 4, ex + 26, my + 32], 195, 345, fill=INK, width=7)
    elif mouth == "o":
        oval(d, ex, my + 4, 15, 19, SKIN, ow=6, outline=INK)
    elif mouth == "open":
        d.chord([ex - 26, my - 14, ex + 26, my + 24], 0, 180, fill=INK)
    elif mouth == "flat":
        d.line([(ex - 24, my + 4), (ex + 24, my + 4)], fill=INK, width=7)
    elif mouth == "small":
        d.line([(ex - 12, my + 6), (ex + 12, my + 6)], fill=INK, width=6)
    elif mouth == "closed":
        d.line([(ex - 18, my + 4), (ex + 18, my + 4)], fill=INK, width=6)
    elif mouth == "mid":
        d.line([(ex - 16, my + 4), (ex + 16, my + 4)], fill=INK, width=7)
    else:  # neutral: faint line
        d.line([(ex - 16, my + 4), (ex + 16, my + 4)], fill=INK, width=5)


# -------------------------------------------------------------- companion ----

def _dot(state: str, expression: str, frame: int) -> Image.Image:
    pose = POSES[state]
    face = dict(FACES[expression])
    for k in ("mouth", "eyes", "brows"):
        if pose.get(k):
            face[k] = str(pose[k])

    img, d = new_layer(SIZE)
    bob = int(pose.get("bob", 0))
    cx, cy, r = 300, GROUND - 96 + bob, 92        # round body sits on the ground

    # stub limbs
    style = str(pose.get("legs", "stand"))
    if style == "walk":
        dl, dr = ((-34, 22), (-12, 12), (22, -34), (12, -12))[frame]
    elif style == "run":
        dl, dr = ((-52, 40), (-26, 22), (40, -52), (22, -26))[frame]
    else:
        dl, dr = -26, 26
    if style == "sit":
        capsule(d, (cx - 20, cy + r - 10), (cx - 78, GROUND), 12, SKIN)
        capsule(d, (cx + 20, cy + r - 10), (cx + 60, GROUND), 12, SKIN)
    else:
        capsule(d, (cx - 24, cy + r - 8), (cx + dl, GROUND), 12, SKIN)
        capsule(d, (cx + 24, cy + r - 8), (cx + dr, GROUND), 12, SKIN)

    # arms
    if pose.get("hands_up"):
        capsule(d, (cx - r + 8, cy - 20), (cx - r - 26, cy - 86), 11, SKIN)
        capsule(d, (cx + r - 8, cy - 20), (cx + r + 26, cy - 86), 11, SKIN)
    else:
        arm_l = float(pose["arm_l"])
        arm_r = float(pose["arm_r"])
        capsule(d, (cx - r + 6, cy - 6), (cx - r - 10 - arm_l, cy + 44), 11, SKIN)
        capsule(d, (cx + r - 6, cy - 6), (cx + r + 10 + abs(arm_r), cy + 44), 11, SKIN)

    # body circle
    circle(d, cx, cy, r, SKIN)
    _face(d, cx, cy - 8, r, face)
    return img


def _build(char_id: str, state: str, expression: str, frame: int) -> Image.Image:
    if char_id in SMALL_IDS:
        return _dot(state, expression, frame)
    return _hero(state, expression, frame)
