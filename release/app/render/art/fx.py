"""FX overlays for scene frames (drawn live, no asset files)."""

from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw

FX = (
    "glimmer_sparkle", "leaf_swirl", "rain_streak", "ripple_ring",
    "dust_motes", "lamp_glow", "speech_pop", "endcard_wave",
)


def draw_fx(img: Image.Image, fx_ids: list[str], t: float, seed: int = 0) -> None:
    """Paint animated FX onto an RGB(A) frame. t = seconds into the scene."""
    d = ImageDraw.Draw(img, "RGBA")
    for fx in fx_ids or []:
        if fx == "glimmer_sparkle":
            rnd = random.Random(seed)
            for i in range(14):
                x = rnd.uniform(0, img.width)
                y = rnd.uniform(0, img.height * 0.7)
                ph = (t * 0.7 + rnd.random()) % 1.0
                a = int(160 * math.sin(ph * math.pi))
                r = 3 + 4 * math.sin(ph * math.pi)
                if r > 0:
                    d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 250, 200, max(0, a)))
        elif fx == "leaf_swirl":
            rnd = random.Random(seed + 1)
            for i in range(8):
                base_x = (rnd.uniform(0, img.width) + t * 90) % (img.width + 120) - 60
                base_y = rnd.uniform(img.height * 0.2, img.height * 0.8)
                wob = math.sin(t * 3 + i) * 30
                d.ellipse([base_x, base_y + wob, base_x + 18, base_y + wob + 10],
                          fill=(94, 143, 76, 200))
        elif fx == "rain_streak":
            rnd = random.Random(seed + 2)
            for i in range(40):
                x = rnd.uniform(0, img.width)
                off = (t * 700 + rnd.uniform(0, img.height)) % (img.height + 100) - 50
                d.line([(x, off), (x - 8, off + 40)], fill=(174, 210, 235, 150), width=3)
        elif fx == "ripple_ring":
            for i in range(3):
                ph = (t * 0.5 + i / 3) % 1.0
                r = 30 + ph * 160
                a = int(150 * (1 - ph))
                cx, cy = img.width // 2, int(img.height * 0.72)
                d.ellipse([cx - r, cy - r * 0.35, cx + r, cy + r * 0.35],
                          outline=(255, 255, 255, max(0, a)), width=5)
        elif fx == "dust_motes":
            rnd = random.Random(seed + 3)
            for i in range(24):
                x = rnd.uniform(0, img.width)
                y = (rnd.uniform(0, img.height) - t * 20) % img.height
                r = rnd.uniform(2, 5)
                a = int(70 + 50 * math.sin(t * 2 + i))
                d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 250, 230, max(20, a)))
        elif fx == "lamp_glow":
            for cx, cy in ((int(img.width * 0.18), int(img.height * 0.35)),
                           (int(img.width * 0.82), int(img.height * 0.35))):
                for r, a in ((160, 26), (110, 40), (66, 60)):
                    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 226, 150, a))
        elif fx == "speech_pop":
            cx, cy = int(img.width * 0.72), int(img.height * 0.3)
            ph = min(1.0, (t % 4) / 0.4) if t < 4 else 1.0
            if ph > 0:
                r = int(70 * ph)
                d.ellipse([cx - r, cy - r * 0.8, cx + r, cy + r * 0.8],
                          fill=(255, 255, 255, 235), outline=(58, 42, 30, 255), width=5)
                d.polygon([(cx - r // 2, cy + r * 0.6), (cx - r // 4, cy + r * 1.3),
                           (cx + r // 6, cy + r * 0.7)], fill=(255, 255, 255, 235))
                for i, ox in enumerate((-r // 3, 0, r // 3)):
                    d.ellipse([cx + ox - 7, cy - 7, cx + ox + 7, cy + 7],
                              fill=(58, 42, 30, 255))
        elif fx == "endcard_wave":
            cx, cy = int(img.width * 0.5), int(img.height * 0.5)
            d.ellipse([cx - 260, cy - 150, cx + 260, cy + 150],
                      fill=(255, 255, 255, 220), outline=(58, 42, 30, 255), width=8)
            a = math.sin(t * 4) * 18
            d.line([(cx - 40, cy - 10), (cx + 40 + a, cy - 30)], fill=(58, 42, 30, 255), width=8)
