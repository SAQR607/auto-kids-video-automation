"""Prop sprites: 20 props + FX variants, drawn 256x256 RGBA, cached."""

from __future__ import annotations

from PIL import Image, ImageDraw

from .shapes import capsule, circle, new_layer, oval, poly

PROPS = (
    "acorn_cap", "map_scroll", "lantern", "tool_belt", "leaf_boat", "stone_stack",
    "pinecone", "honey_drop", "pebble", "twig_pencil", "button", "thread_spool",
    "music_box", "bell_flower", "raft", "rope_coil", "berry_basket", "crayon",
    "paper_star", "shell",
)

_CACHE: dict[str, Image.Image] = {}


def get_prop(prop_id: str) -> Image.Image:
    img = _CACHE.get(prop_id)
    if img is None:
        img = _PROPS.get(prop_id, _pebble)()
        _CACHE[prop_id] = img
    return img


def _base() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    return new_layer((256, 256))


def _acorn_cap():
    img, d = _base()
    d.chord([36, 60, 220, 196], 180, 360, fill="#6B4A2E")
    d.rectangle([36, 128, 220, 150], fill="#6B4A2E")
    oval(d, 128, 190, 78, 56, "#C89A5B")
    capsule(d, (128, 66), (128, 30), 16, "#5A3D24")
    for x in (76, 128, 180):
        d.line([(x, 96), (x, 132)], fill="#5A3D24", width=7)
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


def _lantern():
    img, d = _base()
    capsule(d, (128, 44), (128, 12), 10, "#3A2A1E", ow=3)
    d.arc([78, 20, 178, 90], 180, 360, fill="#3A2A1E", width=10)
    d.rounded_rectangle([64, 80, 192, 224], radius=24, fill="#E8A33D", outline="#3A2A1E", width=8)
    circle(d, 128, 152, 40, "#FFF3C8", ow=0, outline="#FFF3C8")
    circle(d, 128, 152, 24, "#FFFFFF", ow=0, outline="#FFFFFF")
    return img


def _tool_belt():
    img, d = _base()
    d.rounded_rectangle([24, 96, 232, 160], radius=26, fill="#A98A5B", outline="#3A2A1E", width=7)
    d.rounded_rectangle([104, 84, 152, 172], radius=10, fill="#E8C84E", outline="#3A2A1E", width=6)
    capsule(d, (60, 160), (44, 224), 22, "#7A5433")
    capsule(d, (196, 160), (212, 224), 22, "#7A5433")
    return img


def _leaf_boat():
    img, d = _base()
    poly(d, [(28, 150), (128, 96), (228, 150), (128, 196)], "#5FA34F")
    d.line([(50, 148), (206, 148)], fill="#4E8A44", width=6)
    d.line([(128, 104), (128, 188)], fill="#4E8A44", width=6)
    capsule(d, (128, 100), (128, 40), 10, "#6B4A2E", ow=3)
    poly(d, [(134, 44), (196, 64), (134, 92)], "#F2E6C8")
    return img


def _stone_stack():
    img, d = _base()
    for (cx, cy, rx, ry, col) in ((128, 210, 86, 34, "#8A8F98"), (128, 154, 68, 30, "#9AA0AA"),
                                  (128, 106, 52, 26, "#7E848E"), (128, 66, 36, 22, "#A6ACB6")):
        oval(d, cx, cy, rx, ry, col)
    return img


def _pinecone():
    img, d = _base()
    oval(d, 128, 140, 62, 86, "#8A6A45")
    for row in range(4):
        for i in range(3 + row % 2):
            x = 128 + (i - (2 + row % 2) / 2) * 34
            y = 90 + row * 38
            d.arc([x - 16, y - 12, x + 16, y + 20], 180, 360, fill="#5A3D24", width=7)
    capsule(d, (128, 56), (138, 24), 12, "#5A3D24", ow=3)
    return img


def _honey_drop():
    img, d = _base()
    d.chord([56, 96, 200, 240], 0, 360, fill="#E8A33D", outline="#3A2A1E", width=7)
    poly(d, [(128, 30), (96, 120), (160, 120)], "#E8A33D")
    d.arc([70, 110, 160, 200], 120, 260, fill="#FFF3C8", width=10)
    return img


def _pebble():
    img, d = _base()
    oval(d, 128, 150, 84, 62, "#9A8F7E")
    oval(d, 104, 132, 34, 20, "#B4A99A")
    return img


def _twig_pencil():
    img, d = _base()
    capsule(d, (64, 210), (190, 54), 22, "#8A6A45")
    poly(d, [(186, 66), (214, 30), (176, 34)], "#E8D8B8")
    poly(d, [(204, 42), (214, 30), (196, 34)], "#3A2A1E")
    capsule(d, (76, 202), (54, 224), 24, "#5E8F4C")
    return img


def _button():
    img, d = _base()
    circle(d, 128, 140, 78, "#C4453D")
    circle(d, 104, 120, 10, "#8A2F2B", ow=0, outline="#8A2F2B")
    circle(d, 152, 120, 10, "#8A2F2B", ow=0, outline="#8A2F2B")
    circle(d, 104, 160, 10, "#8A2F2B", ow=0, outline="#8A2F2B")
    circle(d, 152, 160, 10, "#8A2F2B", ow=0, outline="#8A2F2B")
    return img


def _thread_spool():
    img, d = _base()
    d.rounded_rectangle([76, 44, 180, 212], radius=14, fill="#4E7A9E", outline="#3A2A1E", width=6)
    d.rectangle([76, 92, 180, 164], fill="#7EB2D8")
    for y in (104, 124, 144):
        d.line([(80, y), (176, y + 8)], fill="#5E93BE", width=6)
    d.rounded_rectangle([60, 36, 196, 64], radius=10, fill="#3F6579", outline="#3A2A1E", width=5)
    d.rounded_rectangle([60, 196, 196, 224], radius=10, fill="#3F6579", outline="#3A2A1E", width=5)
    return img


def _music_box():
    img, d = _base()
    d.rounded_rectangle([48, 96, 208, 216], radius=16, fill="#8A5A3B", outline="#3A2A1E", width=7)
    d.rounded_rectangle([40, 52, 216, 110], radius=14, fill="#A9744B", outline="#3A2A1E", width=7)
    circle(d, 128, 158, 30, "#E8C84E", ow=5, outline="#3A2A1E")
    for ang in (0, 90, 180, 270):
        import math
        px = 128 + math.cos(math.radians(ang)) * 18
        py = 158 + math.sin(math.radians(ang)) * 18
        circle(d, px, py, 5, "#8A5A3B", ow=0, outline="#8A5A3B")
    capsule(d, (196, 76), (230, 60), 10, "#E8C84E", ow=3)
    return img


def _bell_flower():
    img, d = _base()
    capsule(d, (128, 236), (128, 150), 12, "#5E8F4C", ow=3)
    d.chord([64, 60, 192, 190], 0, 360, fill="#E8B4D8", outline="#3A2A1E", width=7)
    d.polygon([(64, 150), (128, 190), (192, 150)], fill="#E8B4D8")
    d.arc([64, 60, 192, 190], 0, 180, fill="#3A2A1E", width=7)
    circle(d, 128, 194, 14, "#F7D774", ow=4, outline="#3A2A1E")
    oval(d, 106, 96, 24, 30, "#F6D8EC")
    return img


def _raft():
    img, d = _base()
    for i, y in enumerate((110, 146, 182, 218)):
        capsule(d, (30, y), (226, y), 30, "#A98A5B" if i % 2 else "#8A6A45")
    capsule(d, (72, 96), (72, 232), 12, "#5A3D24", ow=3)
    capsule(d, (184, 96), (184, 232), 12, "#5A3D24", ow=3)
    capsule(d, (72, 108), (184, 108), 10, "#5A3D24", ow=3)
    return img


def _rope_coil():
    img, d = _base()
    for r, col in ((92, "#C4A67C"), (70, "#AD8F65"), (48, "#C4A67C")):
        d.ellipse([128 - r, 148 - r, 128 + r, 148 + r], outline=col, width=16)
    capsule(d, (196, 96), (228, 54), 14, "#C4A67C", ow=3)
    return img


def _berry_basket():
    img, d = _base()
    d.polygon([(52, 128), (204, 128), (184, 224), (72, 224)], fill="#A98A5B", outline="#3A2A1E")
    d.line([(52, 128), (204, 128)], fill="#3A2A1E", width=7)
    for i in range(4):
        d.line([(70 + i * 38, 132), (82 + i * 34, 218)], fill="#8A6A45", width=6)
    for cx, cy, col in ((96, 116, "#C4453D"), (140, 104, "#7E5AA8"), (184, 118, "#C4453D"),
                        (118, 92, "#C4453D"), (162, 84, "#7E5AA8")):
        circle(d, cx, cy, 26, col, ow=5, outline="#3A2A1E")
    oval(d, 140, 74, 20, 10, "#5E8F4C")
    return img


def _crayon():
    img, d = _base()
    d.rounded_rectangle([96, 60, 160, 216], radius=14, fill="#E8574C", outline="#3A2A1E", width=6)
    poly(d, [(96, 66), (128, 16), (160, 66)], "#E8574C")
    poly(d, [(112, 50), (128, 16), (144, 50)], "#B23A33")
    d.rectangle([96, 140, 160, 158], fill="#F2E6C8", outline="#3A2A1E")
    return img


def _paper_star():
    img, d = _base()
    import math
    pts = []
    for i in range(10):
        r = 96 if i % 2 == 0 else 44
        a = math.radians(-90 + i * 36)
        pts.append((128 + math.cos(a) * r, 140 + math.sin(a) * r))
    poly(d, pts, "#F7D774")
    return img


def _shell():
    img, d = _base()
    d.pieslice([44, 60, 212, 228], 180, 360, fill="#F2D8C8", outline="#3A2A1E", width=7)
    for ang in (205, 235, 265, 295, 325):
        x = 128 + math.cos(math.radians(ang)) * 76
        y = 144 + math.sin(math.radians(ang)) * 76
        d.line([(128, 144), (x, y)], fill="#D8B8A8", width=7)
    d.line([(44, 144), (212, 144)], fill="#3A2A1E", width=7)
    return img


import math  # noqa: E402  (used by several builders)

_PROPS = {
    "acorn_cap": _acorn_cap, "map_scroll": _map_scroll, "lantern": _lantern,
    "tool_belt": _tool_belt, "leaf_boat": _leaf_boat, "stone_stack": _stone_stack,
    "pinecone": _pinecone, "honey_drop": _honey_drop, "pebble": _pebble,
    "twig_pencil": _twig_pencil, "button": _button, "thread_spool": _thread_spool,
    "music_box": _music_box, "bell_flower": _bell_flower, "raft": _raft,
    "rope_coil": _rope_coil, "berry_basket": _berry_basket, "crayon": _crayon,
    "paper_star": _paper_star, "shell": _shell,
}
