"""Drawing primitives: outline-correct shapes for the flat cartoon style."""

from __future__ import annotations

from PIL import Image, ImageDraw

from .palette import INK

OW = 5  # outline width @1080p baseline (scaled by caller via `scale`)


def _ow(ow: int | None) -> int:
    return OW if ow is None else ow


def oval(d: ImageDraw.ImageDraw, cx: float, cy: float, rx: float, ry: float,
         fill: str, ow: int | None = None, outline: str = INK) -> None:
    w = _ow(ow)
    d.ellipse([cx - rx - w, cy - ry - w, cx + rx + w, cy + ry + w], fill=outline)
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=fill)


def circle(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, fill: str,
           ow: int | None = None, outline: str = INK) -> None:
    oval(d, cx, cy, r, r, fill, ow, outline)


def rrect(d: ImageDraw.ImageDraw, box: tuple[float, float, float, float], fill: str,
          radius: float = 12, ow: int | None = None, outline: str = INK) -> None:
    w = _ow(ow)
    x0, y0, x1, y1 = box
    d.rounded_rectangle([x0 - w, y0 - w, x1 + w, y1 + w], radius=radius + w, fill=outline)
    d.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill)


def capsule(d: ImageDraw.ImageDraw, p1: tuple[float, float], p2: tuple[float, float],
            width: float, fill: str, ow: int | None = None, outline: str = INK) -> None:
    """Thick rounded line (limb)."""
    w = _ow(ow)
    r2 = (width + 2 * w) / 2
    r1 = width / 2
    for pts, r in (((p1, p2), r2), ((p1, p2), r1)):
        col = outline if r is r2 else fill
        d.line([pts[0], pts[1]], fill=col, width=int(r * 2))
        d.ellipse([pts[0][0] - r, pts[0][1] - r, pts[0][0] + r, pts[0][1] + r], fill=col)
        d.ellipse([pts[1][0] - r, pts[1][1] - r, pts[1][0] + r, pts[1][1] + r], fill=col)


def blob(d: ImageDraw.ImageDraw, points: list[tuple[float, float]], fill: str,
         ow: int | None = None, outline: str = INK) -> None:
    """Closed smooth-ish polygon (flattened curve via midpoint duplication)."""
    w = _ow(ow)
    if ow is not None or ow is None:
        d.polygon(points, fill=outline, outline=None)
        # shrink toward centroid for inner fill
        if len(points) >= 3:
            cx = sum(p[0] for p in points) / len(points)
            cy = sum(p[1] for p in points) / len(points)
            k = 1.0 - (w / max(4.0, ((cx - points[0][0]) ** 2 + (cy - points[0][1]) ** 2) ** 0.5 + 1e-6))
            k = max(0.75, min(0.98, k))
            inner = [(cx + (x - cx) * k, cy + (y - cy) * k) for x, y in points]
            d.polygon(inner, fill=fill)


def poly(d: ImageDraw.ImageDraw, points: list[tuple[float, float]], fill: str,
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


def wedge(d: ImageDraw.ImageDraw, apex: tuple[float, float], a: tuple[float, float],
          b: tuple[float, float], fill: str, ow: int | None = None, outline: str = INK) -> None:
    poly(d, [apex, a, b], fill, ow, outline)


def new_layer(size: tuple[int, int]) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)
