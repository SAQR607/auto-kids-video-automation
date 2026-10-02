"""Location art: 7 world locations, 4 time-of-day skies, 3 parallax layers.

paint_location(loc_id, tod) -> {"sky","far","mid","near"} each RGBA 2200x1400.
Layers stack: sky (static), far (slow pan), mid (medium), near (fast).
Renderer applies a global grade per tod on top.
"""

from __future__ import annotations

from PIL import Image, ImageDraw

from .shapes import capsule, circle, new_layer, oval, poly

W, H = 2200, 1400

SKIES = {
    "day": ("#8ED4F5", "#CDEFFC"),
    "morning": ("#FFD9A0", "#FFF3D6"),
    "dusk": ("#F5A96B", "#FFD9B0"),
    "night": ("#1B2A4A", "#31486F"),
}

LOCATIONS = (
    "hollow_oak_village", "great_hollow", "whispering_stream",
    "glimmer_meadow", "willowbys_burrow", "mossy_ravine", "glimmer_cave",
)


def _sky(d: ImageDraw.ImageDraw, tod: str, cx: int = 0) -> None:
    top, bot = SKIES.get(tod, SKIES["day"])
    for i in range(H):
        t = i / H
        r = _lerp_col(top, bot, t)
        d.line([(0, i), (W, i)], fill=r)
    if tod == "night":
        for x, y, r in ((300, 180, 5), (760, 110, 4), (1250, 210, 6), (1830, 140, 4),
                        (2050, 300, 5), (520, 320, 3), (1560, 90, 3)):
            circle(d, x, y, r, "#FFF8D8", ow=0, outline="#FFF8D8")
        circle(d, 1850, 220, 86, "#F5F0DC", ow=0, outline="#F5F0DC")
        circle(d, 1888, 196, 78, SKIES["night"][0], ow=0, outline=SKIES["night"][0])
    else:
        sx = {"day": (1760, 200), "morning": (460, 300), "dusk": (1700, 330)}[tod]
        glow = {"day": "#FFF6C8", "morning": "#FFE9B8", "dusk": "#FFC98A"}[tod]
        circle(d, sx[0], sx[1], 96, glow, ow=0, outline=glow)
        circle(d, sx[0], sx[1], 70, "#FFFBE8", ow=0, outline="#FFFBE8")
        if tod == "dusk":
            for x, y in ((320, 240), (900, 160), (1400, 260)):
                oval(d, x, y, 130, 34, "#FFD7B8")
    # clouds
    if tod != "night":
        cc = "#FFFFFF" if tod != "dusk" else "#FFE0C4"
        for cx0, cy0, s in ((360, 240, 1.0), (1100, 150, 0.75), (1750, 420, 0.85), (700, 430, 0.6)):
            for ox, oy, rx, ry in ((0, 0, 90, 44), (-70, 14, 62, 32), (74, 12, 58, 30)):
                oval(d, cx0 + ox * s, cy0 + oy * s, rx * s, ry * s, cc)


def _lerp_col(a: str, b: str, t: float) -> tuple[int, int, int, int]:
    ca = tuple(int(a[i:i + 2], 16) for i in (1, 3, 5))
    cb = tuple(int(b[i:i + 2], 16) for i in (1, 3, 5))
    return tuple(int(ca[i] + (cb[i] - ca[i]) * t) for i in range(3)) + (255,)


def _ground(d: ImageDraw.ImageDraw, y: int, color: str, blade: str | None = None) -> None:
    d.rectangle([0, y, W, H], fill=color)
    if blade:
        for x in range(0, W, 26):
            h = 14 + (x * 7919 % 17)
            d.line([(x, y + 4), (x + 6, y - h)], fill=blade, width=4)


def _tree(d: ImageDraw.ImageDraw, x: int, y: int, s: float, trunk: str, leaf: str,
          leaf2: str | None = None) -> None:
    capsule(d, (x, y), (x, y - 150 * s), 34 * s, trunk)
    for ox, oy, r in ((0, -210, 110), (-86, -160, 76), (86, -160, 76), (0, -290, 72)):
        circle(d, x + ox * s, y + oy * s, r * s, leaf)
    if leaf2:
        circle(d, x - 40 * s, y - 250 * s, 40 * s, leaf2)


def _oak(d: ImageDraw.ImageDraw, x: int, y: int) -> None:
    """Big hollow oak — the village centerpiece."""
    capsule(d, (x - 40, y + 10), (x - 10, y - 320), 96, "#6B4A2E")
    capsule(d, (x + 60, y + 10), (x + 30, y - 300), 80, "#6B4A2E")
    d.polygon([(x - 150, y + 30), (x - 60, y - 120), (x + 70, y - 120), (x + 170, y + 30)], fill="#5A3D24")
    for ox, oy, r in ((-120, -420, 150), (60, -460, 170), (-30, -560, 140),
                      (-260, -350, 120), (230, -360, 130), (150, -560, 100), (-180, -560, 96)):
        circle(d, x + ox, y + oy, r, "#4E8A44")
    for ox, oy, r in ((-80, -500, 60), (120, -400, 66), (-200, -430, 54)):
        circle(d, x + ox, y + oy, r, "#5FA34F")
    # round door + windows
    d.chord([x - 70, y - 170, x + 10, y - 30], 180, 360, fill="#8A6A45")
    d.rectangle([x - 70, y - 100, x + 10, y + 20], fill="#8A6A45")
    d.chord([x - 60, y - 160, x, y - 40], 180, 360, fill="#3A2A1E")
    d.rectangle([x - 60, y - 100, x, y + 20], fill="#3A2A1E")
    circle(d, x - 100, y - 240, 30, "#FFD98A", ow=5, outline="#3A2A1E")
    circle(d, x + 110, y - 230, 30, "#FFD98A", ow=5, outline="#3A2A1E")


def _mush_lamp(d: ImageDraw.ImageDraw, x: int, y: int) -> None:
    capsule(d, (x, y), (x, y - 70), 12, "#E8DCC8")
    d.chord([x - 34, y - 116, x + 34, y - 48], 180, 360, fill="#E2574C")
    d.rectangle([x - 34, y - 84, x + 34, y - 66], fill="#E2574C")
    for ox in (-18, 0, 18):
        circle(d, x + ox, y - 96, 6, "#FFE9C8", ow=0, outline="#FFE9C8")


# ------------------------------------------------------------- painters ------

def paint_location(loc_id: str, tod: str = "day") -> dict[str, Image.Image]:
    sky, ds = new_layer((W, H))
    far, df = new_layer((W, H))
    mid, dm = new_layer((W, H))
    near, dn = new_layer((W, H))
    _sky(ds, tod)

    if loc_id == "hollow_oak_village":
        _hills(df, "#9CC77E", "#87B36B")
        _ground(dm, 860, "#7FB069", "#6BA05A")
        _oak(dm, 1100, 940)
        _house(dm, 520, 940, "#C98A5B")
        _house(dm, 1720, 960, "#B97A6B")
        for x in (330, 760, 1440, 1960, 2100):
            _mush_lamp(dm, x, 950)
        _tree(df, 180, 900, 0.8, "#6B4A2E", "#4E8A44")
        _tree(df, 2050, 880, 0.7, "#6B4A2E", "#5FA34F")
        _grass(dn, 1240, "#5E8F4C")
        for x in (200, 900, 1600):
            _flower(dn, x, 1300, "#F0A5C0")
            _flower(dn, x + 90, 1345, "#F7D774")

    elif loc_id == "great_hollow":
        df.rectangle([0, 0, W, H], fill="#4A301E")
        for bx, by, bw in ((60, 60, 300), (520, 0, 260), (1000, 80, 320), (1500, 20, 280), (1950, 70, 300)):
            d2 = df
            for i in range(bx, bx + bw, 46):
                d2.line([(i, 0), (i - 40, H)], fill="#3A2617", width=18)
        dm.rectangle([0, 900, W, H], fill="#6B4A2E")
        _map_table(dm, 620, 980)
        _lantern(dm, 1450, 420)
        _rope_door(dm, 1900, 940)
        for x in (260, 2140):
            _book_pile(dm, x, 1240)
        dn.rectangle([0, 1330, W, H], fill="#4A301E")

    elif loc_id == "whispering_stream":
        _hills(df, "#A8C98F", "#93B67C")
        _ground(dm, 640, "#7FB069", "#6BA05A")
        _stream(dm, 700)
        for x, y, s in ((320, 900, 0.9), (1880, 860, 1.0), (1500, 700, 0.7), (700, 690, 0.75)):
            _tree(dm, x, y, s, "#6B4A2E", "#4E8A44")
        for x in (520, 1080, 1660):
            _stepping_stone(dm, x, 1060)
        _reeds(dn, 120, 1150)
        _reeds(dn, 2000, 1180)
        _grass(dn, 1300, "#5E8F4C")

    elif loc_id == "glimmer_meadow":
        _hills(df, "#8FC98A", "#7AB677")
        if tod == "night" or tod == "dusk":
            df.rectangle([0, 0, W, H], fill=(40, 30, 60, 40))
        _ground(dm, 820, "#79B268", "#6BA05A")
        for x, y, r in ((300, 700, 46), (760, 640, 54), (1250, 690, 44), (1750, 650, 52), (2050, 720, 40)):
            _flower_big(dm, x, y, r)
        for x in (180, 640, 1140, 1620, 2100):
            _tree(df, x, 840, 0.55 + (x % 3) * 0.08, "#6B4A2E", "#4E8A44")
        _grass(dn, 1240, "#5E8F4C")
        for x, y in ((420, 1160), (980, 1220), (1540, 1150)):
            _glimmer(dm, x, y)

    elif loc_id == "willowbys_burrow":
        df.rectangle([0, 0, W, H], fill="#6B4A2E")
        d2 = df
        for i in range(-200, W + 200, 70):
            d2.line([(i, 0), (i + 120, H)], fill="#5A3D24", width=26)
        dm.rectangle([0, 880, W, H], fill="#A98A5B")
        d3 = dm
        for i in range(-100, W + 100, 120):
            d3.line([(i, 880), (i + 60, H)], fill="#96774C", width=8)
        _window(dm, 420, 520)
        _bookshelf(dm, 1650, 400)
        _tea_table(dm, 800, 1040)
        _rug(dm, 1150, 1240)
        _armchair(dm, 380, 1160)
        dn.rectangle([0, 1350, W, H], fill="#7A5A38")

    elif loc_id == "mossy_ravine":
        _sky_only_wall(df, "#7E8A7A")
        d4 = df
        d4.polygon([(0, 300), (500, 260), (900, 340), (1400, 280), (1900, 350), (2200, 300),
                    (2200, 0), (0, 0)], fill="#6E7A6C")
        _ground(dm, 980, "#6E7E62", "#5E6E52")
        dm.polygon([(0, 1400), (0, 980), (260, 640), (520, 700), (700, 980)], fill="#59645A")
        dm.polygon([(2200, 1400), (2200, 940), (1960, 620), (1720, 700), (1560, 980)], fill="#59645A")
        _bridge(dm, 1100, 760)
        for x in (300, 1900):
            _tree(dm, x, 990, 0.8, "#6B4A2E", "#4E8A44")
        for x, y in ((680, 620), (1520, 600), (420, 430)):
            _moss_patch(dm, x, y)
        _mist(dn, 1180)

    elif loc_id == "glimmer_cave":
        df.rectangle([0, 0, W, H], fill="#2E3A4E")
        for i in range(0, W, 90):
            h = 140 + (i * 617 % 200)
            df.polygon([(i - 40, 0), (i + 40, 0), (i + 18, h)], fill="#26303F")
            df.polygon([(i - 60, H), (i + 60, H), (i + 20, H - h + 60)], fill="#39465C")
        dm.rectangle([0, 1020, W, H], fill="#3E4A5E")
        _root_door(dm, 1100, 1020)
        _heart_stone(dm, 560, 900)
        for x, y, r in ((300, 760, 40), (840, 640, 52), (1450, 700, 44), (1950, 660, 56),
                        (1700, 880, 36), (180, 950, 34)):
            _glow_vein(dm, x, y, r)
        for x, y in ((700, 1100), (1600, 1150), (1250, 1240)):
            _glimmer(dm, x, y)

    return {"sky": sky, "far": far, "mid": mid, "near": near}


# ---- sub-painters ---------------------------------------------------------

def _hills(d, c1, c2):
    d.polygon([(0, 780), (400, 600), (900, 740), (1400, 580), (1900, 720), (2200, 640),
               (2200, 1400), (0, 1400)], fill=c1)
    d.polygon([(0, 900), (500, 760), (1100, 880), (1700, 750), (2200, 860),
               (2200, 1400), (0, 1400)], fill=c2)


def _house(d, x, y, wall):
    d.polygon([(x - 110, y), (x - 90, y - 150), (x + 90, y - 150), (x + 110, y)], fill=wall)
    d.polygon([(x - 130, y - 140), (x, y - 260), (x + 130, y - 140)], fill="#8A5A3B")
    d.rectangle([x - 30, y - 70, x + 30, y], fill="#5A3D24")
    circle(d, x - 70, y - 100, 22, "#FFE9C8", ow=4, outline="#3A2A1E")
    circle(d, x + 70, y - 100, 22, "#FFE9C8", ow=4, outline="#3A2A1E")


def _grass(d, y, color):
    for x in range(0, W, 34):
        h = 26 + (x * 7919 % 20)
        d.line([(x, y), (x + 8, y - h)], fill=color, width=6)


def _flower(d, x, y, col):
    for ang in range(0, 360, 72):
        import math
        px = x + math.cos(math.radians(ang)) * 14
        py = y + math.sin(math.radians(ang)) * 14
        circle(d, px, py, 9, col, ow=0, outline=col)
    circle(d, x, y, 8, "#F7D774", ow=0, outline="#F7D774")


def _flower_big(d, x, y, r):
    capsule(d, (x, y + r * 2), (x, y), 10, "#5E8F4C", ow=3)
    for ang in range(0, 360, 60):
        import math
        px = x + math.cos(math.radians(ang)) * r * 0.7
        py = y + math.sin(math.radians(ang)) * r * 0.7
        oval(d, px, py, r * 0.5, r * 0.38, "#F5E6B8")
    circle(d, x, y, r * 0.34, "#F0A5C0", ow=3)


def _glimmer(d, x, y):
    circle(d, x, y, 16, (255, 245, 180, 90), ow=0, outline=(255, 245, 180, 90))
    circle(d, x, y, 9, "#FFF7C4", ow=0, outline="#FFF7C4")
    circle(d, x, y, 4, "#FFFFFF", ow=0, outline="#FFFFFF")


def _stream(d, y0):
    d.polygon([(0, y0 + 120), (300, y0 + 40), (700, y0 + 160), (1100, y0 + 60),
               (1500, y0 + 180), (1900, y0 + 80), (2200, y0 + 150), (2200, y0 + 320),
               (1900, y0 + 240), (1500, y0 + 340), (1100, y0 + 220), (700, y0 + 320),
               (300, y0 + 200), (0, y0 + 280)], fill="#7EC8E3")
    for x, dy in ((200, 130), (640, 190), (1200, 140), (1700, 220), (2050, 160)):
        d.arc([x, y0 + dy, x + 160, y0 + dy + 70], 200, 340, fill="#BCE8F5", width=10)


def _stepping_stone(d, x, y):
    oval(d, x, y, 74, 34, "#9A8F7E")


def _reeds(d, x, y):
    for i in range(7):
        rx = x + i * 26
        h = 130 + (i * 37 % 60)
        capsule(d, (rx, y), (rx + 10, y - h), 8, "#5E8F4C", ow=3)
        oval(d, rx + 12, y - h, 9, 26, "#8A6A45")


def _map_table(d, x, y):
    oval(d, x, y, 210, 60, "#8A6A45")
    capsule(d, (x - 140, y + 40), (x - 120, y + 150), 26, "#6B4A2E")
    capsule(d, (x + 140, y + 40), (x + 120, y + 150), 26, "#6B4A2E")
    oval(d, x, y - 12, 150, 40, "#F2E6C8")
    d.line([(x - 90, y - 16), (x - 10, y - 30), (x + 80, y - 8)], fill="#B08A5B", width=5)
    circle(d, x + 96, y - 6, 8, "#C4453D", ow=0, outline="#C4453D")


def _lantern(d, x, y):
    capsule(d, (x, 0), (x, y - 60), 6, "#3A2A1E", ow=2)
    d.rounded_rectangle([x - 46, y - 60, x + 46, y + 60], radius=20, fill="#E8A33D", outline="#3A2A1E", width=6)
    circle(d, x, y, 26, "#FFF3C8", ow=0, outline="#FFF3C8")


def _rope_door(d, x, y):
    d.chord([x - 120, y - 260, x + 120, y + 40], 180, 360, fill="#5A3D24")
    d.rectangle([x - 120, y - 110, x + 120, y + 40], fill="#5A3D24")
    for i in range(x - 100, x + 101, 40):
        d.line([(i, y - 240), (i, y + 40)], fill="#7A5A38", width=8)
    d.arc([x - 130, y - 280, x + 130, y + 60], 180, 360, fill="#C4A67C", width=14)


def _book_pile(d, x, y):
    for i, col in enumerate(("#C4453D", "#4E7A9E", "#E8A33D", "#5E8F4C")):
        rrect_box(d, x - 70 + i * 6, y - 40 - i * 34, x + 70 - i * 6, y - 8 - i * 34, col)


def rrect_box(d, x0, y0, x1, y1, fill):
    d.rounded_rectangle([x0, y0, x1, y1], radius=8, fill=fill, outline="#3A2A1E", width=4)


def _window(d, x, y):
    circle(d, x, y, 110, "#FFF3C8", ow=8, outline="#3A2A1E")
    d.line([(x - 110, y), (x + 110, y)], fill="#3A2A1E", width=8)
    d.line([(x, y - 110), (x, y + 110)], fill="#3A2A1E", width=8)
    d.arc([x - 130, y - 130, x + 130, y + 130], 0, 360, fill="#6B4A2E", width=14)


def _bookshelf(d, x, y):
    d.rounded_rectangle([x - 200, y - 100, x + 200, y + 640], radius=24, fill="#7A5A38",
                        outline="#3A2A1E", width=8)
    for row in range(4):
        ry = y + row * 160
        d.rectangle([x - 190, ry + 118, x + 190, ry + 138], fill="#3A2A1E")
        bx = x - 176
        i = 0
        while bx < x + 160:
            w = 26 + (bx * 13 % 20)
            h = 76 + (bx * 7 % 34)
            col = ("#C4453D", "#4E7A9E", "#E8A33D", "#5E8F4C", "#8A5A8E")[(bx + row * 3) % 5]
            d.rectangle([bx, ry + 130 - h, bx + w, ry + 130], fill=col, outline="#3A2A1E", width=3)
            bx += w + 8


def _tea_table(d, x, y):
    oval(d, x, y, 230, 70, "#A98A5B")
    capsule(d, (x, y + 40), (x, y + 150), 40, "#6B4A2E")
    oval(d, x - 60, y - 30, 46, 26, "#E8DCC8")
    capsule(d, (x - 106, y - 34), (x - 140, y - 34), 10, "#E8DCC8", ow=3)
    oval(d, x + 70, y - 26, 40, 22, "#F2E6C8")


def _rug(d, x, y):
    oval(d, x, y, 340, 90, "#C4453D")
    oval(d, x, y, 280, 66, "#E8DCC8")
    oval(d, x, y, 200, 44, "#C4453D")


def _armchair(d, x, y):
    d.rounded_rectangle([x - 150, y - 240, x + 150, y], radius=40, fill="#4E7A9E",
                        outline="#3A2A1E", width=8)
    d.rounded_rectangle([x - 190, y - 170, x - 110, y - 10], radius=30, fill="#3F6579",
                        outline="#3A2A1E", width=6)
    d.rounded_rectangle([x + 110, y - 170, x + 190, y - 10], radius=30, fill="#3F6579",
                        outline="#3A2A1E", width=6)


def _sky_only_wall(d, color):
    d.rectangle([0, 0, W, H], fill=color)


def _bridge(d, x, y):
    d.arc([x - 500, y - 160, x + 500, y + 440], 180, 360, fill="#8A6A45", width=70)
    for i in range(-440, 441, 70):
        t = abs(i) / 500
        py = y + 40 - 200 * (1 - t * t) ** 0.5 if t < 1 else y
        d.line([(x + i, py + 60), (x + i, py - 40)], fill="#6B4A2E", width=8)
    for sx in (-470, 470):
        capsule(d, (x + sx, y + 330), (x + sx, y - 120), 24, "#5A3D24")


def _moss_patch(d, x, y):
    oval(d, x, y, 90, 40, "#6FA35E")
    oval(d, x + 60, y + 20, 60, 28, "#5E8F4C")


def _mist(d, y):
    for x, w in ((100, 700), (900, 900), (1700, 700)):
        oval(d, x + w // 2, y, w // 2, 60, (255, 255, 255, 70))
        oval(d, x + w // 2, y + 70, w // 3, 44, (255, 255, 255, 55))


def _root_door(d, x, y):
    d.chord([x - 160, y - 420, x + 160, y + 40], 180, 360, fill="#5A4A3A")
    d.rectangle([x - 160, y - 190, x + 160, y + 40], fill="#5A4A3A")
    for i in range(x - 140, x + 141, 56):
        d.line([(i, y - 400), (i + 20, y + 40)], fill="#43372B", width=10)
    d.arc([x - 170, y - 440, x + 170, y + 60], 180, 360, fill="#3A2A1E", width=14)
    circle(d, x + 96, y - 60, 24, "#E8C84E", ow=5, outline="#3A2A1E")


def _heart_stone(d, x, y):
    oval(d, x, y, 96, 84, "#6E5E8E")
    d.line([(x - 30, y - 20), (x, y + 30), (x + 30, y - 20)], fill="#C9B8F0", width=10)
    circle(d, x - 24, y - 34, 16, "#E6DDFB", ow=0, outline="#E6DDFB")
    for ang in range(0, 360, 45):
        import math
        px = x + math.cos(math.radians(ang)) * 130
        py = y + math.sin(math.radians(ang)) * 110
        circle(d, px, py, 7, "#B8A8E8", ow=0, outline="#B8A8E8")


def _glow_vein(d, x, y, r):
    oval(d, x, y, r, r * 0.7, (140, 220, 240, 120))
    oval(d, x, y, r * 0.5, r * 0.35, (200, 245, 255, 160))
