"""Thumbnail: 1280x720 close-up composite from the package thumbnail_concept."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .art.characters import get_sprite
from .art.props import get_prop
from .scene import _font, _graded_layers, _text_fit

# title-trim keeps the nouns; short function words only
_STOP = frozenset("a an the of to in on and or is are was were with for at by "
                  "from that this it its his her their as be into over under "
                  "but not so up out".split())


def story_concept(package: dict, cfg: dict | None = None) -> dict:
    """Derive a story-relevant thumbnail concept from the opening scene.

    Used when the package has no LLM thumbnail_concept: the opening scene's
    location and cast keep the thumbnail tied to THIS story instead of the
    generic defaults (fixed village background, single character).
    """
    def _cget(key: str, default: str) -> str:
        try:
            return str(cfg.get(key, default)) if cfg is not None else default
        except Exception:
            return default

    scenes = package.get("scenes") or []
    s0 = scenes[0] if scenes and isinstance(scenes[0], dict) else {}
    chars = [c.get("id") for c in (s0.get("characters") or [])
             if isinstance(c, dict) and c.get("id")]
    return {
        "background": s0.get("location") or _cget("channel.default_location", "hollow_oak_village"),
        "characters": (chars or [_cget("channel.default_character", "juni")])[:2],
        "expression": "excited",
        "text": package.get("title") or _cget("channel.name", "Fernwood Friends"),
    }


def _thumb_text(package: dict, concept: dict, cfg) -> str:
    """Thumbnail line = episode title trimmed to <=4 words (no LLM call)."""
    words = []
    for wd in str(package.get("title") or "").replace("|", " ").split():
        wd = wd.strip("?!.,'\":;—")
        if wd and wd.lower() not in _STOP:
            words.append(wd)
        if len(words) >= 4:
            break
    if len(words) >= 2:
        return " ".join(words)
    return str(concept.get("text") or cfg.get("channel.name", "Fernwood Friends"))


def render_thumbnail(cfg: dict, package: dict, out_path: Path,
                     size: tuple[int, int] = (1280, 720)) -> Path:
    w, h = size
    concept = package.get("thumbnail_concept") or (package.get("metadata") or {}).get("thumbnail_concept") or {}
    # package root may nest it under premise-echo fields
    if not concept:
        for key in ("thumbnail", "thumbnail_concept"):
            if isinstance(package.get(key), dict):
                concept = package[key]
    if not concept:
        concept = story_concept(package, cfg)
    loc = concept.get("background") or str(cfg.get("channel.default_location", "hollow_oak_village"))
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

    # close-up faces, bottom-anchored (the cut edge sits on the frame edge).
    # One shared scale for every face — per-face rescaling made heads differ.
    chars = concept.get("characters") or [str(cfg.get("channel.default_character", "juni"))]
    chars = chars[:2]
    expr = concept.get("expression", "excited")
    xs = [0.34, 0.66] if len(chars) > 1 else [0.50]
    target = int(h * (0.58 if len(chars) > 1 else 0.70))
    faces = []
    for cid in chars:
        sp = get_sprite(cid, "idle", expr)
        s = target / (sp.height * 0.64)
        big = sp.resize((max(1, round(sp.width * s)), max(1, round(sp.height * s))),
                        Image.LANCZOS)
        crop = big.crop((0, 0, big.width, int(big.height * 0.64)))
        bb = crop.getchannel("A").getbbox()
        faces.append(crop.crop(bb) if bb else crop)
    # shadows first so no shadow lands on a drawn face
    for i, sprite in enumerate(faces):
        x = int(xs[i] * w - sprite.width / 2)
        sh = Image.new("RGBA", (int(sprite.width * 0.7), int(sprite.height * 0.10)),
                       (58, 42, 30, 70))
        bg.alpha_composite(sh, (x + int(sprite.width * 0.15), h - int(sprite.height * 0.05)))
    for i in sorted(range(len(faces)), key=lambda i: -i):
        sprite = faces[i]
        x = int(xs[i] * w - sprite.width / 2)
        bg.alpha_composite(sprite, (x, h - sprite.height))

    # story prop from the opening scene, bottom-left on the vignette
    scenes = package.get("scenes") or []
    s0 = scenes[0] if scenes and isinstance(scenes[0], dict) else {}
    plist = s0.get("props")
    pid = next((p for p in plist if isinstance(p, str)), None) if isinstance(plist, list) else None
    if pid:
        pr = get_prop(pid)
        bb = pr.getchannel("A").getbbox()
        if bb:
            pr = pr.crop(bb)
        s = int(h * 0.20) / max(pr.size)
        pr = pr.resize((max(1, int(pr.width * s)), max(1, int(pr.height * s))), Image.LANCZOS)
        bg.alpha_composite(pr, (int(w * 0.03), h - pr.height - int(h * 0.03)))

    # bold high-contrast title text: shrink-to-fit one line, thick dark stroke
    text = _thumb_text(package, concept, cfg).upper()
    d = ImageDraw.Draw(bg)
    fs = int(h * 0.15)
    font = _font(fs)
    while fs > h * 0.09 and d.textlength(text, font=font) > w * 0.90:
        fs = int(fs * 0.93)
        font = _font(fs)
    text = _text_fit(d, text, font, int(w * 0.90))
    sw = max(4, int(fs * 0.14))
    tb = d.multiline_textbbox((0, 0), text, font=font, stroke_width=sw, align="center")
    d.multiline_text((w / 2 - (tb[0] + tb[2]) / 2, h * 0.045 - tb[1]), text,
                     font=font, fill=(255, 226, 66), stroke_width=sw,
                     stroke_fill=(30, 20, 12), align="center",
                     spacing=int(h * 0.015))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    bg.convert("RGB").save(out_path, quality=92)
    return out_path
