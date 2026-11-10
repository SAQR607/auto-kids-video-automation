"""PNG-backed sprites for hand-drawn characters.

Some cast members are drawn by hand (user-authored PNG sets under
``assets/characters_src/<char_id>/``) instead of procedurally. This module
maps such sets onto the ``characters.get_sprite`` contract:

- contract name -> source file (``STATE_FILES`` / ``EXPR_FILES``)
- expression-on-state compositing: the expression's face rectangle is
  resized onto the state body's face rectangle, so the paste boundary
  coincides with the cream-face edge on both sides (no visible seam)
- lip-sync: while talking, the base frame's mouth region is re-pasted
  over the expression face (mirrors ``_face()`` where ``pose.mouth``
  overrides the expression mouth)
- normalization: uniform scale so the character occupies the same
  on-screen height as its procedural build, per-state ground alignment
  (feet -> the procedural idle content bottom; walk/run keep their arc
  because the whole cycle shares one offset), idle centre -> canvas centre

``build()`` returns ``None`` when a character (or one combination) has no
source files — callers fall back to the procedural PIL path, so partially
redrawn casts work.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

# committed, quantized source art (see memory: quantized 256 colors, h=1500)
SRC_ROOT = Path(__file__).resolve().parents[3] / "assets" / "characters_src"

# contract state -> source file key (``{frame}`` cycles over 0..3)
STATE_FILES: dict[str, str] = {
    "idle": "pose1_idle",
    "walk": "walk{frame}",
    "run": "run{frame}",
    "sit": "sitting",
    "sleep": "sleeping",
    "carry": "carry",
    "point": "pointing",
    "happy": "happy_action",
    "sad": "sad_action",
    "surprised": "surprised_action",
    "talk_closed": "pose2_closed",
    "talk_mid": "pose3_mid",
    "talk_open": "pose4_open",
}

# contract expression -> source file key
EXPR_FILES: dict[str, str] = {
    "neutral": "pose1_idle",
    "worried": "worried_talk",
    "amazed": "amazed",
    "brave": "brave",
    "confident": "confident",
    "curious": "curious",
    "determined": "determined",
    "excited": "excited",
    "happy": "happy",
    "proud": "proud",
    "sad": "sad",
    "silly": "silly",
    "sleepy": "sleepy",
    "surprised": "surprised",
}

# states whose drawn face may be replaced by an expression face
_COMPOSITE_STATES = frozenset({"idle", "talk_closed", "talk_mid", "talk_open", "sit"})
_TALK_STATES = frozenset({"talk_closed", "talk_mid", "talk_open"})

_FACE_GAP = 15        # cream-row gap that ends the face block
_WIDTH_TOL = 1.15     # own face wider than this x idle -> use the idle rect
_MIN_W = 0.80         # ... or narrower than this (wink: one sclera missing)
_MIN_H = 0.85         # ... or much shorter (half-closed eyes) -> idle rect
_MAX_H = 1.30
_MATCH_TOL = 0.25     # base/overlay face width must match within 25%
                      # (every drawn pair sits within 12%; the only wider
                      # case is willowby's pupil-anchored sitting head at
                      # 0.79 -- its head is genuinely smaller while seated)
_MIN_DARK = 5         # dark px required to call a mouth "found"

# --- per-character face geometry (measured on the hand-drawn sources) -------
# bramble keeps the approved cream-band detector; the rest anchor on the white
# sclera of the big eyes and expand by (a*Ew, b*Eh, c*Eh):
#   a = sideways (muzzle/cheek width), b = up (brows), c = down (mouth+chin)
CREAM_CHARS = frozenset({"bramble"})
MARGINS: dict[str, tuple[float, float, float]] = {
    "fern":    (0.25, 0.60, 1.70),
    "juni":    (0.30, 0.80, 1.40),
    "marlow":  (0.30, 0.80, 1.45),
    "pipkin":  (0.30, 0.80, 1.25),
    "willowby": (0.30, 0.70, 1.60),
    "wren":    (0.10, 0.35, 0.60),
}
# mouth search starts this many px below the sclera bottom (keeps the restore
# box clear of the eyes; wren's beak tucks right under them -> tiny gap)
MOUTH_DY: dict[str, int] = {
    "fern": 25, "juni": 20, "marlow": 10, "pipkin": 25,
    "willowby": 25, "wren": 8,
}
# Measured over all 224 sources: smallest real idle sclera = 4912 (fern),
# largest non-eye white = 1840 (pipkin teeth) -> 4000 admits every idle eye
# with margin while staying far above noise; components in 4000..6000 are
# all real eyes (walk/run/sad frames where the sclera is partly closed).
_MIN_COMP = 4000        # min white-component area (full-res px^2)
_MIN_CLUSTER = 5000     # min eye-cluster area
_MAX_CLUSTER_GAP = 200  # px between white components of one eye pair
# dark-pupil anchoring for composite bases whose sclera can't be measured
# (willowby's sitting drawing has no white px at all): over the cast the
# pupils measure 2320..3344 px^2, brows 608..848, mouth 720 -> area and
# shape strip brows/mouth, position above the pupil band strips the mouth
_MIN_PUPIL = 1500       # min dark-component area to count as a pupil
_MAX_PUPIL_DIM = 140    # max pupil bbox side (brows are flat)
_BROW_MIN, _BROW_MAX = 400, 6000   # brow component area bounds

_IMG: dict[Path, Image.Image] = {}
_FACE: dict[Path, tuple[tuple[int, int, int, int] | None,
                        tuple[int, int, int, int] | None]] = {}
_META: dict[str, dict] = {}


def _path(char_id: str, key: str) -> Path:
    return SRC_ROOT / char_id / f"{char_id}_{key}.png"


def _load(path: Path) -> Image.Image | None:
    img = _IMG.get(path)
    if img is None:
        if not path.exists():
            return None
        img = Image.open(path).convert("RGBA")
        _IMG[path] = img
    return img


def _alpha_bbox(img: Image.Image) -> tuple[int, int, int, int] | None:
    a = np.asarray(img)
    ys, xs = np.where(a[..., 3] > 8)
    if not len(xs):
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def _cream_mask(img: Image.Image) -> np.ndarray:
    a = np.asarray(img).astype(int)
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    # warm light fill (Bramble muzzle #F8F2CE etc.); white eye-whites are
    # excluded by the r-b warmth test but sit inside the face anyway
    return (al > 200) & (r > 225) & (g > 210) & (b > 150) & ((r - b) >= 12)


def _measure_face(img: Image.Image) -> tuple[int, int, int, int] | None:
    """Bounding box of the first contiguous cream block (the face)."""
    cream = _cream_mask(img)
    rows = cream.sum(1)
    nz = np.where(rows > 3)[0]
    if not len(nz):
        return None
    end = int(nz[0])
    for y in nz[1:]:
        if int(y) - end > _FACE_GAP:
            break
        end = int(y)
    band = cream[nz[0]:end + 1]
    xs = np.where(band.any(0))[0]
    if not len(xs):
        return None
    return int(xs[0]), int(nz[0]), int(xs[-1]), end


def _white_components(mask: np.ndarray, scale: int = 4):
    """8-connected components of an any-pooled mask -> full-res bboxes."""
    h, w = mask.shape
    ds = mask[:h // scale * scale, :w // scale * scale].reshape(
        h // scale, scale, w // scale, scale).any(axis=(1, 3))
    H, W = ds.shape
    seen = np.zeros_like(ds, dtype=bool)
    out = []
    for i in range(H):
        for j in np.where(ds[i] & ~seen[i])[0]:
            if seen[i, j]:
                continue
            q = deque([(i, int(j))])
            seen[i, j] = True
            ys, xs = [], []
            while q:
                y, x = q.popleft()
                ys.append(y)
                xs.append(x)
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if (0 <= ny < H and 0 <= nx < W
                                and ds[ny, nx] and not seen[ny, nx]):
                            seen[ny, nx] = True
                            q.append((ny, nx))
            out.append((min(xs) * scale, min(ys) * scale,
                        max(xs) * scale + scale - 1, max(ys) * scale + scale - 1,
                        len(ys) * scale * scale))
    return out


def _cluster(cands: list[tuple]) -> list[list[tuple]]:
    """Single-linkage clusters of components, largest total area first.

    Components closer than ``_MAX_CLUSTER_GAP`` join one cluster: a pupil
    splits each sclera into crescents that must reunite, and a brow pair
    (idle gap 153px, sitting gap 117px) must land in one cluster.
    """
    def gap(p, q):
        dx = max(0, max(p[0] - q[2], q[0] - p[2]))
        dy = max(0, max(p[1] - q[3], q[1] - p[3]))
        return max(dx, dy)

    clusters: list[list[tuple]] = []
    for c in sorted(cands, key=lambda c: -c[4]):
        for cl in clusters:
            if any(gap(c, o) <= _MAX_CLUSTER_GAP for o in cl):
                cl.append(c)
                break
        else:
            clusters.append([c])
    clusters.sort(key=lambda cl: -sum(c[4] for c in cl))
    return clusters


def _measure_eyes(img: Image.Image) -> tuple[int, int, int, int] | None:
    """Eye-pair bbox from the white sclera (big CalArts eyes), or None.

    Components are clustered single-linkage (see ``_cluster``). Files with
    closed eyes (happy/sit variants) return None -> caller anchors on the
    idle rect.
    """
    a = np.asarray(img).astype(int)
    ys, xs = np.where(a[..., 3] > 8)
    if not len(xs):
        return None
    top, bot = int(ys.min()), int(ys.max())
    white = ((a[..., 3] > 200) & (a[..., 0] > 240) & (a[..., 1] > 240)
             & (a[..., 2] > 235))
    cands = [c for c in _white_components(white)
             if c[4] >= _MIN_COMP and (c[2] - c[0]) >= 40 and (c[3] - c[1]) >= 40
             and (c[1] + c[3]) / 2 <= top + 0.55 * (bot - top)]
    if not cands:
        return None

    clusters = _cluster(cands)
    top_cl = clusters[0]
    if len(clusters) > 1:                       # eyes drawn far apart
        sec = clusters[1]
        tcy = sum((c[1] + c[3]) / 2 * c[4] for c in top_cl) / sum(c[4] for c in top_cl)
        scy = sum((c[1] + c[3]) / 2 * c[4] for c in sec) / sum(c[4] for c in sec)
        if abs(tcy - scy) <= 0.6 * max(c[3] - c[1] for c in top_cl + sec):
            top_cl = top_cl + sec
    if sum(c[4] for c in top_cl) < _MIN_CLUSTER:
        return None
    return (min(c[0] for c in top_cl), min(c[1] for c in top_cl),
            max(c[2] for c in top_cl), max(c[3] for c in top_cl))


def _measure_pupils(img: Image.Image
                    ) -> tuple[tuple[int, int, int, int],
                               tuple[int, int, int, int]] | None:
    """Left/right dark-pupil bboxes (left first), or None.

    Fallback landmark when the sclera can't be measured (willowby's
    sitting drawing is all brown). Pupils are the only big dark comps in
    the upper body band: brows and mouth fall below ``_MIN_PUPIL``, body
    outlines and head fills exceed ``_MAX_PUPIL_DIM``.
    """
    a = np.asarray(img).astype(int)
    ys, xs = np.where(a[..., 3] > 8)
    if not len(xs):
        return None
    top, bot = int(ys.min()), int(ys.max())
    dark = ((a[..., 3] > 200) & (a[..., 0] < 90) & (a[..., 1] < 90)
            & (a[..., 2] < 90))
    cands = [c for c in _white_components(dark)
             if c[4] >= _MIN_PUPIL and (c[2] - c[0]) <= _MAX_PUPIL_DIM
             and (c[3] - c[1]) <= _MAX_PUPIL_DIM
             and (c[1] + c[3]) / 2 <= top + 0.55 * (bot - top)]
    if len(cands) < 2:
        return None
    pair = _cluster(cands)[0]
    if len(pair) < 2:                      # only one pupil-sized blob
        return None
    two = sorted(pair, key=lambda c: -c[4])[:2]
    two.sort(key=lambda c: c[0])
    return ((two[0][0], two[0][1], two[0][2], two[0][3]),
            (two[1][0], two[1][1], two[1][2], two[1][3]))


def _measure_brows(img: Image.Image, pupils) -> tuple[tuple[int, int, int, int],
                                                      tuple[int, int, int, int]] | None:
    """Left/right brow bboxes just above the pupil band, or None.

    Position separates brows from the mouth: their sizes overlap (brows
    608..848 px^2, the sitting mouth 720 px^2), but brows end above the
    pupils while the mouth starts well below them.
    """
    if pupils is None:
        return None
    a = np.asarray(img).astype(int)
    dark = ((a[..., 3] > 200) & (a[..., 0] < 90) & (a[..., 1] < 90)
            & (a[..., 2] < 90))
    ptop = min(p[1] for p in pupils)
    cands = [c for c in _white_components(dark)
             if _BROW_MIN <= c[4] <= _BROW_MAX
             and (c[2] - c[0]) <= 160 and (c[3] - c[1]) <= 70
             and c[3] <= ptop + 20]
    if not cands:
        return None
    pair = _cluster(cands)[0]
    if len(pair) < 2:                      # brow pair must be drawn
        return None
    two = sorted(pair, key=lambda c: -c[4])[:2]
    two.sort(key=lambda c: c[0])
    return ((two[0][0], two[0][1], two[0][2], two[0][3]),
            (two[1][0], two[1][1], two[1][2], two[1][3]))


def _expand_eyes(char_id: str, e: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    a_, b_, c_ = MARGINS.get(char_id, (0.3, 0.7, 1.2))
    x0, y0, x1, y1 = e
    ew, eh = x1 - x0, y1 - y0
    return (round(x0 - a_ * ew), round(y0 - b_ * eh),
            round(x1 + a_ * ew), round(y1 + c_ * eh))


def _state_key(char_id: str, path: Path) -> str | None:
    """Contract state a source file belongs to (expression files -> None)."""
    prefix = f"{char_id}_"
    if not path.stem.startswith(prefix):
        return None
    key = path.stem[len(prefix):]
    for st, tmpl in STATE_FILES.items():
        keys = ([tmpl.format(frame=f) for f in range(4)]
                if "{frame}" in tmpl else [tmpl])
        if key in keys:
            return st
    return None


def _pupil_anchor(char_id: str, img: Image.Image):
    """(face rect, pupil-pair eye box) mapping the idle face onto this
    image's dark pupil+brow landmarks, or None when they can't be measured.

    Willowby's sitting drawing has no white sclera at all, so the eye-pair
    detector can't place its face. Fit the idle face rect onto the drawn
    pupils+brows instead (least squares per axis over the four landmark
    centres; pupils only -> uniform inter-pupil scale) so the expression
    paste lands on the face that is actually drawn. The fit is discarded
    when it asks for an implausible scale.
    """
    idle_path = _path(char_id, STATE_FILES["idle"])
    idle = _load(idle_path)
    if idle is None:
        return None
    tp, ip = _measure_pupils(img), _measure_pupils(idle)
    if tp is None or ip is None:
        return None
    idle_rect, _ = _face_rect(char_id, idle_path)
    if idle_rect is None:
        return None
    tb, ib = _measure_brows(img, tp), _measure_brows(idle, ip)

    def ctr(b):
        return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)

    pts_i, pts_t = [ctr(b) for b in ip], [ctr(b) for b in tp]
    if tb is not None and ib is not None:
        pts_i += [ctr(b) for b in ib]
        pts_t += [ctr(b) for b in tb]
        mx_i = sum(p[0] for p in pts_i) / len(pts_i)
        my_i = sum(p[1] for p in pts_i) / len(pts_i)
        mx_t = sum(p[0] for p in pts_t) / len(pts_t)
        my_t = sum(p[1] for p in pts_t) / len(pts_t)
        ax = (sum((p[0] - mx_i) * (q[0] - mx_t)
                  for p, q in zip(pts_i, pts_t))
              / sum((p[0] - mx_i) ** 2 for p in pts_i))
        ay = (sum((p[1] - my_i) * (q[1] - my_t)
                  for p, q in zip(pts_i, pts_t))
              / sum((p[1] - my_i) ** 2 for p in pts_i))
    else:                                   # brows hidden -> pupils only
        d_i = ((ip[1][0] - ip[0][0]) ** 2 + (ip[1][1] - ip[0][1]) ** 2) ** .5
        d_t = ((tp[1][0] - tp[0][0]) ** 2 + (tp[1][1] - tp[0][1]) ** 2) ** .5
        if d_i <= 0:
            return None
        ax = ay = d_t / d_i
        mx_i = (ip[0][0] + ip[1][0]) / 2; my_i = (ip[0][1] + ip[1][1]) / 2
        mx_t = (tp[0][0] + tp[1][0]) / 2; my_t = (tp[0][1] + tp[1][1]) / 2
    if not (0.5 <= ax <= 1.4 and 0.5 <= ay <= 1.4):
        return None                         # nonsense fit -> idle rect
    x0, y0, x1, y1 = idle_rect
    rect = (round(mx_t + (x0 - mx_i) * ax), round(my_t + (y0 - my_i) * ay),
            round(mx_t + (x1 - mx_i) * ax), round(my_t + (y1 - my_i) * ay))
    if rect[2] <= rect[0] or rect[3] <= rect[1]:
        return None
    eye = (min(p[0] for p in tp), min(p[1] for p in tp),
           max(p[2] for p in tp), max(p[3] for p in tp))
    return rect, eye


def _face_rect(char_id: str, path: Path):
    """(face rect, eye box | None) for one source file.

    Bramble: cream band (approved behaviour). Others: eye-pair box expanded
    by ``MARGINS``. Closed-eye files (happy/sit variants) fall back to the
    idle face; composite bases whose sclera can't be measured (willowby's
    sitting drawing has no white px at all) anchor on their drawn pupils
    instead; any other measurement whose size deviates from the idle face
    (inflated cream block, wink, half-closed eyes) is clamped to idle --
    the pupil-anchored rect is fitted to its own drawing and skips that
    clamp (its head is genuinely smaller while seated).
    """
    if path in _FACE:
        return _FACE[path]
    if not path.exists():
        return None, None
    idle_path = _path(char_id, STATE_FILES["idle"])
    img = _load(path)
    anchored = False
    if char_id in CREAM_CHARS:
        rect, eye = _measure_face(img), None
    else:
        e = _measure_eyes(img)
        if e is not None:
            rect, eye = _expand_eyes(char_id, e), e
        elif path == idle_path:
            rect, eye = _measure_face(img), None    # idle must be detectable
        else:
            rect, eye = _face_rect(char_id, idle_path)
            if _state_key(char_id, path) in _COMPOSITE_STATES:
                ap = _pupil_anchor(char_id, img)
                if ap is not None:
                    rect, eye = ap
                    anchored = True
    if rect is not None and path != idle_path and not anchored:
        idle_rect, _ = _face_rect(char_id, idle_path)
        if idle_rect is not None:
            w, h = rect[2] - rect[0], rect[3] - rect[1]
            iw, ih = (idle_rect[2] - idle_rect[0],
                      idle_rect[3] - idle_rect[1])
            if not (_MIN_W * iw <= w <= _WIDTH_TOL * iw
                    and _MIN_H * ih <= h <= _MAX_H * ih):
                rect = idle_rect
    _FACE[path] = (rect, eye)
    return rect, eye


def _mouth_span(img: Image.Image,
                rect: tuple[int, int, int, int],
                eye: tuple[int, int, int, int] | None,
                char_id: str) -> tuple[int | None, int | None]:
    """Top/bottom of the mouth = dark pixels in the face's centre columns.

    Eye-anchored rects (the new cast): scan from just below the sclera down
    to the rect bottom — the eyes can never fall into the band. Cream rects
    (bramble): rel-y 0.66..0.95 only — big CalArts pupils dip into the
    centre columns (down to rel-y 0.63) and would otherwise be mistaken
    for the mouth, which drags the lip-sync restore box up across the
    eyes. Threshold 140 catches grey feature lines (frowns measure ~87).
    """
    x0, y0, x1, y1 = rect
    fw, fh = x1 - x0, y1 - y0
    cx = (x0 + x1) // 2
    half = max(8, int(0.17 * fw))
    if eye is not None:
        dy = MOUTH_DY.get(char_id, max(8, round(0.1 * (eye[3] - eye[1]))))
        top_row = eye[3] + dy
        bot_row = y1
    else:
        top_row = y0 + int(0.66 * fh)
        bot_row = y0 + int(0.95 * fh)
    a = np.asarray(img).astype(int)
    m = ((a[..., 3] > 200) & (a[..., 0] < 140) & (a[..., 1] < 140)
         & (a[..., 2] < 140))[top_row:bot_row, cx - half:cx + half]
    ys, _ = np.where(m)
    if len(ys) < _MIN_DARK:
        return None, None
    return int(ys.min()) + top_row, int(ys.max()) + top_row


def _resize_rgba(crop: Image.Image, size: tuple[int, int]) -> Image.Image:
    """LANCZOS resize without alpha-edge fringe: the sources carry magenta
    preview colour in their transparent pixels, which would bleed into the
    head edge. Fully opaque crops (bramble) take the plain path."""
    alpha = crop.getchannel("A")
    if alpha.getextrema()[0] >= 255:
        return crop.resize(size, Image.LANCZOS)
    arr = np.asarray(crop).astype(np.float32)
    pm = Image.fromarray(
        np.round(arr[..., :3] * (arr[..., 3:4] / 255.0)).astype(np.uint8), "RGB"
    ).resize(size, Image.LANCZOS)
    a2 = alpha.resize(size, Image.LANCZOS)
    aa = np.asarray(a2).astype(np.float32)[..., None] / 255.0
    rgb = np.asarray(pm).astype(np.float32) / np.maximum(aa, 1e-6)
    out = np.dstack([np.clip(rgb, 0, 255), np.asarray(a2)]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def _composite(char_id: str, base: Image.Image, base_path: Path,
               ov: Image.Image, ov_path: Path, talk: bool) -> Image.Image | None:
    br, be = _face_rect(char_id, base_path)
    orr, oe = _face_rect(char_id, ov_path)
    if br is None or orr is None:
        return None
    bx0, by0, bx1, by1 = br
    ox0, oy0, ox1, oy1 = orr
    bw, bh, ow, oh = bx1 - bx0, by1 - by0, ox1 - ox0, oy1 - oy0
    if ow <= 0 or oh <= 0 or bw <= 0 or bh <= 0:
        return None
    if not (1 - _MATCH_TOL <= bw / ow <= 1 + _MATCH_TOL):
        return None                      # heads differ too much -> keep drawn face
    crop = ov.crop(orr)
    if (bw, bh) != (ow, oh):
        crop = _resize_rgba(crop, (bw, bh))
    out = base.copy()
    out.paste(crop, (bx0, by0), crop)    # alpha mask: never erase base head
    if not talk:
        return out

    # lip-sync: restore the base frame's talk mouth over the expression face
    b_top, b_bottom = _mouth_span(base, br, be, char_id)
    if b_top is None:
        return out
    o_top, o_bottom = _mouth_span(ov, orr, oe, char_id)
    if o_top is not None:                # cover the expression mouth too
        b_top = min(b_top, round(by0 + (o_top - oy0) * (bh / oh)) - 6)
        b_bottom = max(b_bottom, round(by0 + (o_bottom - oy0) * (bh / oh)) + 6)
    cx = (bx0 + bx1) // 2
    half = max(20, int(0.26 * bw))
    box = (cx - half, max(by0, b_top - 6), cx + half, min(by1, b_bottom + 6))
    out.paste(base.crop(box), (box[0], box[1]))
    return out


def _meta(char_id: str, size: tuple[int, int]) -> dict | None:
    """Per-character transform: scale + x offset + per-state ground offsets.

    Target metrics come from the procedural build of the same character so
    a hand-drawn cast member is sized/grounded identically to a PIL one.
    """
    m = _META.get(char_id)
    if m is None:
        from . import characters  # local import: avoids the module cycle
        idle_path = _path(char_id, STATE_FILES["idle"])
        idle_img = _load(idle_path)
        if idle_img is None:
            return None
        src_box = _alpha_bbox(idle_img)
        if src_box is None:
            return None
        pil = characters._build(char_id, "idle", "neutral", 0)
        pil_box = _alpha_bbox(pil)
        if pil_box is None:
            return None
        src_cx = (src_box[0] + src_box[2]) / 2
        ref_h = pil_box[3] - pil_box[1]
        ref_bottom = pil_box[3]
        s = ref_h / (src_box[3] - src_box[1])
        dx = size[0] / 2 - src_cx * s

        bottoms: dict[str, int] = {}
        for st, tmpl in STATE_FILES.items():
            frames = (0, 1, 2, 3) if st in ("walk", "run") else (0,)
            bs = []
            for fr in frames:
                img = _load(_path(char_id, tmpl.format(frame=fr)))
                if img is None:
                    continue
                box = _alpha_bbox(img)
                if box is not None:
                    bs.append(box[3])
            if bs:
                bottoms[st] = max(bs)     # one offset per cycle -> arc preserved
        m = {"s": s, "dx": dx, "ref_bottom": ref_bottom, "bottoms": bottoms}
        _META[char_id] = m
    return m


def build(char_id: str, state: str, expression: str, frame: int = 0, *,
          size: tuple[int, int] = (600, 760)) -> Image.Image | None:
    """Contract sprite from hand-drawn sources, or None -> PIL fallback."""
    tmpl = STATE_FILES.get(state)
    if tmpl is None:
        return None
    base_path = _path(char_id, tmpl.format(frame=frame))
    base = _load(base_path)
    if base is None:
        return None

    if expression != "neutral" and state in _COMPOSITE_STATES:
        ov_key = EXPR_FILES.get(expression)
        ov_path = _path(char_id, ov_key) if ov_key else None
        ov = _load(ov_path) if ov_path else None
        if ov is not None:
            merged = _composite(char_id, base, base_path, ov, ov_path,
                                talk=state in _TALK_STATES)
            if merged is not None:
                base = merged

    meta = _meta(char_id, size)
    if meta is None:
        return None
    s, dx = meta["s"], meta["dx"]
    w, h = base.size
    scaled = base.resize((max(1, round(w * s)), max(1, round(h * s))),
                         Image.LANCZOS)
    bottom = meta["bottoms"].get(state)
    if bottom is None:
        box = _alpha_bbox(base)
        if box is None:
            return None
        bottom = box[3]
    y_px = round(meta["ref_bottom"] - bottom * s)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.paste(scaled, (round(dx), y_px))
    return out
