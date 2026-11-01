"""Pure numpy/PIL video metrics — no new dependencies.

All functions take float32/float64 arrays in 0..255 unless noted. Metric
definitions are fixed so results are comparable across CI runs.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def to_gray(rgb: np.ndarray) -> np.ndarray:
    """HxWx3 uint8/float -> HxW float luminance (Rec.601)."""
    arr = rgb.astype(np.float64)
    return arr[..., 0] * 0.299 + arr[..., 1] * 0.587 + arr[..., 2] * 0.114


def psnr(a: np.ndarray, b: np.ndarray) -> float:
    """PSNR in dB over 0..255 range (inf for identical inputs)."""
    x = a.astype(np.float64)
    y = b.astype(np.float64)
    mse = float(np.mean((x - y) ** 2))
    if mse <= 1e-12:
        return float("inf")
    return 10.0 * float(np.log10(255.0 ** 2 / mse))


def _window_sums(img: np.ndarray, k: int) -> dict[str, np.ndarray]:
    """Sums of x, x^2 over kxk windows via integral image (valid region)."""
    padded = np.pad(img.astype(np.float64), ((1, 0), (1, 0)), mode="constant")
    ii = padded.cumsum(axis=0).cumsum(axis=1)
    s1 = ii[k:, k:] - ii[:-k, k:] - ii[k:, :-k] + ii[:-k, :-k]
    ii2 = np.pad(img.astype(np.float64) ** 2, ((1, 0), ((1, 0))), mode="constant") \
        .cumsum(axis=0).cumsum(axis=1)
    s2 = ii2[k:, k:] - ii2[:-k, k:] - ii2[k:, :-k] + ii2[:-k, :-k]
    return {"s1": s1, "s2": s2}


def ssim(a: np.ndarray, b: np.ndarray, k: int = 8) -> float:
    """Windowed SSIM (8x8 windows, C1/C2 per the original paper) on grayscale."""
    x = to_gray(a) if a.ndim == 3 else a.astype(np.float64)
    y = to_gray(b) if b.ndim == 3 else b.astype(np.float64)
    if x.shape != y.shape:
        raise ValueError(f"shape mismatch {x.shape} vs {y.shape}")
    if min(x.shape) < k:
        raise ValueError("image smaller than SSIM window")

    wx = _window_sums(x, k)
    wy = _window_sums(y, k)
    # cross term
    padded_xy = np.pad(x * y, ((1, 0), (1, 0)), mode="constant")
    ii_xy = padded_xy.cumsum(axis=0).cumsum(axis=1)
    sxy = ii_xy[k:, k:] - ii_xy[:-k, k:] - ii_xy[k:, :-k] + ii_xy[:-k, :-k]

    n = float(k * k)
    mux = wx["s1"] / n
    muy = wy["s1"] / n
    varx = np.maximum(wx["s2"] / n - mux ** 2, 0.0)
    vary = np.maximum(wy["s2"] / n - muy ** 2, 0.0)
    cov = sxy / n - mux * muy

    c1 = (0.01 * 255.0) ** 2
    c2 = (0.03 * 255.0) ** 2
    num = (2 * mux * muy + c1) * (2 * cov + c2)
    den = (mux ** 2 + muy ** 2 + c1) * (varx + vary + c2)
    return float(np.mean(num / den))


def laplacian_var(gray: np.ndarray) -> float:
    """Variance of the 4-neighbour Laplacian — classic focus/sharpness proxy."""
    g = gray.astype(np.float64) if gray.ndim == 3 else gray.astype(np.float64)
    if g.ndim == 3:
        g = to_gray(gray)
    lap = -4.0 * g[1:-1, 1:-1] + g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:]
    return float(np.var(lap))


def colorfulness(rgb: np.ndarray) -> float:
    """Hasler–Süsstrunk colorfulness metric (R-G / Y-B statistics)."""
    arr = rgb.astype(np.float64)
    rg = arr[..., 0] - arr[..., 1]
    yb = 0.5 * (arr[..., 0] + arr[..., 1]) - arr[..., 2]
    return float(np.sqrt(rg.std() ** 2 + yb.std() ** 2)
                 + 0.3 * np.sqrt(rg.mean() ** 2 + yb.mean() ** 2))


def flicker_mae(frames: list[np.ndarray]) -> float:
    """Mean |frame[i+1]-frame[i]| over consecutive frames (0 = perfectly stable).
    Pass identical-content windows (static camera, no fx) to probe stability."""
    if len(frames) < 2:
        return 0.0
    total = 0.0
    for prev, cur in zip(frames[:-1], frames[1:]):
        total += float(np.mean(np.abs(cur.astype(np.float64) - prev.astype(np.float64))))
    return total / (len(frames) - 1)


def _phase_shift(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """Sub-pixel translation (dx, dy) of b relative to a via phase correlation."""
    h, w = a.shape
    win = np.outer(np.hanning(h), np.hanning(w))
    fa = np.fft.fft2((a - a.mean()) * win)
    fb = np.fft.fft2((b - b.mean()) * win)
    cross = fa * np.conj(fb)
    mag = np.abs(cross)
    cross = cross / np.maximum(mag, 1e-12)
    surf = np.abs(np.fft.ifft2(cross))
    peak = np.unravel_index(int(np.argmax(surf)), surf.shape)
    py, px = int(peak[0]), int(peak[1])

    # 1-D parabolic refinement on each axis (periodic neighbours)
    def refine(axis: int, p: int, n: int) -> float:
        if axis == 0:
            vals = (surf[(p - 1) % n, px], surf[p, px], surf[(p + 1) % n, px])
        else:
            vals = (surf[py, (p - 1) % n], surf[py, p], surf[py, (p + 1) % n])
        denom = vals[0] - 2 * vals[1] + vals[2]
        if abs(denom) < 1e-12:
            return float(p)
        delta = 0.5 * (vals[0] - vals[2]) / denom
        delta = float(np.clip(delta, -1.0, 1.0))
        return p + delta

    fy = refine(0, py, h)
    fx = refine(1, px, w)
    if fy > h / 2:
        fy -= h
    if fx > w / 2:
        fx -= w
    # a - b sign: shift of b relative to a
    return -fx, -fy


def pan_motion(greys: list[np.ndarray], scale: float = 1.0) -> dict[str, float]:
    """Motion continuity over consecutive grayscale frames.

    Returns displacement statistics in source pixels (scale maps crop pixels
    back to source pixels). A smooth pan => consistent non-zero dx with low
    jitter and near-zero frozen_pct; cache/quantization stepping => large
    frozen_pct (identical consecutive frames) alternating with big jumps.
    """
    if len(greys) < 3:
        return {"pairs": 0.0, "median_dx": 0.0, "jitter_px": 0.0,
                "max_step_px": 0.0, "frozen_pct": 100.0}
    dxs: list[float] = []
    frozen = 0
    for prev, cur in zip(greys[:-1], greys[1:]):
        mae = float(np.mean(np.abs(cur - prev)))
        if mae < 0.05:
            frozen += 1
            dxs.append(0.0)
            continue
        dx, _ = _phase_shift(prev, cur)
        dxs.append(dx * scale)
    arr = np.asarray(dxs, dtype=np.float64)
    median = float(np.median(arr))
    active = arr[np.abs(arr) > 0.05]
    jitter_src = float(np.std(arr - median))
    return {
        "pairs": float(len(dxs)),
        "median_dx": abs(median),
        "jitter_px": jitter_src,
        "max_step_px": float(np.max(np.abs(arr))) if len(arr) else 0.0,
        "frozen_pct": 100.0 * frozen / max(1, len(dxs)),
    }


def load_png(path: str | Path) -> np.ndarray:
    with Image.open(path) as im:
        return np.asarray(im.convert("RGB"))
