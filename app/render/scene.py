"""Scene compositor: one RGB frame per (scene, t).

Performance contract (weekly ~12k frames): backgrounds are pre-composited and
cached per quantized camera rect; sprites/props are paste+mask on RGB; full-frame
alpha ops are avoided. Target <= ~80 ms/frame on a 4-core CPU.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .art.fx import draw_fx
from .art.locations import paint_location
from .art.props import get_prop
from .art.characters import get_sprite

_TOD_TINT = {  # per-channel RGB multiply + add (alpha untouched)
    "day": None,
    "morning": ((1.05, 1.00, 0.92), (6, 4, 0)),
    "dusk": ((1.06, 0.86, 0.72), (8, 0, 0)),
    "night": ((0.55, 0.62, 0.92), (8, 12, 34)),
}

_POSITION_X = {"far_left": 0.15, "left": 0.28, "center": 0.50, "right": 0.72, "far_right": 0.85}
_PROP_ANCHORS = [(0.17, 0.885), (0.50, 0.905), (0.83, 0.885), (0.32, 0.925), (0.68, 0.925)]
_PARALLAX = {"sky": 0.35, "far": 0.55, "mid": 1.0, "near": 1.12}

_LAYERS_CACHE: dict[tuple[str, str], dict[str, Image.Image]] = {}
_BG_CACHE: dict[tuple, Image.Image] = {}
_SPRITE_CACHE: dict[tuple, Image.Image] = {}
_FONT_CACHE: dict[int, ImageFont.FreeTypeFont] = {}
_MASK_CACHE: dict[int, Image.Image] = {}
_OVERLAY_CACHE: dict[tuple, Image.Image] = {}


def graded_layers(loc_id: str, tod: str) -> dict[str, Image.Image]:
    key = (loc_id, tod)
    got = _LAYERS_CACHE.get(key)
    if got is None:
        layers = paint_location(loc_id, tod)
        tint = _TOD_TINT.get(tod)
        if tint is not None:
            mul, add = tint
            for k, im in layers.items():
                arr = np.asarray(im).copy()
                rgb = arr[..., :3].astype(np.float32)
                rgb = rgb * np.array(mul, dtype=np.float32) + np.array(add, dtype=np.float32)
                arr[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
                layers[k] = Image.fromarray(arr, "RGBA")
        got = layers
        _LAYERS_CACHE[key] = got
    return got


# back-compat alias used by thumbnail.py
_graded_layers = graded_layers


def _view_rect(cam: str, p: float, vw: int, vh: int, bg_w: int, bg_h: int,
               layer_k: float) -> tuple[int, int, int, int]:
    ar = vw / vh
    if bg_w / bg_h > ar:
        h = bg_h
        w = h * ar
    else:
        w = bg_w
        h = w / ar
    z = 1.0
    dx = dy = 0.0
    if cam == "push_in":
        z = 1.0 + 0.10 * p
    elif cam == "pull_out":
        z = 1.10 - 0.10 * p
    elif cam == "pan_l":
        dx = (0.5 - p) * 150
    elif cam == "pan_r":
        dx = (p - 0.5) * 150
    elif cam == "drift":
        import math

        dx = 46 * math.sin(p * math.pi)
        dy = 20 * math.sin(p * math.pi * 2)
    dx *= layer_k
    dy *= layer_k
    w /= z
    h /= z
    cx, cy = bg_w / 2 + dx, bg_h / 2 + dy
    x0 = max(0, min(bg_w - w, cx - w / 2))
    y0 = max(0, min(bg_h - h, cy - h / 2))
    return int(x0), int(y0), int(x0 + w), int(y0 + h)


def _composed_bg(loc_id: str, tod: str, cam: str, p: float, w: int, h: int) -> Image.Image:
    """RGB background for this camera position (rect-quantized cache)."""
    rects = {}
    for k, par in _PARALLAX.items():
        r = _view_rect(cam, p, w, h, 2200, 1400, par)
        rects[k] = (r[0] // 8, r[1] // 8, r[2] // 8, r[3] // 8)
    key = (loc_id, tod, w, h, tuple(rects.items()))
    got = _BG_CACHE.get(key)
    if got is None:
        layers = graded_layers(loc_id, tod)
        base = None
        for k in ("sky", "far", "mid", "near"):
            r = _view_rect(cam, p, w, h, 2200, 1400, _PARALLAX[k])
            piece = layers[k].crop(r).resize((w, h), Image.BILINEAR)
            if base is None:
                base = piece.convert("RGB")
            else:
                base.paste(piece, (0, 0), piece)
        got = base
        if len(_BG_CACHE) >= 32:
            _BG_CACHE.pop(next(iter(_BG_CACHE)))
        _BG_CACHE[key] = got
    return got


def font(size: int) -> ImageFont.FreeTypeFont:
    f = _FONT_CACHE.get(size)
    if f is None:
        for cand in ("C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/segoeuib.ttf",
                     "C:/Windows/Fonts/tahomabd.ttf", "C:/Windows/Fonts/arial.ttf"):
            if Path(cand).exists():
                f = ImageFont.truetype(cand, size)
                break
        if f is None:
            f = ImageFont.load_default(size)
        _FONT_CACHE[size] = f
    return f


_font = font  # back-compat


def _ease_out(p: float) -> float:
    p = max(0.0, min(1.0, p))
    return 1 - (1 - p) ** 3


def _black_mask(size: tuple[int, int], alpha: int) -> Image.Image:
    a = max(0, min(255, (alpha // 8) * 8))
    key = ("blk", size, a)
    got = _MASK_CACHE.get(key)
    if got is None:
        got = Image.new("L", size, a)
        if len(_MASK_CACHE) > 80:
            _MASK_CACHE.pop(next(iter(_MASK_CACHE)))
        _MASK_CACHE[key] = got
    return got


_FULLBLACK: dict[tuple, Image.Image] = {}


def _black_image(size: tuple[int, int]) -> Image.Image:
    got = _FULLBLACK.get(size)
    if got is None:
        got = Image.new("RGB", size, (0, 0, 0))
        _FULLBLACK[size] = got
    return got


def _wipe_mask(p: float, size: tuple[int, int]) -> Image.Image:
    step = max(0, min(23, int(p * 24)))
    key = ("w", step, size)
    got = _MASK_CACHE.get(key)
    if got is None:
        w, h = size
        xs = np.linspace(0, 1, w, dtype=np.float32)
        edge = (step + 1) / 24 * 1.25
        col = np.clip((edge - xs) * 4, 0, 1)
        arr = np.zeros((h, w), dtype=np.uint8)
        arr[:] = (col[None, :] * 255).astype(np.uint8)
        got = Image.fromarray(arr, "L")
        _MASK_CACHE[key] = got
    return got


def _text_fit(draw: ImageDraw.ImageDraw, text: str, fnt, max_w: int) -> str:
    if draw.textlength(text, font=fnt) <= max_w:
        return text
    words = text.split()
    line, out = "", []
    for wd in words:
        trial = (line + " " + wd).strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            line = trial
        else:
            out.append(line)
            line = wd
    if line:
        out.append(line)
    return "\n".join(out)


def _title_overlay(package_title: str, episode_label: str, w: int, h: int) -> Image.Image:
    """RGBA title panel (full alpha), alpha-scaled at composite time."""
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    panel_w, panel_h = int(w * 0.78), int(h * 0.30)
    px, py = int(w * 0.11), int(h * 0.60)
    d.rounded_rectangle([px, py, px + panel_w, py + panel_h], radius=28,
                        fill=(30, 22, 16, 170))
    title_font = font(int(h * 0.062))
    sub_font = font(int(h * 0.034))
    txt = _text_fit(d, package_title, title_font, int(w * 0.70))
    tb = d.multiline_textbbox((0, 0), txt, font=title_font, spacing=6)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    tx = int(w * 0.5 - tw / 2)
    ty = py + int((panel_h - th - 40) / 2)
    d.multiline_text((tx, ty), txt, font=title_font, fill=(255, 244, 224, 255),
                     spacing=6, align="center")
    sub = episode_label or "Fernwood Friends"
    sw = d.textlength(sub, font=sub_font)
    d.text((w * 0.5 - sw / 2, ty + th + 22), sub, font=sub_font, fill=(255, 214, 150, 255))
    return ov


def _end_overlay(w: int, h: int) -> Image.Image:
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    panel_w, panel_h = int(w * 0.66), int(h * 0.34)
    px, py = int(w * 0.17), int(h * 0.52)
    d.rounded_rectangle([px, py, px + panel_w, py + panel_h], radius=30,
                        fill=(255, 250, 240, 236), outline=(58, 42, 30, 255), width=6)
    h1 = font(int(h * 0.070))
    h2 = font(int(h * 0.036))
    l1 = "Fernwood Friends"
    w1 = d.textlength(l1, font=h1)
    d.text((w * 0.5 - w1 / 2, h * 0.565), l1, font=h1, fill=(58, 42, 30, 255))
    l2 = "New stories Monday, Wednesday & Friday"
    w2 = d.textlength(l2, font=h2)
    d.text((w * 0.5 - w2 / 2, h * 0.665), l2, font=h2, fill=(120, 90, 60, 255))
    return ov


def _scale_overlay(ov: Image.Image, alpha: int) -> Image.Image:
    """Quantized-alpha variant of an RGBA overlay (cached)."""
    a = max(0, min(24, alpha // 11))
    if a >= 24:
        return ov
    key = ("ov", id(ov), a)
    got = _OVERLAY_CACHE.get(key)
    if got is None:
        chan = ov.getchannel("A").point(lambda v: v * a // 24)
        got = ov.copy()
        got.putalpha(chan)
        if len(_OVERLAY_CACHE) > 64:
            _OVERLAY_CACHE.clear()
        _OVERLAY_CACHE[key] = got
    return got


def _sprite_sized(char_id: str, state: str, expr: str, frame: int, scale: float) -> Image.Image:
    sp0 = get_sprite(char_id, state, expr, frame)
    size = (max(1, int(sp0.width * scale)), max(1, int(sp0.height * scale)))
    key = (char_id, state, expr, frame, size)
    got = _SPRITE_CACHE.get(key)
    if got is None:
        got = sp0.resize(size, Image.BILINEAR)
        if len(_SPRITE_CACHE) > 400:
            _SPRITE_CACHE.clear()
        _SPRITE_CACHE[key] = got
    return got


def _active_line(lines: list[dict], t: float, speaker: str) -> dict | None:
    for ln in lines or []:
        if ln.get("speaker") == speaker and ln["start"] <= t < ln["end"]:
            return ln
    return None


def _char_state_expr(char_id: str, entry: dict, lines: list[dict], t: float) -> tuple[str, str]:
    base_state = entry.get("state", "idle")
    active = _active_line(lines, t, char_id)
    if active is not None:
        phase = int((t - active["start"]) * 8) % 4
        state = ("talk_open", "talk_mid", "talk_closed", "talk_mid")[phase]
        return state, active.get("emotion") or "neutral"
    expr = "neutral"
    for ln in lines or []:
        if ln.get("speaker") == char_id and ln["end"] <= t:
            expr = ln.get("emotion") or expr
    return base_state, expr


def render_frame(scene: dict, t: float, scene_dur: float, cfg: dict, *,
                 frame_w: int, frame_h: int, frame_no: int = 0,
                 lines: list[dict] | None = None, scene_index: int = 0,
                 scene_count: int = 14, package_title: str = "",
                 episode_label: str = "") -> Image.Image:
    loc_id = scene.get("location", "hollow_oak_village")
    tod = scene.get("time_of_day", "day")
    cam = scene.get("camera", "static")
    p = max(0.0, min(1.0, t / max(0.5, scene_dur)))
    lines = lines or []
    has_fx = bool(scene.get("fx"))

    frame = _composed_bg(loc_id, tod, cam, p, frame_w, frame_h).copy()

    # --- characters
    entries = scene.get("characters", [])
    if entries:
        base_scale = (0.40 * frame_h) / 760.0
        ground = frame_h * 0.90
        used: list[float] = []
        for ch in entries:
            cid = ch.get("id", "juni")
            xpos = _POSITION_X.get(ch.get("position", "center"), 0.5)
            if any(abs(xpos - v) < 0.01 for v in used):
                xpos = min(0.9, xpos + 0.12)
            used.append(xpos)
            state, expr = _char_state_expr(cid, ch, lines, t)
            fno = frame_no % 4 if state in ("walk", "run") else 0
            scale = base_scale * (1.05 if str(ch.get("position", "")).startswith("far_") else 1.0)
            sp = _sprite_sized(cid, state, expr, fno, scale)
            x = int(xpos * frame_w - sp.width / 2)
            ent = ch.get("enter", "onscreen")
            if ent == "enter_left":
                x -= int((1 - _ease_out(t / 0.9)) * (frame_w * 0.6))
            elif ent == "enter_right":
                x += int((1 - _ease_out(t / 0.9)) * (frame_w * 0.6))
            y = int(ground - sp.height)
            # ground shadow (small ellipse, cheap)
            sh_w = int(sp.width * 0.66)
            sh_h = max(6, int(sp.height * 0.075))
            sh_key = ("sh", sh_w, sh_h)
            sh = _MASK_CACHE.get(sh_key)
            if sh is None:
                sh_im = Image.new("RGBA", (sh_w, sh_h), (0, 0, 0, 0))
                sd = ImageDraw.Draw(sh_im)
                sd.ellipse([0, 0, sh_w - 1, sh_h - 1], fill=(58, 42, 30, 70))
                sh = sh_im
                _MASK_CACHE[sh_key] = sh
            frame.paste(sh, (x + int(sp.width * 0.17), int(ground - sh_h // 2)), sh)
            frame.paste(sp, (x, y), sp)

    # --- props
    for i, pid in enumerate(scene.get("props", []) or []):
        if i >= len(_PROP_ANCHORS):
            break
        px, py = _PROP_ANCHORS[i]
        ph = int(frame_h * 0.085)
        pkey = ("pr", pid, ph)
        prop = _MASK_CACHE.get(pkey)
        if prop is None:
            src = get_prop(pid)
            prop = src.resize((max(1, int(src.width * ph / src.height)), ph), Image.BILINEAR)
            _MASK_CACHE[pkey] = prop
        frame.paste(prop, (int(px * frame_w - prop.width / 2),
                           int(py * frame_h - prop.height / 2)), prop)

    # --- fx (on a scratch RGBA layer, then paste+mask)
    if has_fx:
        seed = int(hashlib.sha1(str(scene.get("scene_id", "s")).encode()).hexdigest()[:6], 16)
        fx_layer = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
        draw_fx(fx_layer, scene["fx"], t, seed=seed)
        frame.paste(fx_layer, (0, 0), fx_layer)

    # --- overlays
    if scene_index == 0 and t < 4.6 and package_title:
        alpha = int(255 * min(1.0, t / 0.6, (4.6 - t) / 0.8))
        if alpha > 8:
            okey = ("title", package_title, episode_label, frame_w, frame_h)
            ov = _OVERLAY_CACHE.get(okey)
            if ov is None:
                ov = _title_overlay(package_title, episode_label, frame_w, frame_h)
                _OVERLAY_CACHE[okey] = ov
            sc = _scale_overlay(ov, alpha)
            frame.paste(sc, (0, 0), sc)
    if scene_index == scene_count - 1 and t > scene_dur - 4.6:
        alpha = int(255 * min(1.0, (t - (scene_dur - 4.6)) / 0.8))
        if alpha > 8:
            okey = ("end", frame_w, frame_h)
            ov = _OVERLAY_CACHE.get(okey)
            if ov is None:
                ov = _end_overlay(frame_w, frame_h)
                _OVERLAY_CACHE[okey] = ov
            sc = _scale_overlay(ov, alpha)
            frame.paste(sc, (0, 0), sc)

    # --- transitions
    trans = scene.get("transition_in", "fade")
    if scene_index > 0:
        if trans == "wipe_leaves" and p < 0.14:
            m = _wipe_mask(p / 0.14, (frame_w, frame_h))
            frame.paste(_black_image((frame_w, frame_h)), (0, 0), m)
        elif trans != "cut" and t < 0.45:
            m = _black_mask((frame_w, frame_h), int(255 * (1 - t / 0.45)))
            frame.paste(_black_image((frame_w, frame_h)), (0, 0), m)
    if scene_dur - t < 0.35 and scene_index < scene_count - 1:
        m = _black_mask((frame_w, frame_h), int(255 * (1 - (scene_dur - t) / 0.35)))
        frame.paste(_black_image((frame_w, frame_h)), (0, 0), m)
    return frame
