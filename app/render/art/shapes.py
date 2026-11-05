"""Drawing primitives: outline-correct shapes for the flat cartoon style.

PIL has no anti-aliasing, so `aa_layer()` draws at 2x through a
coordinate-scaling proxy (`ScaledDraw`) and `flatten()` downscales with
premultiplied alpha (clean AA edges, no dark halo). Opt-in: existing
callers of `new_layer()` are untouched and keep pixel-identical output.
"""

from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageChops, ImageDraw

from .palette import INK

OW = 5  # outline width @1080p baseline (scaled by caller via `scale`)
AA = 2  # default supersample factor


def _ow(ow: int | None) -> int:
    return OW if ow is None else ow


# ------------------------------------------------------------- anti-aliasing --

class ScaledDraw:
    """ImageDraw proxy multiplying coordinates/widths/radii by `s`.

    Any drawing method the art modules use is scaled; unknown attributes
    fall through to the raw ImageDraw (unscaled — for non-geometry calls
    like text measurement, which the art code does not use).
    """
    __slots__ = ("_d", "_s")

    def __init__(self, d: ImageDraw.ImageDraw, s: int) -> None:
        self._d, self._s = d, s

    def _xy(self, xy):
        s = self._s
        if not xy:
            return xy
        if isinstance(xy[0], (tuple, list)):
            return [(x * s, y * s) for x, y in xy]
        return [v * s for v in xy]

    def _w(self, w):
        return max(1, round(w * self._s)) if w else w

    def line(self, xy, fill=None, width=1, joint=None):
        self._d.line(self._xy(xy), fill=fill, width=self._w(width), joint=joint)

    def ellipse(self, xy, fill=None, outline=None, width=1):
        self._d.ellipse(self._xy(xy), fill=fill, outline=outline,
                        width=self._w(width))

    def polygon(self, xy, fill=None, outline=None, width=1):
        self._d.polygon(self._xy(xy), fill=fill, outline=outline,
                        width=self._w(width))

    def rectangle(self, xy, fill=None, outline=None, width=1):
        self._d.rectangle(self._xy(xy), fill=fill, outline=outline,
                          width=self._w(width))

    def rounded_rectangle(self, xy, radius=0, fill=None, outline=None, width=1):
        self._d.rounded_rectangle(self._xy(xy), radius=radius * self._s,
                                  fill=fill, outline=outline,
                                  width=self._w(width))

    def arc(self, xy, start, end, fill=None, width=1):
        self._d.arc(self._xy(xy), start, end, fill=fill, width=self._w(width))

    def pieslice(self, xy, start, end, fill=None, outline=None, width=1):
        self._d.pieslice(self._xy(xy), start, end, fill=fill, outline=outline,
                         width=self._w(width))

    def chord(self, xy, start, end, fill=None, outline=None, width=1):
        self._d.chord(self._xy(xy), start, end, fill=fill, outline=outline,
                      width=self._w(width))

    def point(self, xy, fill=None):
        self._d.point(self._xy(xy), fill=fill)

    def __getattr__(self, name):
        return getattr(self._d, name)


def aa_layer(size: tuple[int, int], s: int = AA
             ) -> tuple[Image.Image, ScaledDraw]:
    """Layer drawn at `s`x for anti-aliased output. Pair with `flatten()`."""
    big = (size[0] * s, size[1] * s)
    img = Image.new("RGBA", big, (0, 0, 0, 0))
    return img, ScaledDraw(ImageDraw.Draw(img), s)


def flatten(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Downscale an `aa_layer` image to `size` with premultiplied alpha.

    Premultiplying before the box-filter reduce stops transparent-black
    pixels from bleeding into edges (the classic dark-halo artifact);
    un-premultiplying afterwards restores true colours — but only the
    partial-alpha silhouette band needs it (opaque pixels are unchanged
    by the premultiply, fully-transparent ones stay zero), which keeps
    the whole round-trip cheap enough for per-sprite builds.
    """
    s = img.width // size[0] if size[0] else 1
    if s <= 1:
        return img.resize(size, Image.LANCZOS) if img.size != size else img
    r, g, b, a = img.split()
    pre = Image.merge("RGBA", (ImageChops.multiply(r, a), ImageChops.multiply(g, a),
                               ImageChops.multiply(b, a), a)).reduce(s)
    arr = np.asarray(pre)
    a8 = arr[..., 3]
    out = arr.copy()
    edge = (a8 > 0) & (a8 < 255)
    if edge.any():
        ae = a8[edge].astype(np.uint16)
        rgb = arr[..., :3][edge].astype(np.uint16)
        rgb *= 255
        rgb //= ae[:, None]
        np.clip(rgb, 0, 255, out=rgb)
        out[..., :3][edge] = rgb.astype(np.uint8)
    return Image.fromarray(out, "RGBA")


# ----------------------------------------------------------------- primitives --

def oval(d, cx: float, cy: float, rx: float, ry: float,
         fill: str, ow: int | None = None, outline: str = INK) -> None:
    w = _ow(ow)
    d.ellipse([cx - rx - w, cy - ry - w, cx + rx + w, cy + ry + w], fill=outline)
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=fill)


def circle(d, cx: float, cy: float, r: float, fill: str,
           ow: int | None = None, outline: str = INK) -> None:
    oval(d, cx, cy, r, r, fill, ow, outline)


def rrect(d, box: tuple[float, float, float, float], fill: str,
          radius: float = 12, ow: int | None = None, outline: str = INK) -> None:
    w = _ow(ow)
    x0, y0, x1, y1 = box
    d.rounded_rectangle([x0 - w, y0 - w, x1 + w, y1 + w], radius=radius + w, fill=outline)
    d.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill)


def capsule(d, p1: tuple[float, float], p2: tuple[float, float],
            width: float, fill: str, ow: int | None = None, outline: str = INK) -> None:
    """Thick rounded line (limb)."""
    w = _ow(ow)
    for r, col in (((width + 2 * w) / 2, outline), (width / 2, fill)):
        d.line([p1, p2], fill=col, width=int(r * 2))
        d.ellipse([p1[0] - r, p1[1] - r, p1[0] + r, p1[1] + r], fill=col)
        d.ellipse([p2[0] - r, p2[1] - r, p2[0] + r, p2[1] + r], fill=col)


def blob(d, points: list[tuple[float, float]], fill: str,
         ow: int | None = None, outline: str = INK) -> None:
    """Closed smooth-ish polygon (outline first, shrink toward centroid)."""
    w = _ow(ow)
    d.polygon(points, fill=outline, outline=None)
    if len(points) >= 3:
        cx = sum(p[0] for p in points) / len(points)
        cy = sum(p[1] for p in points) / len(points)
        r0 = math.hypot(cx - points[0][0], cy - points[0][1]) + 1e-6
        k = max(0.75, min(0.98, 1.0 - (w / max(4.0, r0))))
        inner = [(cx + (x - cx) * k, cy + (y - cy) * k) for x, y in points]
        d.polygon(inner, fill=fill)


def poly(d, points: list[tuple[float, float]], fill: str,
         ow: int | None = None, outline: str = INK) -> None:
    w = _ow(ow)
    d.polygon(points, fill=outline)
    if len(points) >= 3:
        cx = sum(p[0] for p in points) / len(points)
        cy = sum(p[1] for p in points) / len(points)
        inner = []
        for x, y in points:
            vx, vy = x - cx, y - cy
            dist = (vx * vx + vy * vy) ** 0.5 or 1
            shrink = min(w, dist * 0.4)
            inner.append((x - vx / dist * shrink, y - vy / dist * shrink))
        d.polygon(inner, fill=fill)


def wedge(d, apex: tuple[float, float], a: tuple[float, float],
          b: tuple[float, float], fill: str, ow: int | None = None,
          outline: str = INK) -> None:
    poly(d, [apex, a, b], fill, ow, outline)


def new_layer(size: tuple[int, int]) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)
