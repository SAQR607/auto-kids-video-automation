# The Great Hollow (`great_hollow`) — location layer prompts

> Redesign prompts for the 4-layer background set. Tool: **Meta AI** (image gen).
> One fenced prompt per stage; each prompt generates the 4 named layers
> (`sky`, `far`, `mid`, `near`) → 16 images per location, 112 across all 7.
>
> **Outputs**: save each returned image as `<stage>/<layer>.png` (runtime path
> `assets/locations/great_hollow/<stage>/<layer>.png`; wiring into the
> pipeline follows after review).
> **Flag failures**: after each stage tick the QC line and write any failure
> right there (wrong size/aspect, `far`/`mid`/`near` came back opaque instead
> of transparent, text/watermark, characters in frame, style drift) — re-roll
> failed images with the same prompt.
>
> Layer contract: `paint_location("great_hollow", stage)` → `sky` opaque
> base + `far`/`mid`/`near` alpha pastes, each 2200×1400 RGBA (parallax
> 0.35/0.55/1.0/1.12). Palette hexes are binding (`universe/manifest.json`).
> All four stages must read as the same place — identical layout, only sky and
> light change. This is an interior: the `sky` base is a plain ambient
> gradient that the full-frame `far` wall covers.

## Stage: morning → `assets/locations/great_hollow/morning/`

QC: ⬜ size/aspect 11:7 · ⬜ alpha on far/mid/near · ⬜ no text/watermark · ⬜ no characters · ⬜ style match

```text
Generate 4 separate landscape images (each 2200×1400, 11:7 aspect) for a kids' animation background set.

STYLE (binding): flat vector-cartoon children's storybook background art — solid shapes with soft rounded silhouettes, no gradients except light glows and water ripples, every object outlined in dark warm brown #3A2A1E at a consistent weight that scales with the object (about 5px at 1080p), interior patches colour-blocked with NO outline, one soft light key from the upper-left, only 5-7 hues per frame, main shapes readable as silhouettes when scaled down small, cozy gentle preschool mood.

LOCATION: The Great Hollow — the cozy clubhouse interior inside a giant oak: dark wood-grain walls, a round map table, a hanging lantern, a big arched rope door, piles of books. Interior palette: wall #4A301E, floor #6B4A2E, lantern glow #FFC46B, table #A9743F, map paper #F2E3C2.

TIME OF DAY — MORNING. Light: warm gold morning light leaking in from the upper-left (global wash #FFF3D6 at ~18%), gentle long shadows to the right, lantern giving a soft constant #FFC46B glow.

THE 4 IMAGES:
1. sky — base plate only: plain full-frame opaque vertical gradient from #7A5433 (top) to #4A301E (bottom), nothing else (it sits behind the wall).
2. far — transparent cutout layer: full-frame dark oak wall #4A301E with wide diagonal wood-grain stripes #3A2617 running top to bottom, covering the entire canvas edge to edge (this layer is opaque full-frame by design; only its silhouette edges are cut out by the wall itself).
3. mid — transparent cutout layer: wooden floor band #6B4A2E from y≈900 (64% of height) to the bottom; round map table at x≈620, y≈980 (oval top #8A6A45, cream map #F2E6C8 with a brown route line and one red pin); hanging lantern from the top edge at x≈1450 down to y≈420 (dark cord, rounded rectangle #E8A33D body, outline #3A2A1E, glowing core #FFF3C8); big arched rope door right at x≈1900 (arch #5A3D24 with vertical slats #7A5A38, thick rope arc #C4A67C); small colourful book piles bottom-left at x≈260 and bottom-right at x≈2140 (spines #C4453D, #4E7A9E, #E8A33D, #5E8F4C, dark outlines). Everything above the floor line is transparent.
4. near — transparent cutout layer: dark floor strip #4A301E from y≈1330 (95%) to the bottom edge, full width. Everything else transparent.

RULES: images 2-4 must have a fully transparent background (alpha PNG) containing only their own objects, positioned so all four stack into one continuous scene with a shared horizon and ground line. No characters, animals, people, text, watermarks or logos anywhere. Keep object shapes, colours and layout identical across all four images. If you cannot return four images at once, generate them one at a time with this same prompt.
```

## Stage: day → `assets/locations/great_hollow/day/`

QC: ⬜ size/aspect 11:7 · ⬜ alpha on far/mid/near · ⬜ no text/watermark · ⬜ no characters · ⬜ style match

```text
Generate 4 separate landscape images (each 2200×1400, 11:7 aspect) for a kids' animation background set.

STYLE (binding): flat vector-cartoon children's storybook background art — solid shapes with soft rounded silhouettes, no gradients except light glows and water ripples, every object outlined in dark warm brown #3A2A1E at a consistent weight that scales with the object (about 5px at 1080p), interior patches colour-blocked with NO outline, one soft light key from the upper-left, only 5-7 hues per frame, main shapes readable as silhouettes when scaled down small, cozy gentle preschool mood.

LOCATION: The Great Hollow — the cozy clubhouse interior inside a giant oak: dark wood-grain walls, a round map table, a hanging lantern, a big arched rope door, piles of books. Interior palette: wall #4A301E, floor #6B4A2E, lantern glow #FFC46B, table #A9743F, map paper #F2E3C2.

TIME OF DAY — DAY. Light: clean neutral daylight from the upper-left, no colour wash, short soft shadows, lantern glowing softly #FFC46B.

THE 4 IMAGES:
1. sky — base plate only: plain full-frame opaque vertical gradient from #7A5433 (top) to #4A301E (bottom), nothing else (it sits behind the wall).
2. far — transparent cutout layer: full-frame dark oak wall #4A301E with wide diagonal wood-grain stripes #3A2617 running top to bottom, covering the entire canvas edge to edge (this layer is opaque full-frame by design; only its silhouette edges are cut out by the wall itself).
3. mid — transparent cutout layer: wooden floor band #6B4A2E from y≈900 (64% of height) to the bottom; round map table at x≈620, y≈980 (oval top #8A6A45, cream map #F2E6C8 with a brown route line and one red pin); hanging lantern from the top edge at x≈1450 down to y≈420 (dark cord, rounded rectangle #E8A33D body, outline #3A2A1E, glowing core #FFF3C8); big arched rope door right at x≈1900 (arch #5A3D24 with vertical slats #7A5A38, thick rope arc #C4A67C); small colourful book piles bottom-left at x≈260 and bottom-right at x≈2140 (spines #C4453D, #4E7A9E, #E8A33D, #5E8F4C, dark outlines). Everything above the floor line is transparent.
4. near — transparent cutout layer: dark floor strip #4A301E from y≈1330 (95%) to the bottom edge, full width. Everything else transparent.

RULES: images 2-4 must have a fully transparent background (alpha PNG) containing only their own objects, positioned so all four stack into one continuous scene with a shared horizon and ground line. No characters, animals, people, text, watermarks or logos anywhere. Keep object shapes, colours and layout identical across all four images. If you cannot return four images at once, generate them one at a time with this same prompt.
```

## Stage: dusk → `assets/locations/great_hollow/dusk/`

QC: ⬜ size/aspect 11:7 · ⬜ alpha on far/mid/near · ⬜ no text/watermark · ⬜ no characters · ⬜ style match

```text
Generate 4 separate landscape images (each 2200×1400, 11:7 aspect) for a kids' animation background set.

STYLE (binding): flat vector-cartoon children's storybook background art — solid shapes with soft rounded silhouettes, no gradients except light glows and water ripples, every object outlined in dark warm brown #3A2A1E at a consistent weight that scales with the object (about 5px at 1080p), interior patches colour-blocked with NO outline, one soft light key from the upper-left, only 5-7 hues per frame, main shapes readable as silhouettes when scaled down small, cozy gentle preschool mood.

LOCATION: The Great Hollow — the cozy clubhouse interior inside a giant oak: dark wood-grain walls, a round map table, a hanging lantern, a big arched rope door, piles of books. Interior palette: wall #4A301E, floor #6B4A2E, lantern glow #FFC46B, table #A9743F, map paper #F2E3C2.

TIME OF DAY — DUSK. Light: warm orange dusk wash #F5A96B at ~25% with violet #7A6FB0 falling from the top of the frame, long shadows to the left, the hanging lantern is now the dominant warm light with a stronger #FFC46B glow pooling on the table and floor.

THE 4 IMAGES:
1. sky — base plate only: plain full-frame opaque vertical gradient from #7A5433 (top) to #4A301E (bottom), faintly warmed by orange dusk light, nothing else (it sits behind the wall).
2. far — transparent cutout layer: full-frame dark oak wall #4A301E with wide diagonal wood-grain stripes #3A2617 running top to bottom, warmed by the orange/violet dusk light, covering the entire canvas edge to edge (this layer is opaque full-frame by design).
3. mid — transparent cutout layer: wooden floor band #6B4A2E from y≈900 (64% of height) to the bottom, dusk-warmed; round map table at x≈620, y≈980 (oval top #8A6A45, cream map #F2E6C8 with a brown route line and one red pin, lantern light pooling on it); hanging lantern from the top edge at x≈1450 down to y≈420 (dark cord, rounded rectangle #E8A33D body, outline #3A2A1E, bright glowing core #FFF3C8 with a soft #FFC46B halo); big arched rope door right at x≈1900 (arch #5A3D24 with vertical slats #7A5A38, thick rope arc #C4A67C); small colourful book piles bottom-left at x≈260 and bottom-right at x≈2140 (spines #C4453D, #4E7A9E, #E8A33D, #5E8F4C, dark outlines). Everything above the floor line is transparent.
4. near — transparent cutout layer: dark floor strip #4A301E from y≈1330 (95%) to the bottom edge, full width, dusk-warmed where the lantern light reaches. Everything else transparent.

RULES: images 2-4 must have a fully transparent background (alpha PNG) containing only their own objects, positioned so all four stack into one continuous scene with a shared horizon and ground line. No characters, animals, people, text, watermarks or logos anywhere. Keep object shapes, colours and layout identical across all four images. If you cannot return four images at once, generate them one at a time with this same prompt.
```

## Stage: night → `assets/locations/great_hollow/night/`

QC: ⬜ size/aspect 11:7 · ⬜ alpha on far/mid/near · ⬜ no text/watermark · ⬜ no characters · ⬜ style match

```text
Generate 4 separate landscape images (each 2200×1400, 11:7 aspect) for a kids' animation background set.

STYLE (binding): flat vector-cartoon children's storybook background art — solid shapes with soft rounded silhouettes, no gradients except light glows and water ripples, every object outlined in dark warm brown #3A2A1E at a consistent weight that scales with the object (about 5px at 1080p), interior patches colour-blocked with NO outline, one soft light key from the upper-left, only 5-7 hues per frame, main shapes readable as silhouettes when scaled down small, cozy gentle preschool mood.

LOCATION: The Great Hollow — the cozy clubhouse interior inside a giant oak: dark wood-grain walls, a round map table, a hanging lantern, a big arched rope door, piles of books. Interior palette: wall #4A301E, floor #6B4A2E, lantern glow #FFC46B, table #A9743F, map paper #F2E3C2.

TIME OF DAY — NIGHT. Light: cool blue night wash #22304F at ~45% with deep indigo #0B1026 from the top, walls and floor desaturated toward blue, the hanging lantern is the only warm light source casting a bright #FFC46B pool over the table and floor.

THE 4 IMAGES:
1. sky — base plate only: plain full-frame opaque vertical gradient from #7A5433 (top) to #4A301E (bottom), faintly cooled by blue night light, nothing else (it sits behind the wall).
2. far — transparent cutout layer: full-frame dark oak wall #4A301E with wide diagonal wood-grain stripes #3A2617 running top to bottom, cooled and desaturated by night light, covering the entire canvas edge to edge (this layer is opaque full-frame by design).
3. mid — transparent cutout layer: wooden floor band #6B4A2E from y≈900 (64% of height) to the bottom, night-cooled except where lantern light pools; round map table at x≈620, y≈980 (oval top #8A6A45, cream map #F2E6C8 glowing in the lantern light, brown route line and one red pin); hanging lantern from the top edge at x≈1450 down to y≈420 (dark cord, rounded rectangle #E8A33D body, outline #3A2A1E, brilliant glowing core #FFF3C8 with a wide #FFC46B halo); big arched rope door right at x≈1900 (arch #5A3D24 with vertical slats #7A5A38, thick rope arc #C4A67C); small colourful book piles bottom-left at x≈260 and bottom-right at x≈2140 (spines #C4453D, #4E7A9E, #E8A33D, #5E8F4C, dark outlines). Everything above the floor line is transparent.
4. near — transparent cutout layer: dark floor strip #4A301E from y≈1330 (95%) to the bottom edge, full width, night-cooled. Everything else transparent.

RULES: images 2-4 must have a fully transparent background (alpha PNG) containing only their own objects, positioned so all four stack into one continuous scene with a shared horizon and ground line. No characters, animals, people, text, watermarks or logos anywhere. Keep object shapes, colours and layout identical across all four images. If you cannot return four images at once, generate them one at a time with this same prompt.
```
