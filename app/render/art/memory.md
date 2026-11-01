# `app/render/art/` — Art Backends

## Module Responsibilities

Deterministic PIL drawing code for all visuals. Two backends selected by
profile: **Fernwood base** (default) and **stickman** (`APP_PROFILE=stickman`).
All art is regenerable from code — `python -m app assets` writes committed PNGs.

## Dispatch Pattern (key design)

`backend.py` resolves the active backend:

- `stickman(kind)` → the stickman module when `APP_PROFILE=stickman`, else `None`
- `active(kind)` → stickman override, else the Fernwood base module

Base art functions self-dispatch at call time; `assets.py` resolves build-time
tuples (`SPECIES/POSES/FACES/LOCATIONS/PROPS`) via `art_module(kind)`.
Stickman modules **mirror the base contracts** (same function signatures and
return shapes), so the renderer/pipeline never branches on profile.

## Current-layer Index

| File | Role |
|---|---|
| `backend.py` | Profile-aware backend dispatcher (pattern above) |
| `shapes.py` | Drawing primitives (outline-correct, flat cartoon style) |
| `palette.py` | Shared palette (binding colors from the bibles) |
| `characters.py` | Fernwood cast: `get_sprite(char_id, state, expression, frame)` → RGBA 600×760, cached; 13 states, 14 expressions, 4-frame walk/run cycles |
| `locations.py` | 7 locations, 4 time-of-day skies, 3 parallax layers: `paint_location(loc_id, tod)` → `{sky, far, mid, near}` RGBA 2200×1400 |
| `props.py` | 20 binding props (from `universe/manifest.json`), 256×256 RGBA |
| `fx.py` | FX overlays drawn live on frames (no asset files) |
| `stickman_characters.py` | Stickman cast (contract mirrors `characters.py`); solo hero "stik" = stick figure + red scarf (silhouette via accessory) |
| `stickman_locations.py` | 6 era-neutral storybook-history settings (contract mirrors `locations.py`) |
| `stickman_props.py` | Era-neutral props (contract mirrors `props.py`); unknown ids fall back to a neutral bundle |

## Development Notes

- When adding a new art kind: implement the base module + (optionally) a `stickman_`
  override with the **same contract**, then register in `backend.py` / `assets.py` tuples.
- Keep drawings deterministic (seeded/no wall-clock randomness) so asset builds are reproducible.
- Binding content counts (cast size, locations, props) come from `universe/manifest.json` —
  extend bibles + manifest first, then art code.
- The renderer applies the global time-of-day grade on top of location layers.
