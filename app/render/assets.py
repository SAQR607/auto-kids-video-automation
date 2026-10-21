"""Asset build: writes deterministic PNGs under assets/ (committed build output).

All art is regenerable from code — `python -m app assets build` is the source
of truth. The renderer auto-regenerates missing files; QC verifies the build.
Profile-aware: spec tuples (SPECIES/POSES/FACES/LOCATIONS/PROPS) and builders
resolve from the active art backend (Fernwood base or stickman override).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from PIL import Image

from .art.backend import art_module

TODS = ("day", "morning", "dusk", "night")


def build_all(assets_root: str | Path) -> dict[str, int]:
    root = Path(assets_root)
    counts: dict[str, int] = {}
    chars = art_module("characters")
    locs = art_module("locations")
    props = art_module("props")

    # characters: id/state/expression variants (idle neutral rest-state frames only —
    # dynamic states are drawn at runtime; committed PNGs cover static fallback).
    n = 0
    for cid in chars.SPECIES:
        cdir = root / "characters" / cid
        cdir.mkdir(parents=True, exist_ok=True)
        for st in chars.POSES:
            for fr in ((0, 1, 2, 3) if st in ("walk", "run") else (0,)):
                chars.get_sprite(cid, st, "neutral", fr).save(cdir / f"{st}_neutral_f{fr}.png")
                n += 1
        for expr in chars.FACES:
            chars.get_sprite(cid, "talk_mid", expr).save(cdir / f"talk_mid_{expr}_f0.png")
            n += 1
    counts["characters"] = n

    # locations: 4 tods x layers
    n = 0
    for loc in locs.LOCATIONS:
        for tod in TODS:
            layers = locs.paint_location(loc, tod)
            ldir = root / "locations" / loc / tod
            ldir.mkdir(parents=True, exist_ok=True)
            for name, im in layers.items():
                im.save(ldir / f"{name}.png")
                n += 1
    counts["locations"] = n

    # props
    n = 0
    pdir = root / "props"
    pdir.mkdir(parents=True, exist_ok=True)
    for pid in props.PROPS:
        props.get_prop(pid).save(pdir / f"{pid}.png")
        n += 1
    counts["props"] = n

    (root / "build.json").write_text(
        json.dumps({"built_at": int(time.time()), "counts": counts}, indent=2),
        encoding="utf-8",
    )
    return counts


def ensure_location(loc_id: str, tod: str, assets_root: str | Path) -> Path:
    """Return path to a layer dir, building it if missing (runtime self-heal)."""
    ldir = Path(assets_root) / "locations" / loc_id / tod
    if not (ldir / "near.png").exists():
        ldir.mkdir(parents=True, exist_ok=True)
        for name, im in art_module("locations").paint_location(loc_id, tod).items():
            im.save(ldir / f"{name}.png")
    return ldir


def ensure_prop(prop_id: str, assets_root: str | Path) -> Path:
    p = Path(assets_root) / "props" / f"{prop_id}.png"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        art_module("props").get_prop(prop_id).save(p)
    return p
