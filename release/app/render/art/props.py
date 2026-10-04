"""Prop sprites: the 20 binding props from universe/manifest.json, 256x256 RGBA."""

from __future__ import annotations

import math

from PIL import Image, ImageDraw

from .shapes import capsule, circle, new_layer, oval, poly

PROPS = (
    "leaf_cap", "tool_belt", "blue_pebble", "amber_scarf", "magnifier_leaf",
    "rope_coil", "acorn_cup", "satchel", "lantern", "map_scroll",
    "whistle_berry", "snack_basket", "umbrella_leaf", "compass_stone", "plank_boat",
    "shell_bucket", "twig_staff", "book", "pocket_watch", "pinecone_ball",
)

_CACHE: dict[str, Image.Image] = {}


def get_prop(prop_id: str) -> Image.Image:
    img = _CACHE.get(prop_id)
    if img is None:
        img = _BUILDERS.get(prop_id, _blue_pebble)()
        _CACHE[prop_id] = img
    return img


def _base() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    return new_layer((256, 256))


def _leaf_cap():
    img, d = _base()
    d.chord([36, 76, 220, 216], 180, 360, fill="#5C8A3A", outline="#3A2A1E", width=7)
    d.rectangle([36, 146, 220, 162], fill="#5C8A3A")
    d.line([(36, 154), (220, 154)], fill="#3A2A1E", width=7)
    capsule(d, (128, 84), (128, 40), 12, "#3F6B29", ow=3)
    d.line([(128, 140), (128, 92)], fill="#3F6B29", width=6)
    for x in (84, 172):
        d.line([(x, 152), (x - 16, 118)], fill="#3F6B29", width=5)
    return img


def _tool_belt():
    img, d = _base()
    d.rounded_rectangle([24, 96, 232, 160], radius=26, fill="#A98A5B", outline="#3A2A1E", width=7)
    d.rounded_rectangle([104, 84, 152, 172], radius=10, fill="#E8C84E", outline="#3A2A1E", width=6)
    capsule(d, (60, 160), (44, 224), 22, "#7A5433")
    capsule(d, (196, 160), (212, 224), 22, "#7A5433")
    return img


def _blue_pebble():
    img, d = _base()
    oval(d, 128, 150, 84, 62, "#5B8FB9")
    oval(d, 104, 132, 34, 20, "#8FC0DE")
    return img


def _amber_scarf():
    img, d = _base()
    d.arc([56, 40, 200, 160], 0, 360, fill="#E9973A", width=40)
    d.rounded_rectangle([86, 96, 170, 150], radius=18, fill="#E9973A", outline="#3A2A1E", width=6)
    poly(d, [(96, 146), (160, 146), (150, 232), (112, 232)], "#E9973A")
    for i in range(4):
        x = 108 + i * 16
        d.line([(x, 226), (x, 244)], fill="#3A2A1E", width=5)
    d.line([(96, 120), (160, 120)], fill="#C47A28", width=8)
    return img


def _magnifier_leaf():
    img, d = _base()
    poly(d, [(40, 200), (150, 60), (224, 120), (110, 240)], "#5FA34F")
    d.line([(56, 196), (210, 128)], fill="#4E8A44", width=7)
    circle(d, 150, 130, 58, (255, 255, 255, 90), ow=8, outline="#3A2A1E")
    d.arc([104, 84, 196, 176], 0, 360, fill="#BCE8F5", width=6)
    capsule(d, (92, 190), (48, 236), 20, "#8A6A45")
    return img


def _rope_coil():
    img, d = _base()
    for r, col in ((92, "#C4A67C"), (70, "#AD8F65"), (48, "#C4A67C")):
        d.ellipse([128 - r, 148 - r, 128 + r, 148 + r], outline=col, width=16)
    capsule(d, (196, 96), (228, 54), 14, "#C4A67C", ow=3)
    return img


def _acorn_cup():
    img, d = _base()
    d.chord([36, 60, 220, 196], 180, 360, fill="#6B4A2E")
    d.rectangle([36, 128, 220, 150], fill="#6B4A2E")
    oval(d, 128, 190, 78, 56, "#C89A5B")
    capsule(d, (128, 66), (128, 30), 16, "#5A3D24")
    for x in (76, 128, 180):
        d.line([(x, 96), (x, 132)], fill="#5A3D24", width=7)
    return img


def _satchel():
    img, d = _base()
    d.rounded_rectangle([48, 108, 208, 224], radius=26, fill="#A9744B", outline="#3A2A1E", width=7)
    d.rounded_rectangle([40, 76, 216, 132], radius=24, fill="#8A5A3B", outline="#3A2A1E", width=7)
    d.arc([64, 10, 192, 120], 180, 360, fill="#5A3D24", width=14)
    d.rounded_rectangle([104, 120, 152, 156], radius=8, fill="#E8C84E", outline="#3A2A1E", width=5)
    d.line([(48, 168), (208, 168)], fill="#8A5A3B", width=6)
    return img


def _lantern():
    img, d = _base()
    capsule(d, (128, 44), (128, 12), 10, "#3A2A1E", ow=3)
    d.arc([78, 20, 178, 90], 180, 360, fill="#3A2A1E", width=10)
    d.rounded_rectangle([64, 80, 192, 224], radius=24, fill="#E8A33D", outline="#3A2A1E", width=8)
    circle(d, 128, 152, 40, "#FFF3C8", ow=0, outline="#FFF3C8")
    circle(d, 128, 152, 24, "#FFFFFF", ow=0, outline="#FFFFFF")
    return img


def _map_scroll():
    img, d = _base()
    d.rounded_rectangle([52, 44, 204, 212], radius=16, fill="#F2E6C8", outline="#3A2A1E", width=7)
    capsule(d, (40, 52), (40, 204), 26, "#8A6A45")
    capsule(d, (216, 52), (216, 204), 26, "#8A6A45")
    d.line([(80, 100), (130, 84), (170, 120)], fill="#B08A5B", width=6, joint="curve")
    d.line([(80, 150), (120, 170), (176, 150)], fill="#B08A5B", width=6, joint="curve")
    circle(d, 176, 152, 10, "#C4453D", ow=0, outline="#C4453D")
    circle(d, 82, 100, 8, "#5E8F4C", ow=0, outline="#5E8F4C")
    return img


def _whistle_berry():
    img, d = _base()
    circle(d, 128, 152, 78, "#C4453D")
    oval(d, 100, 122, 30, 20, "#E8827A")
    capsule(d, (128, 76), (140, 36), 12, "#5E8F4C", ow=3)
    oval(d, 156, 66, 30, 18, "#5FA34F")
    circle(d, 170, 168, 20, "#8A2F2B", ow=5, outline="#3A2A1E")
    circle(d, 170, 168, 9, "#F2E6C8", ow=0, outline="#F2E6C8")
    return img


def _snack_basket():
    img, d = _base()
    d.polygon([(52, 128), (204, 128), (184, 224), (72, 224)], fill="#A98A5B", outline="#3A2A1E")
    d.line([(52, 128), (204, 128)], fill="#3A2A1E", width=7)
    for i in range(4):
        d.line([(70 + i * 38, 132), (82 + i * 34, 218)], fill="#8A6A45", width=6)
    d.arc([64, 30, 192, 150], 180, 360, fill="#5A3D24", width=12)
    oval(d, 100, 116, 34, 26, "#C89A5B")
    d.chord([70, 84, 130, 136], 180, 360, fill="#6B4A2E")
    circle(d, 156, 112, 26, "#C4453D")
    circle(d, 186, 122, 22, "#7E5AA8")
    return img


def _umbrella_leaf():
    img, d = _base()
    capsule(d, (128, 246), (128, 92), 14, "#8A6A45", ow=4)
    d.chord([36, 40, 220, 200], 180, 360, fill="#5FA34F", outline="#3A2A1E", width=7)
    d.rectangle([36, 118, 220, 134], fill="#5FA34F")
    d.line([(36, 126), (220, 126)], fill="#3A2A1E", width=7)
    for x in (84, 128, 172):
        d.line([(x, 126), (x, 74)], fill="#4E8A44", width=6)
    d.line([(128, 246), (156, 234)], fill="#8A6A45", width=12)
    return img


def _compass_stone():
    img, d = _base()
    oval(d, 128, 148, 96, 84, "#9A8F7E")
    oval(d, 128, 148, 74, 64, "#F2E6C8")
    poly(d, [(128, 96), (144, 148), (128, 140)], "#C4453D")
    poly(d, [(128, 200), (112, 148), (128, 156)], "#3A2A1E")
    circle(d, 128, 148, 8, "#3A2A1E", ow=0, outline="#3A2A1E")
    d.text((122, 84), "", fill="#3A2A1E")
    return img


def _plank_boat():
    img, d = _base()
    for i, y in enumerate((110, 146, 182, 218)):
        capsule(d, (30, y), (226, y), 30, "#A98A5B" if i % 2 else "#8A6A45")
    capsule(d, (72, 96), (72, 232), 12, "#5A3D24", ow=3)
    capsule(d, (184, 96), (184, 232), 12, "#5A3D24", ow=3)
    capsule(d, (72, 108), (184, 108), 10, "#5A3D24", ow=3)
    return img


def _shell_bucket():
    img, d = _base()
    d.polygon([(64, 108), (192, 108), (176, 224), (80, 224)], fill="#B08D6A", outline="#3A2A1E")
    d.line([(64, 108), (192, 108)], fill="#3A2A1E", width=7)
    d.arc([52, 60, 204, 200], 180, 360, fill="#5A3D24", width=12)
    d.pieslice([96, 132, 160, 196], 180, 360, fill="#F2D8C8", outline="#3A2A1E", width=5)
    for ang in (205, 250, 295, 335):
        x = 128 + math.cos(math.radians(ang)) * 30
        y = 164 + math.sin(math.radians(ang)) * 30
        d.line([(128, 164), (x, y)], fill="#D8B8A8", width=5)
    return img


def _twig_staff():
    img, d = _base()
    capsule(d, (96, 240), (150, 30), 20, "#8A6A45")
    d.line([(112, 170), (134, 96)], fill="#6B4A2E", width=6)
    capsule(d, (150, 30), (184, 58), 12, "#8A6A45", ow=4)
    oval(d, 178, 40, 26, 18, "#5FA34F")
    circle(d, 96, 232, 16, "#C89A5B", ow=4, outline="#3A2A1E")
    return img


def _book():
    img, d = _base()
    d.rounded_rectangle([56, 48, 200, 216], radius=14, fill="#4E7A4A", outline="#3A2A1E", width=7)
    d.rectangle([70, 48, 86, 216], fill="#3F6539")
    d.line([(86, 48), (86, 216)], fill="#3A2A1E", width=6)
    d.rounded_rectangle([96, 84, 184, 132], radius=8, fill="#F2E6C8", outline="#3A2A1E", width=5)
    d.line([(110, 108), (170, 108)], fill="#8A6A45", width=6)
    d.line([(110, 156), (170, 156)], fill="#F2E6C8", width=5)
    d.line([(110, 178), (156, 178)], fill="#F2E6C8", width=5)
    return img


def _pocket_watch():
    img, d = _base()
    d.arc([70, 6, 186, 116], 180, 360, fill="#C9CDD1", width=10)
    capsule(d, (128, 12), (128, 34), 16, "#C9CDD1", ow=4)
    circle(d, 128, 150, 84, "#E8C84E")
    circle(d, 128, 150, 64, "#F7EFC8")
    d.line([(128, 150), (128, 104)], fill="#3A2A1E", width=7)
    d.line([(128, 150), (160, 166)], fill="#3A2A1E", width=7)
    circle(d, 128, 150, 7, "#3A2A1E", ow=0, outline="#3A2A1E")
    for ang in range(0, 360, 90):
        x = 128 + math.cos(math.radians(ang)) * 52
        y = 150 + math.sin(math.radians(ang)) * 52
        circle(d, x, y, 5, "#3A2A1E", ow=0, outline="#3A2A1E")
    d.rounded_rectangle([116, 44, 140, 70], radius=6, fill="#C9CDD1", outline="#3A2A1E", width=5)
    return img


def _pinecone_ball():
    img, d = _base()
    circle(d, 128, 148, 92, "#8A6A45")
    for row in range(5):
        for i in range(5 + row % 2):
            x = 128 + (i - (4 + row % 2) / 2) * 36
            y = 76 + row * 34
            if (x - 128) ** 2 + (y - 148) ** 2 > 84 ** 2:
                continue
            d.arc([x - 17, y - 13, x + 17, y + 21], 180, 360, fill="#5A3D24", width=7)
    capsule(d, (128, 56), (138, 26), 12, "#5A3D24", ow=3)
    return img


_BUILDERS = {
    "leaf_cap": _leaf_cap, "tool_belt": _tool_belt, "blue_pebble": _blue_pebble,
    "amber_scarf": _amber_scarf, "magnifier_leaf": _magnifier_leaf, "rope_coil": _rope_coil,
    "acorn_cup": _acorn_cup, "satchel": _satchel, "lantern": _lantern, "map_scroll": _map_scroll,
    "whistle_berry": _whistle_berry, "snack_basket": _snack_basket, "umbrella_leaf": _umbrella_leaf,
    "compass_stone": _compass_stone, "plank_boat": _plank_boat, "shell_bucket": _shell_bucket,
    "twig_staff": _twig_staff, "book": _book, "pocket_watch": _pocket_watch,
    "pinecone_ball": _pinecone_ball,
}
