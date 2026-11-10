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
| `locations.py` | 7 locations, 4 time-of-day skies, 3 parallax layers: `paint_location(loc_id, tod)` → `{sky, far, mid, near}` RGBA 2200×1400; **PNG-first** — serves `assets/locations/<loc>/<tod>/<layer>.png`, `_paint_procedural` is fallback |
| `props.py` | 20 binding props (from `universe/manifest.json`), 256×256 RGBA; **PNG-first** — serves `assets/props_src/<id>.png`, PIL builders are fallback |
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

## Art-Style Redesign (decided 2026-11-05 — in progress)

User decision: **complete redesign of the look** — keep the 7 cast members (names,
personalities, species) and the world (7 locations, 20 props), but change the overall
artistic style. Not a polish of the current flat style.

**Style chosen: Modern CalArts** (user decision 2026-11-05) — bean-shaped bodies,
thick rounded outlines, oversized glossy eyes, small mouths, noodle limbs, bright
friendly colors (Steven Universe / Craig of the Creek era). Mockup images were planned
(7 PNGs, one per character × 3 styles) but the image API failed with *insufficient
account funds* and the user can't top up → style picked from written descriptions
instead. No AI-generated art anywhere in the plan; everything hand-coded in PIL.

Fallback if hand-coded PIL restyle proves insufficient: **ComfyUI on GitHub Actions**
(`https://github.com/Comfy-Org/ComfyUI`) to generate character/background art.
Notes on that fallback: CI has no GPU (CPU inference, slow, multi-GB model downloads
per run unless cached as artifacts); generated art must still satisfy determinism +
asset-count contract (231/112/20) → likely means generating **once**, committing PNGs,
and keeping `get_sprite` as a loader — the "regenerable from code" rule would need an
explicit exception. Decide before implementing.

Contract red lines for the redesign (unchanged):
- `get_sprite(char_id, state, expression, frame)` signature + fallbacks; RGBA 600×760;
  `GROUND=716`; self-dispatch first; POSES/FACES keys stay synced with
  `stickman_characters.py` + `universe/manifest.json`; asset counts 231/112/20
  asserted in `test_assets_build`; fully deterministic (motion derived from `frame_no`).
- Stickman profile keeps its own style — redesign applies to the **Fernwood base only**;
  stickman modules only mirror contract changes.
- Baseline gates to respect/tighten same-change: `sharpness_laplacian` ≥ 276 (rel 0.85
  of 324.9), `colorfulness` ≥ 61.45 (rel 0.90 of 68.28), `render_ms_per_frame` ≤ 60
  (current 52.9 — sprite builds are cached; supersampled/AA builds must stay cheap).

## Hand-drawn PNG art path — Bramble loader built (2026-11-05, checkpoint pending)

**Pivot**: first PIL CalArts pass (`42dc437`) was rejected by the user; they hand-drew
Bramble themselves → `assets/characters/bramble_new/` (32 PNGs). If approved, the user
redraws all 7 cast members + variants the same way, and `get_sprite` becomes a
**PNG loader + normalizer** (PIL path stays as fallback for not-yet-redrawn chars).

**Audit verdict: usable.** Findings:
- All 32 files 1120×2240 RGBA; magenta is alpha-0 preview only (no background);
  edges clean over light/dark/green (no visible fringe — defringe optional).
- Style matches approved direction: fully flat, no blush/nose, solid pupils,
  thick outlines, tool belt present. All 32 files visually distinct.
- **Coverage = contract-complete with 2 filename mappings**:
  states 13/13 — `pose1_idle→idle`, `pose2/3/4→talk_closed/mid/open`,
  `walk0-3`, `run0-3`, `sitting→sit`, `sleeping→sleep`, `carry`, `pointing→point`,
  `happy_action/sad_action/surprised_action→happy/sad/surprised`;
  expressions 14/14 — `neutral←pose1_idle`, `worried←worried_talk`, rest direct.

**Issues + planned solutions** (pending user confirmation):
1. **state×emotion combos** (main engineering item): expression files are full bodies
   on the standing pose, but runtime needs e.g. `sit×sad`, `walk×happy`, and lip-sync
   `talk_*×emotion`. Plan: head/face compositing (expression head box over state body),
   alignment tight among expression/pose files (face cx 559-561, cy 671-685 at 1120w);
   restore talk mouth from `pose2/3/4` after face paste → mirrors current `_face`
   (`pose.mouth` overrides expression mouth, so lip-sync wins). Fallback if seams show
   on tilted-head states (walk/run/carry/point): neutral face on dynamic states only.
2. **Ground line varies** per file (foot_y 2015-2079 vs idle 2057): normalize with a
   **per-state** Y offset (feet→`GROUND=716`), not per-frame — preserves run-air arc.
   Uniform scale: content → 600×760 canvas, same transform within a state.
3. **Repo size**: 24.9 MB/char full-res (×7 ≈ 174 MB) → quantize 256 colors + canvas
   height 1500 ≈ 5 MB/char (35 MB total; existing committed sprites = 27 MB/256 files).
   Quantizing also flattens the paper grain (8252 opaque colours → ≤256).
4. **Palette ≠ canon bible**: art has body `#858585`, muzzle `#F8F2CE`, stripes
   `#484848`, belt `#C88626` vs bible `#8A8F98` / `#F4F3EE` / `#2E2E33` → sync
   `universe/CHARACTER_BIBLE.md` + `manifest.json` to the art (art = source of truth)
   once user confirms.
5. **Contract**: `get_sprite` keeps signature/600×760/GROUND/determinism/counts
   (231/112/20); `blink`/`phase` kwargs accepted but have **no external callers**
   (only `characters.py` itself) → PNG path may ignore them; `python -m app assets`
   builds from the PNG sources; tests in `tests/test_art.py` (all states neutral,
   idle×all faces, walk frames differ) stay green.

**Decisions confirmed by user (2026-11-05, via question round):**
1. Filename mapping as proposed (loader translates contract names → user filenames;
   no file renames).
2. **Auto face compositing** — expression head pasted onto state body + talk mouth
   restored from `pose2/3/4`; fallback to neutral face on dynamic states if seams show.
3. Sources stored **quantized 256 colors, canvas height 1500** (~5 MB/char).
   Verified visually: quantize+resize deviates 0.39/255 mean RGB from original —
   detail fully retained; only paper grain flattens (intended).
4. **Bible/manifest synced to user's art** (art = canon): Bramble body `#858585`,
   muzzle `#F8F2CE`, stripes `#484848`, belt `#C88626` (done — superseded by the
   all-7 sync below).

**Suitability verdict delivered to user: USABLE, green light.** All visible pixels in
the pipeline come from the user's drawings (loader only scales/translates/pastes
their own regions — nothing redrawn by code). User will now redraw the remaining
6 characters (+ variants) in parallel while the Bramble loader is built; exact
32-file recipe (filenames, 1120×2240 RGBA, consistent ground line ≈y2060, face
center ≈cx560/face-top ≈y360, neutral faces on walk/run frames) given to user.

**Status: implementation DONE, checkpoint image awaiting user approval (2026-11-05).**
Landed in working tree (uncommitted):
1. `assets/characters_src/bramble/` — 32 files 750×1500, quantized 256c, 5.0 MB
   (originals stay in untracked `assets/characters/bramble_new/`).
2. **`app/render/art/png_sprites.py`** — `STATE_FILES`/`EXPR_FILES` mapping,
   `_measure_face`/`_face_rect` (first contiguous cream block, gap>15; clamped to
   idle rect when >1.15× wider, e.g. pose3_mid), `_mouth_span`, `_composite`
   (face-rect→face-rect resize paste; talk mouth restored after), `_meta`
   (scale from procedural PIL idle content height, dx centring, per-state ground
   bottom = max content bottom over cycle frames → run/walk arc preserved),
   `build()` returns None → PIL fallback (per-combination, partial casts work).
3. **Wired into `characters.get_sprite`** after id/state/expr validation, before
   `_build`; `_CACHE` key unchanged (blink/phase accepted, ignored by PNG path).
4. **Bible/manifest/palette synced to art** (art = canon): body `#858585`,
   muzzle/belly `#F8F2CE`, stripes `#484848`, belt `#C88626` — edited in
   `CHARACTER_BIBLE.md`, `manifest.json`, `palette.py` BRAMBLE entry (hexes
   corrected by the all-7 sync below).

**Bug found & fixed during self-review**: `_mouth_span` originally scanned from
rel-y 0.50 with thr<70 → in `sad`/`excited` etc. the big pupils dip into the
centre columns (rel-y ≤0.63) and grey frowns (r≈87) were missed, so the
lip-sync restore box started mid-face and sliced a horizontal strip through the
composited eyes. Fix: scan rel-y **0.66..0.95** only, threshold **<140**
(all mouths sit at rel 0.70–0.91 across all 32 files; eye bottoms ≤0.63).

**Verified**: full contact sheet (39 combos: 14 idle×expression, talk×3 emotions,
sit/carry/point/sleep/happy/sad/surprised, walk0-3, run0-3) — no seams
(column-step profile of composited faces matches un-composited ones; high-step
columns are the natural hood/ear edges), lip-sync closed→mid→open correct with
eyes intact, feet on GROUND line with run bob arc. `pytest -q` exit 0
(all 340+, incl. `test_art.py` count gates 231/112/20).

**Next**: user approves checkpoint image (`z_bramble_check.png`), then remaining
6 characters' redraws land the same way (recipe already given), then commit code
+ `characters_src/bramble/` (not memory files, not `bramble_new/`, not `_*.py`
scratch / `z_*.png`), push, CI.

## Full cast + props redesign delivered — wiring in progress (2026-11-07)

User hand-drew **all 7 cast members** and **all 20 props** in the Bramble style:

| Where | Contents |
|---|---|
| `assets/characters/<char>_new/` | 32 files each (fern **33**), 1120×2240 RGBA, magenta alpha-0 preview; untracked (gitignored) |
| `assets/props_new/` | 20 files, 1120×2240 RGBA; ids match `PROPS` exactly (gitignored 2026-11-07) |

Naming quirks: juni/marlow/pipkin files **unprefixed** (`pose1_idle.png`); bramble/
fern/willowby prefixed; **fern** has variants (`sad2`, `sleepy_new`, `surprised_new`,
`worried_talk_new`, both `silly` + `silly_new`); **wren** a different scheme
(`wren_01_idle_cutout`, `walk_01_wide…`, `run_01_widest…`, `sit`, `carry_empty`,
`point`, `silly_wink`, `sleep_upright`, `happy2`/`sad2`/`surprised2`, `worried`).

**Decisions confirmed (2026-11-07 question round):**
1. **Sources**: canonical `<char>_<key>.png` names in `assets/characters_src/<char>/`
   (resize h=1500 + quantize 256c, same as Bramble); originals never renamed.
2. **Fern map**: sad←`sad2`, sleepy←`sleepy_new`, surprised←`surprised_new`,
   worried←`worried_talk_new`, silly←`silly_new` (`fern_silly.png` stays unused).
3. **Wren map**: states happy/sad/surprised←`happy2`/`sad2`/`surprised2`;
   expressions←`happy`/`sad`/`surprised`; silly←`silly_wink`, sit←`sit`,
   sleep←`sleep_upright`, carry←`carry_empty`, point←`point`,
   walk/run←`walk_01..04`/`run_01..04`, talk←`02/03/04`, neutral←`01_idle`.
4. **Bible/manifest/palette → art for all 7** (art = canon, Bramble already done).
5. **Props**: same PNG-first pattern — quantized sources in `assets/props_src/`,
   crop-to-content → fit 256×256; PIL builders stay fallback; gitignore `props_new/`.
   Stickman profile untouched.
6. **Face detection caveat**: `_measure_face` cream mask is Bramble-tuned — Fern's
   cream **body** and Wren's cream **belly** pass it, Wren's face has no cream at
   all → per-character face handling required; verify via contact sheets.
7. **Locations = prompt files only** for now: `universe/prompts/locations/<loc>.md`,
   4 stages (morning/day/dusk/night) × one fenced copy-paste **Meta AI** prompt ×
   4 images (sky/far/mid/near) = 112 images total; full style block embedded per
   prompt (standalone); request 2200×1400 + alpha for far/mid/near, flag failures
   when images return.
8. **Workflow**: wire everything → `pytest -q` → `python -m app assets` → contact
   sheets for user review → commit only after user OK.

## Full cast + props wiring LANDED — awaiting user OK to commit (2026-11-07)

All of decision 1-8 above is implemented and verified; everything is uncommitted:

1. **Sources built**: `assets/characters_src/<char>/` 224 files (h=1500,
   quantized 256c; bramble's 32 already committed) + `assets/props_src/` 20
   files (crop-to-content → fit 256×256 letterbox → same quantize recipe,
   315 KB). Originals `*_new/` untouched, untracked (`.gitignore` now has
   `assets/characters/*_new/` + `assets/props_new/`).
2. **Props loader**: `props.py` `SRC_ROOT` + `_load_png` — `get_prop` order =
   stickman override → PNG → PIL builder. `_props_check.py`: 20/20 served from
   PNG, **0 builder fallbacks**, size/bbox OK. Consumers unchanged (`scene.py`
   resizes by height → ph×ph on the square canvas, identical to builders).
3. **Face detection v2** (`png_sprites.py`): eye-pair detector with per-char
   `MARGINS`/`MOUTH_DY`, `CREAM_CHARS` (bramble cream band), `_MIN_COMP=4000`
   (measured: smallest idle sclera 4912 vs largest non-eye white 1840),
   white-restore after quantize, shared single-linkage `_cluster` helper.
4. **Willowby sit face fix (candidate C)**: sitting drawing has no white px →
   `_pupil_anchor` fits the idle face rect onto drawn pupil+brow centroids
   (lsq per axis; pupils-only → uniform inter-pupil scale; fit rejected outside
   0.5–1.4). Sit rect = `(173,356,564,658)` (0.787×0.926 of idle), anchored
   rects bypass the idle size clamp, anchor applies only to composite base
   states when sclera detection fails. `_MATCH_TOL` **0.12 → 0.25** (all drawn
   pairs ≤12%, willowby sit 0.765–0.806). Idle-rect fallback kept for
   expression overlays (sad has closed eyes → `_measure_eyes` None).
5. **Colour sync (art = canon)** — 7 dicts in `palette.py`, 25 hexes in
   `manifest.json` `characters` block (count-guarded script), 8 blocks in
   `CHARACTER_BIBLE.md` (header now states the art-canon policy):

   | char | body | belly | dark | accent |
   |---|---|---|---|---|
   | juni | `#FD8127` | `#FCD88C` | `#5D2800` | cap `#2F9D30` / vein `#195518` |
   | bramble | `#858585` | `#F8F2CE` | `#484848` | belt `#C88626` (tool `#7A5433` unchanged — no art match >0.05%) |
   | marlow | `#B56A33` | `#FEF0CB` | `#432113` | pebble `#3173D1` (from prop art) |
   | wren | `#9B643D` | `#F2DAB5` | `#3A271D` | scarf+beak `#E59336` (`#DD9935` = shading) |
   | willowby | `#AF8964` | `#EEE1CF` | `#3C261B` | vest `#4F7648` / metal `#C9CCD2` |
   | fern | `#E6CDAA` | `#FEF7E8` | `#3C271D` | spot `#E8D0AC` (spots are tan, not white) |
   | pipkin | `#9E968F` | `#FEF1D8` | `#3B271E` | ear_inner `#E7B0A5` |

   Old accents `#C98B5E`/`#B45F4C` had **zero** strict matches in art (stale).
   Not synced (deliberate): `characters.py` hardcoded inner-ear pinks
   `#E8B4A6`/`#D8B48F`/`#F6E4CC` and `props.py` PIL-builder hexes — procedural
   fallback only, no strict art counterpart / superseded by PNG sources.
   Location/brand hexes (`#E9973A`, `#5B8FB9`, …) in other manifest blocks +
   bibles are a different domain — untouched.
6. **Location prompts landed**: `universe/prompts/locations/<loc>.md` × 7 —
   4 stages (morning/day/dusk/night) × one standalone fenced **Meta AI**
   prompt × 4 images (sky/far/mid/near) = 28 prompts / 112 images. Each embeds
   the full ASSET_BIBLE style block, `SKIES` gradient + sun/moon coords, the
   per-location layer inventory + binding hexes, 2200×1400 (11:7) + alpha for
   far/mid/near, output paths `assets/locations/<loc>/<tod>/<layer>.png`, and
   a per-stage QC line to flag failures (opaque returns, size, text, chars).
   Cave `near` is documented as legitimately empty; interior `sky` as an
   ambient base plate. No loader yet — prompts only (per decision 7).

**Verification**: `pytest` **340 passed** (exit 0), `python -m app assets`
**363 files (231/112/20)**, face dump clean (`(pupil-anchored)` only),
gate survey 0 rejections @0.25 / 0 unintended enables, composite check ALL OK
(78), visual review `z_sheet_{1..4}_v4.png` (willowby sit×sad seated behind
glasses; all 7 cast correct) + `z_props_v1.png` (20 props undistorted).

**Commit scope (only after user OK)**: code + `assets/characters_src/` (224) +
`assets/props_src/` (20) + `universe/` edits (manifest/bible/prompts) + memory
files. **Exclude**: `*_new/` originals, `_*.py` scratch, `z_*.png`.

## Locations PNG-first + willowbys block patch — landed 2026-11-10

All 112 location layers (7 locs × 4 tods × sky/far/mid/near) were generated by the
user from `universe/prompts/locations/*.md` and approved. Storage decision:
**output-only** — the single committed copy is `assets/locations/<loc>/<tod>/<layer>.png`
(RGBA 2200×1400, ~65 MB); the delivery archive `assets/locations/<loc>_new/` stays
gitignored. Install/patch by root `_install_locations.py` (uncommitted `_*.py` rule;
re-runnable from `*_new/`, idempotent).

1. **Loader**: `paint_location` dispatch = stickman override → `_load_pngs`
   (**all-or-nothing per (loc,tod)**: all 4 layers present → serve them, else …) →
   `_paint_procedural` (legacy code fallback). `PNG_ROOT = assets/locations`.
   Build re-saves are byte-idempotent (same `im.save` call as build_all).
2. **willowbys_burrow patch** (baked into the converter): AI leaked flat color blocks
   onto `mid` in morning/dusk/night (violates "everything above the floor line is
   transparent"). Final rule, per tod:
   - `strict` = d ≤ tol vs block RGBs, in region (alpha>32, y<floor, x≥xmin —
     night xmin 1990 protects chair/spines sharing the hex);
   - ring = `dilate(erode(strict, 1), 8)` — the 1px seam through shelf gaps must not
     anchor the fringe into furniture (this was the orange-book bite);
   - fringe = ring & d ≤ tol*6 & ~dark & ~wisp (soft low-spread px = shadow wisp);
   - **ramp** (chroma-hue <45° to block) for dark-side AA blends beyond tol*6, cmag
     floor per tod: morning **20**, night **11**, **dusk off** (orange hue collides
     with brown furniture); every ramp px must touch a dark stroke (asserted orphan=0).
   - Clears morning 101664 / dusk 462471 / night 86182 px. Accepted residue: faint
     y176 pane-top line (night), pre-existing teal hairline (morning) — user chose
     to keep both rather than widen the rule.
