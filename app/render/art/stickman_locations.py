"""Stickman profile locations: 6 era-neutral storybook-history settings.

Contract mirrors art/locations.py: paint_location(loc_id, tod) ->
{"sky","far","mid","near"} each RGBA 2200x1400. Muted, parchment-friendly
palette; the renderer applies its global time-of-day grade on top.
"""

from __future__ import annotations

from PIL import Image, ImageDraw

from .shapes import capsule, circle, new_layer, oval, poly

W, H = 2200, 1400

SKIES = {
    "day": ("#A8CBE0", "#DCEBF2"),
    "morning": ("#E8CBA6", "#F6E8D4"),
    "dusk": ("#D9A882", "#EFD8BC"),
    "night": ("#26364F", "#3E5372"),
}

LOCATIONS = (
    "village_lane", "market_square", "river_dock",
    "workshop_street", "hall_of_columns", "hilltop_road",
)

INK = "#2A2622"


# ------------------------------------------------------------------ sky ----

def _sky(d: ImageDraw.ImageDraw, tod: str) -> None:
    top, bot = SKIES.get(tod, SKIES["day"])
    for i in range(H):
        t = i / H
        d.line([(0, i), (W, i)], fill=_lerp(top, bot, t))
    if tod == "night":
        for x, y, r in ((300, 170, 4), (760, 110, 3), (1250, 210, 5), (1830, 140, 3),
                        (2050, 300, 4), (520, 320, 3)):
            circle(d, x, y, r, "#FFF8D8", ow=0, outline="#FFF8D8")
        circle(d, 1850, 210, 78, "#F2ECCE", ow=0, outline="#F2ECCE")
        circle(d, 1884, 186, 66, SKIES["night"][0], ow=0, outline=SKIES["night"][0])
    else:
        sx, sy = {"day": (1740, 210), "morning": (470, 300), "dusk": (1690, 330)}[tod]
        glow = {"day": "#FFF6C8", "morning": "#FFE9B8", "dusk": "#FFD9A8"}[tod]
        circle(d, sx, sy, 92, glow, ow=0, outline=glow)
        circle(d, sx, sy, 64, "#FFFBE8", ow=0, outline="#FFFBE8")
        cc = "#FFFFFF" if tod != "dusk" else "#F2DEC8"
        for cx, cy, s in ((360, 240, 1.0), (1100, 150, 0.75), (1750, 430, 0.8)):
            for ox, oy, rx, ry in ((0, 0, 88, 42), (-68, 14, 60, 30), (72, 12, 56, 28)):
                oval(d, cx + ox * s, cy + oy * s, rx * s, ry * s, cc)


def _lerp(a: str, b: str, t: float) -> tuple[int, int, int, int]:
    ca = tuple(int(a[i:i + 2], 16) for i in (1, 3, 5))
    cb = tuple(int(b[i:i + 2], 16) for i in (1, 3, 5))
    return tuple(int(ca[i] + (cb[i] - ca[i]) * t) for i in range(3)) + (255,)


# --------------------------------------------------------------- shared ----

def _hills(d, c1, c2):
    d.polygon([(0, 760), (420, 600), (900, 730), (1420, 590), (1900, 720), (2200, 650),
               (2200, 1400), (0, 1400)], fill=c1)
    d.polygon([(0, 890), (520, 760), (1120, 880), (1720, 750), (2200, 860),
               (2200, 1400), (0, 1400)], fill=c2)


def _ground(d, y, color):
    d.rectangle([0, y, W, H], fill=color)


def _tree(d, x, y, s, trunk="#7A5A3C", leaf="#7E9A5E"):
    capsule(d, (x, y), (x, y - 140 * s), 30 * s, trunk)
    for ox, oy, r in ((0, -200, 100), (-80, -150, 70), (80, -150, 70), (0, -275, 66)):
        circle(d, x + ox * s, y + oy * s, r * s, leaf)


def _house(d, x, y, wall, roof, door="#5A4331"):
    d.polygon([(x - 105, y), (x - 86, y - 150), (x + 86, y - 150), (x + 105, y)], fill=wall)
    d.polygon([(x - 128, y - 140), (x, y - 258), (x + 128, y - 140)], fill=roof)
    d.rectangle([x - 28, y - 72, x + 28, y], fill=door)
    circle(d, x - 66, y - 102, 20, "#F4E8C8", ow=4, outline=INK)
    circle(d, x + 66, y - 102, 20, "#F4E8C8", ow=4, outline=INK)


def _banner(d, x, y, w, col="#B4553F"):
    capsule(d, (x, y), (x, y + 300), 8, INK, ow=3)
    d.polygon([(x + 8, y), (x + w, y + 20), (x + w, y + 210), (x + 8, y + 230)], fill=col)
    circle(d, x + w // 2, y + 110, 34, "#E8D9A8", ow=4, outline=INK)


def _wheel(d, x, y, r):
    circle(d, x, y, r, "#9A7A52", ow=8, outline=INK)
    circle(d, x, y, r * 0.22, "#7A5A3C", ow=4, outline=INK)
    for ang in (0, 45, 90, 135):
        import math
        rad = math.radians(ang)
        d.line([(x - math.cos(rad) * r, y - math.sin(rad) * r),
                (x + math.cos(rad) * r, y + math.sin(rad) * r)], fill=INK, width=7)


# ------------------------------------------------------------- painters ----

def paint_location(loc_id: str, tod: str = "day") -> dict[str, Image.Image]:
    sky, ds = new_layer((W, H))
    far, df = new_layer((W, H))
    mid, dm = new_layer((W, H))
    near, dn = new_layer((W, H))
    _sky(ds, tod)

    if loc_id == "village_lane":
        _hills(df, "#A5B98A", "#93A87A")
        _tree(df, 170, 880, 0.85)
        _tree(df, 2060, 860, 0.75)
        _ground(dm, 880, "#C9B48C")
        _house(dm, 480, 940, "#E4D3AC", "#A96F4A")
        _house(dm, 1100, 970, "#DCC9A2", "#96613F")
        _house(dm, 1740, 950, "#E7D6B0", "#A96F4A")
        d = dm
        d.polygon([(760, 1400), (980, 990), (1220, 990), (1440, 1400)], fill="#C0A97E")
        for x in (300, 1560, 1980):
            _tree(dm, x, 940, 0.55, leaf="#8AA066")
        _grass(dn, 1270, "#A08C62")
        for x in (240, 980, 1720):
            circle(dn, x, 1330, 14, "#C4756B", ow=4, outline=INK)
            circle(dn, x + 60, 1360, 12, "#D9B45C", ow=4, outline=INK)

    elif loc_id == "market_square":
        _hills(df, "#AABD90", "#98AC80")
        df.rectangle([0, 0, W, 600], fill=(0, 0, 0, 0))
        _ground(dm, 860, "#CBB68E")
        for x, col in ((420, "#B4553F"), (1100, "#4E7A9E"), (1780, "#7E9A5E")):
            _stall(dm, x, 960, col)
        _banner(dm, 2050, 420, 120, "#B4553F")
        _banner(dm, 130, 460, 110, "#4E7A9E")
        d = dm
        d.rectangle([0, 860, W, 900], fill="#B7A077")
        for x in (760, 1440):
            capsule(d, (x, 860), (x, 620), 26, "#E7D9BC")
            d.rectangle([x - 44, 590, x + 44, 630], fill="#E7D9BC")
        _grass(dn, 1300, "#A08C62")
        for x in (560, 1300, 2040):
            oval(dn, x, 1350, 60, 26, "#9A7A52")

    elif loc_id == "river_dock":
        _hills(df, "#9DB69A", "#8CA68A")
        for x, y, s in ((300, 840, 0.8), (1880, 820, 0.9), (1480, 700, 0.6)):
            _tree(df, x, y, s, leaf="#7E9A66")
        d = dm
        d.rectangle([0, 780, W, H], fill="#7FA8B8")
        for y in (840, 940, 1060, 1190, 1320):
            d.arc([100, y - 30, 520, y + 60], 190, 350, fill="#A8CCD6", width=9)
            d.arc([1100, y - 20, 1560, y + 70], 190, 350, fill="#A8CCD6", width=9)
        _boat(dm, 1360, 900, 1.0)
        for x in (240, 460, 680):
            capsule(d, (x, 980), (x, 1140), 24, "#7A5A3C")
        d2 = dn
        d2.rectangle([0, 1040, 860, 1130], fill="#9A7A52")
        d2.rectangle([0, 1040, 860, 1064], fill="#B08C60")
        for x in (90, 330, 570, 810):
            capsule(d2, (x, 1064), (x, 1210), 16, "#7A5A3C")

    elif loc_id == "workshop_street":
        _hills(df, "#A2B489", "#90A477")
        _ground(dm, 870, "#C6B086")
        d = dm
        # workshop shed with chimney
        d.rectangle([180, 560, 900, 900], fill="#D8C49C")
        d.polygon([(140, 580), (540, 420), (940, 580)], fill="#8E6247")
        d.rectangle([760, 330, 850, 470], fill="#A08666")
        d.rectangle([260, 700, 420, 900], fill="#5A4331")
        d.rectangle([520, 640, 660, 760], fill="#F4E8C8")
        # anvil block + forge glow
        d.rectangle([1060, 780, 1340, 900], fill="#8A8074")
        d.polygon([(1040, 740), (1360, 740), (1330, 790), (1070, 790)], fill="#6E665C")
        circle(d, 1200, 846, 46, "#E8A33D", ow=5, outline=INK)
        # second shed
        d.rectangle([1560, 600, 2140, 900], fill="#CFBA92")
        d.polygon([(1520, 620), (1850, 470), (2180, 620)], fill="#96684B")
        d.rectangle([1780, 720, 1900, 900], fill="#5A4331")
        _wheel(dn, 420, 1240, 96)
        _grass(dn, 1290, "#A08C62")
        for x in (1460, 2080):
            capsule(dn, (x, 1400), (x, 1210), 14, "#7A5A3C")
            oval(dn, x, 1190, 30, 46, "#9A7A52")

    elif loc_id == "hall_of_columns":
        d0 = df
        d0.rectangle([0, 0, W, H], fill="#E2D4B4")
        d0.rectangle([0, 940, W, H], fill="#CDBB96")
        for i in range(-60, W + 60, 340):
            d0.line([(i, 0), (i + 60, H)], fill="#D6C7A6", width=10)
        d = dm
        for x in (320, 900, 1480, 2060):
            capsule(d, (x, 980), (x, 300), 74, "#EFE4CA")
            d.rectangle([x - 58, 260, x + 58, 330], fill="#EFE4CA")
            d.rectangle([x - 66, 950, x + 66, 1010], fill="#E0D2B2")
        _banner(dm, 1190, 330, 150, "#B4553F")
        _banner(dm, 30, 360, 120, "#4E7A9E")
        d2 = dn
        d2.rectangle([0, 1320, W, H], fill="#BFAA82")
        d2.polygon([(760, 1400), (1440, 1400), (1330, 1330), (870, 1330)], fill="#A08C62")
        oval(dn, 1100, 1360, 210, 46, "#9A7A52")

    elif loc_id == "hilltop_road":
        _hills(df, "#A8BC8E", "#96AA7C")
        df.polygon([(1500, 700), (1560, 640), (1620, 660), (1680, 620), (1740, 650),
                    (1800, 630), (1860, 670), (1860, 720), (1500, 720)], fill="#B7C3A4")
        for x, s in ((330, 0.7), (760, 0.55), (2050, 0.65)):
            _tree(df, x, 840, s)
        d = dm
        d.polygon([(0, 1400), (0, 980), (420, 900), (900, 960), (1400, 890),
                   (1900, 950), (2200, 900), (2200, 1400)], fill="#C7B189")
        d.polygon([(620, 1400), (1060, 960), (1240, 970), (1500, 1400)], fill="#D8C6A0")
        d.polygon([(760, 1240), (1030, 1050), (1130, 1060), (1210, 1250)], fill="#C7B189")
        _house(dm, 1900, 950, "#E4D3AC", "#A96F4A")
        _grass(dn, 1310, "#A08C62")
        for x in (300, 1700, 2100):
            capsule(dn, (x, 1400), (x, 1220), 12, "#7A5A3C")
            circle(dn, x, 1200, 26, "#8AA066", ow=4, outline=INK)

    return {"sky": sky, "far": far, "mid": mid, "near": near}


# --------------------------------------------------------- sub-painters ----

def _grass(d, y, color):
    for x in range(0, W, 34):
        h = 24 + (x * 7919 % 18)
        d.line([(x, y), (x + 8, y - h)], fill=color, width=6)


def _stall(d, x, y, col):
    d.polygon([(x - 170, y - 240), (x + 170, y - 240), (x + 140, y - 150), (x - 140, y - 150)],
              fill=col)
    for sx in (x - 160, x + 160):
        capsule(d, (sx, y), (sx, y - 250), 14, "#7A5A3C")
    d.rectangle([x - 150, y - 60, x + 150, y], fill="#9A7A52")
    d.rectangle([x - 150, y - 76, x + 150, y - 60], fill="#B08C60")
    for ox, col2 in ((-90, "#C4756B"), (0, "#D9B45C"), (90, "#8AA066")):
        oval(d, x + ox, y - 96, 34, 26, col2)


def _boat(d, x, y, s):
    d.polygon([(x - 200 * s, y), (x + 200 * s, y), (x + 150 * s, y + 80 * s),
               (x - 150 * s, y + 80 * s)], fill="#9A7A52")
    capsule(d, (x, y), (x, y - 240 * s), 14 * s, "#7A5A3C")
    poly(d, [(x + 10 * s, y - 230 * s), (x + 170 * s, y - 60 * s), (x + 10 * s, y - 60 * s)],
         "#EFE4CA")
