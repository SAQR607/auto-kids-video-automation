"""Thumbnail: 1280x720 composite from the package thumbnail_concept."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

from .art.characters import get_sprite
from .scene import _font, _graded_layers, _text_fit


def render_thumbnail(cfg: dict, package: dict, out_path: Path,
                     size: tuple[int, int] = (1280, 720)) -> Path:
    w, h = size
    concept = package.get("thumbnail_concept") or (package.get("metadata") or {}).get("thumbnail_concept") or {}
    # package root may nest it under premise-echo fields
    if not concept:
        for key in ("thumbnail", "thumbnail_concept"):
            if isinstance(package.get(key), dict):
                concept = package[key]
    loc = concept.get("background", "hollow_oak_village")
    layers = _graded_layers(loc, "day")

    # cover-crop bg
    ar = w / h
    bw, bh = 2200, 1400
    if bw / bh > ar:
        ch = bh
        cw = ch * ar
    else:
        cw = bw
        ch = cw / ar
    rect = (int((bw - cw) / 2), int((bh - ch) / 2.6), int((bw - cw) / 2 + cw), int((bh - ch) / 2.6 + ch))
    bg = Image.new("RGBA", (w, h))
    for k in ("sky", "far", "mid", "near"):
        bg.alpha_composite(layers[k].crop(rect).resize((w, h), Image.BILINEAR))
    # readability vignette
    vig = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vig)
    for i in range(90):
        a = int(90 * (i / 90) ** 1.5)
        vd.rectangle([0, h - 90 + i, w, h - 90 + i + 1], fill=(20, 14, 10, a))
    bg.alpha_composite(vig)

    # characters
    chars = concept.get("characters", ["juni"])[:2]
    expr = concept.get("expression", "excited")
    scale = (h * 0.62) / 760.0
    xs = [0.30, 0.70] if len(chars) > 1 else [0.50]
    order = sorted(range(len(chars)), key=lambda i: -i)
    for i, cid in zip(order, chars):
        sp = get_sprite(cid, "happy", expr)
        cw2, chh = int(sp.width * scale), int(sp.height * scale)
        sprite = sp.resize((cw2, chh), Image.BILINEAR)
        x = int(xs[i] * w - cw2 / 2)
        y = h - chh - int(h * 0.02)
        sh = Image.new("RGBA", (int(cw2 * 0.7), int(chh * 0.09)), (58, 42, 30, 70))
        bg.alpha_composite(sh, (x + int(cw2 * 0.15), h - int(chh * 0.05)))
        bg.alpha_composite(sprite, (x, y))

    # text panel
    text = (concept.get("text") or package.get("title", "Fernwood Friends")).upper()
    d = ImageDraw.Draw(bg)
    font = _font(int(h * 0.13))
    text = _text_fit(d, text, font, int(w * 0.92))
    tb = d.textbbox((0, 0), text, font=font)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    panel_w, panel_h = tw + 70, th + 44
    px = int((w - panel_w) / 2)
    py = int(h * 0.055)
    panel = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    pd = ImageDraw.Draw(panel)
    pd.rounded_rectangle([px, py, px + panel_w, py + panel_h], radius=26,
                         fill=(255, 246, 230, 238), outline=(58, 42, 30, 255), width=6)
    bg.alpha_composite(panel)
    d = ImageDraw.Draw(bg)
    d.text((px + 35 - tb[0], py + 22 - tb[1]), text, font=font, fill=(58, 42, 30, 255))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    bg.convert("RGB").save(out_path, quality=92)
    return out_path
