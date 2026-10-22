"""Stickman profile props: era-neutral storybook-history objects.

Contract mirrors art/props.py: get_prop(pid) -> RGBA (cached); unknown ids
fall back to a neutral bundle. Sizes are pre-rendered at scene scale basis
(renderer resizes by height, preserving aspect).
"""

from __future__ import annotations

from PIL import Image, ImageDraw

from .shapes import capsule, circle, new_layer, oval, poly

INK = "#2A2622"
PROPS = ("scroll", "oil_lamp", "jug", "basket", "crate", "oar", "hammer", "ladder", "lantern", "signpost",
         "rope", "stone")

_SIZE = (320, 320)
_CACHE: dict[str, Image.Image] = {}


def get_prop(prop_id: str) -> Image.Image:
    if prop_id not in PROPS:
        prop_id = "crate"
    img = _CACHE.get(prop_id)
    if img is None:
        img = _BUILDERS[prop_id]()
        _CACHE[prop_id] = img
    return img


def _scroll() -> Image.Image:
    img, d = new_layer(_SIZE)
    d.rounded_rectangle([40, 110, 280, 210], radius=16, fill="#F2E6C8", outline=INK, width=6)
    for x in (60, 260):
        capsule(d, (x, 96), (x, 224), 30, "#9A7A52")
    d.line([(90, 150), (230, 150)], fill="#B49B6E", width=5)
    d.line([(90, 176), (210, 176)], fill="#B49B6E", width=5)
    return img


def _oil_lamp() -> Image.Image:
    img, d = new_layer(_SIZE)
    oval(d, 160, 230, 100, 44, "#C4A15E")
    d.polygon([(160, 90), (210, 190), (110, 190)], fill="#D9B45C")
    circle(d, 160, 74, 26, "#F4C86A", ow=5, outline=INK)
    circle(d, 160, 62, 12, "#FFF3C8", ow=0, outline="#FFF3C8")
    capsule(d, (244, 210), (280, 170), 16, "#C4A15E")
    return img


def _jug() -> Image.Image:
    img, d = new_layer(_SIZE)
    oval(d, 160, 210, 92, 100, "#B4795A")
    d.rectangle([136, 90, 184, 140], fill="#B4795A")
    d.ellipse([126, 74, 194, 112], fill="#96613F", outline=INK, width=5)
    capsule(d, (244, 170), (276, 224), 18, "#96613F")
    d.arc([120, 170, 200, 250], 20, 160, fill="#8E5640", width=6)
    return img


def _basket() -> Image.Image:
    img, d = new_layer(_SIZE)
    d.polygon([(60, 150), (260, 150), (234, 270), (86, 270)], fill="#C9A56A")
    d.arc([80, 60, 240, 240], 180, 360, fill=INK, width=8)
    for y in (180, 214, 248):
        d.line([(70 + (y - 150) // 4, y), (250 - (y - 150) // 4, y)], fill="#A08050", width=5)
    return img


def _crate() -> Image.Image:
    img, d = new_layer(_SIZE)
    d.rounded_rectangle([50, 90, 270, 270], radius=10, fill="#C9A56A", outline=INK, width=6)
    d.line([(50, 90), (270, 270)], fill="#A08050", width=8)
    d.line([(270, 90), (50, 270)], fill="#A08050", width=8)
    d.rectangle([50, 166, 270, 186], fill="#A08050")
    return img


def _oar() -> Image.Image:
    img, d = new_layer(_SIZE)
    capsule(d, (80, 280), (220, 70), 16, "#9A7A52")
    oval(d, 232, 58, 34, 56, "#B08C60")
    return img


def _hammer() -> Image.Image:
    img, d = new_layer(_SIZE)
    capsule(d, (90, 270), (220, 90), 18, "#9A7A52")
    d.rounded_rectangle([170, 40, 290, 110], radius=12, fill="#8A8074", outline=INK, width=6)
    return img


def _ladder() -> Image.Image:
    img, d = new_layer(_SIZE)
    capsule(d, (90, 300), (130, 30), 16, "#9A7A52")
    capsule(d, (230, 300), (190, 30), 16, "#9A7A52")
    for y in (80, 140, 200, 260):
        t = (y - 30) / 270
        lx = 130 - 40 * (1 - t)
        rx = 190 + 40 * (1 - t)
        d.line([(lx, y), (rx, y)], fill="#9A7A52", width=14)
    return img


def _lantern() -> Image.Image:
    img, d = new_layer(_SIZE)
    capsule(d, (160, 30), (160, 70), 8, INK, ow=3)
    d.rounded_rectangle([100, 70, 220, 250], radius=22, fill="#E8A33D", outline=INK, width=7)
    circle(d, 160, 160, 44, "#FFF3C8", ow=0, outline="#FFF3C8")
    d.rounded_rectangle([110, 250, 210, 280], radius=8, fill="#9A7A52", outline=INK, width=5)
    return img


def _signpost() -> Image.Image:
    img, d = new_layer(_SIZE)
    capsule(d, (150, 300), (150, 50), 18, "#9A7A52")
    d.polygon([(150, 70), (290, 70), (310, 110), (290, 150), (150, 150)], fill="#C9A56A")
    d.polygon([(150, 170), (30, 170), (10, 210), (30, 250), (150, 250)], fill="#B08C60")
    d.line([(170, 110), (270, 110)], fill="#8E6A44", width=6)
    d.line([(170, 210), (60, 210)], fill="#8E6A44", width=6)
    return img


def _rope() -> Image.Image:
    img, d = new_layer(_SIZE)
    for r in (110, 84, 58):
        d.ellipse([160 - r, 190 - r // 2, 160 + r, 190 + r // 2], outline="#B08C60", width=16)
    d.line([(258, 176), (300, 120)], fill="#B08C60", width=14)
    circle(d, 302, 112, 12, "#B08C60", ow=4, outline=INK)
    d.ellipse([50, 74, 150, 150], outline=INK, width=4)
    return img


def _stone() -> Image.Image:
    img, d = new_layer(_SIZE)
    d.polygon([(52, 220), (86, 120), (170, 88), (258, 132), (274, 226), (168, 274)],
              fill="#9E9A92", outline=INK, width=6)
    d.polygon([(110, 138), (168, 112), (214, 140), (160, 164)], fill="#B8B4AC")
    return img


_BUILDERS = {
    "scroll": _scroll, "oil_lamp": _oil_lamp, "jug": _jug, "basket": _basket,
    "crate": _crate, "oar": _oar, "hammer": _hammer, "ladder": _ladder,
    "lantern": _lantern, "signpost": _signpost, "rope": _rope, "stone": _stone,
}
