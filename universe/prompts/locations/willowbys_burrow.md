# Willowby's Burrow (`willowbys_burrow`) — location layer prompts

> Redesign prompts for the 4-layer background set. Tool: **Meta AI** (image gen).
> One fenced prompt per stage; each prompt generates the 4 named layers
> (`sky`, `far`, `mid`, `near`) → 16 images per location, 112 across all 7.
>
> **Outputs**: save each returned image as `<stage>/<layer>.png` (runtime path
> `assets/locations/willowbys_burrow/<stage>/<layer>.png`; wiring into the
> pipeline follows after review).
> **Flag failures**: after each stage tick the QC line and write any failure
> right there (wrong size/aspect, `far`/`mid`/`near` came back opaque instead
> of transparent, text/watermark, characters in frame, style drift) — re-roll
> failed images with the same prompt.
>
> Layer contract: `paint_location("willowbys_burrow", stage)` → `sky` opaque
> base + `far`/`mid`/`near` alpha pastes, each 2200×1400 RGBA (parallax
> 0.35/0.55/1.0/1.12). Palette hexes are binding (`universe/manifest.json`).
> All four stages must read as the same place — identical layout, only sky and
> light change. This is an interior: the `sky` base is a plain ambient
> gradient that the full-frame `far` wall covers.

## Stage: morning → `assets/locations/willowbys_burrow/morning/`

QC: ⬜ size/aspect 11:7 · ⬜ alpha on far/mid/near · ⬜ no text/watermark · ⬜ no characters · ⬜ style match

```text
Generate 4 separate landscape images (each 2200×1400, 11:7 aspect) for a kids' animation background set.

STYLE (binding): flat vector-cartoon children's storybook background art — solid shapes with soft rounded silhouettes, no gradients except light glows and water ripples, every object outlined in dark warm brown #3A2A1E at a consistent weight that scales with the object (about 5px at 1080p), interior patches colour-blocked with NO outline, one soft light key from the upper-left, only 5-7 hues per frame, main shapes readable as silhouettes when scaled down small, cozy gentle preschool mood.

LOCATION: Willowby's Burrow — a cozy den under the meadow: packed-earth walls with root grain, a round glowing window, a tall bookshelf full of colourful spines, a low tea table with cups, a striped rug, a blue armchair, a hanging root lamp. Palette: earth #8A6A48, wall #6B4A2E, floor #A98A5B, lamp/window glow #FFD98A, chair #4E7A9E, rug #C4453D.

TIME OF DAY — MORNING. Light: warm gold morning light leaking through the round window from the upper-left (global wash #FFF3D6 at ~18%), gentle long shadows to the right, window pane glowing #FFF3C8.

THE 4 IMAGES:
1. sky — base plate only: plain full-frame opaque vertical gradient from #A98A5B (top) to #6B4A2E (bottom), nothing else (it sits behind the wall).
2. far — transparent cutout layer: full-frame packed-earth wall #6B4A2E with wide diagonal root-grain stripes #5A3D24 running top to bottom, covering the entire canvas edge to edge (this layer is opaque full-frame by design).
3. mid — transparent cutout layer: wooden floor #A98A5B from y≈880 (63% of height) to the bottom with thin plank lines #96774C; round glowing window left at x≈420, y≈520 (cream pane #FFF3C8, dark cross bars #3A2A1E, bark ring #6B4A2E); tall bookshelf right at x≈1650 (frame #7A5A38, four shelves of colourful spines #C4453D, #4E7A9E, #E8A33D, #5E8F4C, #8A5A8E, dark outlines); low tea table at x≈800, y≈1040 (top #A98A5B, two cream cups #E8DCC8); striped round rug at x≈1150, y≈1240 (rings #C4453D / #E8DCC8); blue armchair at x≈380, y≈1160 (#4E7A9E with darker #3F6579 arms). Everything above the floor line is transparent.
4. near — transparent cutout layer: warm floor strip #7A5A38 from y≈1350 (96%) to the bottom edge, full width. Everything else transparent.

RULES: images 2-4 must have a fully transparent background (alpha PNG) containing only their own objects, positioned so all four stack into one continuous scene with a shared horizon and ground line. No characters, animals, people, text, watermarks or logos anywhere. Keep object shapes, colours and layout identical across all four images. If you cannot return four images at once, generate them one at a time with this same prompt.
```

## Stage: day → `assets/locations/willowbys_burrow/day/`

QC: ⬜ size/aspect 11:7 · ⬜ alpha on far/mid/near · ⬜ no text/watermark · ⬜ no characters · ⬜ style match

```text
Generate 4 separate landscape images (each 2200×1400, 11:7 aspect) for a kids' animation background set.

STYLE (binding): flat vector-cartoon children's storybook background art — solid shapes with soft rounded silhouettes, no gradients except light glows and water ripples, every object outlined in dark warm brown #3A2A1E at a consistent weight that scales with the object (about 5px at 1080p), interior patches colour-blocked with NO outline, one soft light key from the upper-left, only 5-7 hues per frame, main shapes readable as silhouettes when scaled down small, cozy gentle preschool mood.

LOCATION: Willowby's Burrow — a cozy den under the meadow: packed-earth walls with root grain, a round glowing window, a tall bookshelf full of colourful spines, a low tea table with cups, a striped rug, a blue armchair, a hanging root lamp. Palette: earth #8A6A48, wall #6B4A2E, floor #A98A5B, lamp/window glow #FFD98A, chair #4E7A9E, rug #C4453D.

TIME OF DAY — DAY. Light: clean neutral daylight through the window from the upper-left, no colour wash, short soft shadows, window pane bright #FFF3C8.

THE 4 IMAGES:
1. sky — base plate only: plain full-frame opaque vertical gradient from #A98A5B (top) to #6B4A2E (bottom), nothing else (it sits behind the wall).
2. far — transparent cutout layer: full-frame packed-earth wall #6B4A2E with wide diagonal root-grain stripes #5A3D24 running top to bottom, covering the entire canvas edge to edge (this layer is opaque full-frame by design).
3. mid — transparent cutout layer: wooden floor #A98A5B from y≈880 (63% of height) to the bottom with thin plank lines #96774C; round glowing window left at x≈420, y≈520 (cream pane #FFF3C8, dark cross bars #3A2A1E, bark ring #6B4A2E); tall bookshelf right at x≈1650 (frame #7A5A38, four shelves of colourful spines #C4453D, #4E7A9E, #E8A33D, #5E8F4C, #8A5A8E, dark outlines); low tea table at x≈800, y≈1040 (top #A98A5B, two cream cups #E8DCC8); striped round rug at x≈1150, y≈1240 (rings #C4453D / #E8DCC8); blue armchair at x≈380, y≈1160 (#4E7A9E with darker #3F6579 arms). Everything above the floor line is transparent.
4. near — transparent cutout layer: warm floor strip #7A5A38 from y≈1350 (96%) to the bottom edge, full width. Everything else transparent.

RULES: images 2-4 must have a fully transparent background (alpha PNG) containing only their own objects, positioned so all four stack into one continuous scene with a shared horizon and ground line. No characters, animals, people, text, watermarks or logos anywhere. Keep object shapes, colours and layout identical across all four images. If you cannot return four images at once, generate them one at a time with this same prompt.
```

## Stage: dusk → `assets/locations/willowbys_burrow/dusk/`

QC: ⬜ size/aspect 11:7 · ⬜ alpha on far/mid/near · ⬜ no text/watermark · ⬜ no characters · ⬜ style match

```text
Generate 4 separate landscape images (each 2200×1400, 11:7 aspect) for a kids' animation background set.

STYLE (binding): flat vector-cartoon children's storybook background art — solid shapes with soft rounded silhouettes, no gradients except light glows and water ripples, every object outlined in dark warm brown #3A2A1E at a consistent weight that scales with the object (about 5px at 1080p), interior patches colour-blocked with NO outline, one soft light key from the upper-left, only 5-7 hues per frame, main shapes readable as silhouettes when scaled down small, cozy gentle preschool mood.

LOCATION: Willowby's Burrow — a cozy den under the meadow: packed-earth walls with root grain, a round glowing window, a tall bookshelf full of colourful spines, a low tea table with cups, a striped rug, a blue armchair, a hanging root lamp. Palette: earth #8A6A48, wall #6B4A2E, floor #A98A5B, lamp/window glow #FFD98A, chair #4E7A9E, rug #C4453D.

TIME OF DAY — DUSK. Light: warm orange dusk wash #F5A96B at ~25% with violet #7A6FB0 falling from the top of the frame, long shadows to the left, the round window glows warm orange from the setting sun and the root lamp becomes a cozy #FFD98A light source pooling on the floor.

THE 4 IMAGES:
1. sky — base plate only: plain full-frame opaque vertical gradient from #A98A5B (top) to #6B4A2E (bottom), faintly warmed by orange dusk light, nothing else (it sits behind the wall).
2. far — transparent cutout layer: full-frame packed-earth wall #6B4A2E with wide diagonal root-grain stripes #5A3D24 running top to bottom, warmed by the orange/violet dusk light, covering the entire canvas edge to edge (this layer is opaque full-frame by design).
3. mid — transparent cutout layer: wooden floor #A98A5B from y≈880 (63% of height) to the bottom with thin plank lines #96774C, dusk-warmed with long shadows to the left; round glowing window left at x≈420, y≈520 (pane glowing warm orange-cream #FFE9B8, dark cross bars #3A2A1E, bark ring #6B4A2E); tall bookshelf right at x≈1650 (frame #7A5A38, four shelves of colourful spines #C4453D, #4E7A9E, #E8A33D, #5E8F4C, #8A5A8E, dark outlines); low tea table at x≈800, y≈1040 (top #A98A5B, two cream cups #E8DCC8 catching lamp light); striped round rug at x≈1150, y≈1240 (rings #C4453D / #E8DCC8); blue armchair at x≈380, y≈1160 (#4E7A9E with darker #3F6579 arms). Everything above the floor line is transparent.
4. near — transparent cutout layer: warm floor strip #7A5A38 from y≈1350 (96%) to the bottom edge, full width, dusk-warmed where lamp light reaches. Everything else transparent.

RULES: images 2-4 must have a fully transparent background (alpha PNG) containing only their own objects, positioned so all four stack into one continuous scene with a shared horizon and ground line. No characters, animals, people, text, watermarks or logos anywhere. Keep object shapes, colours and layout identical across all four images. If you cannot return four images at once, generate them one at a time with this same prompt.
```

## Stage: night → `assets/locations/willowbys_burrow/night/`

QC: ⬜ size/aspect 11:7 · ⬜ alpha on far/mid/near · ⬜ no text/watermark · ⬜ no characters · ⬜ style match

```text
Generate 4 separate landscape images (each 2200×1400, 11:7 aspect) for a kids' animation background set.

STYLE (binding): flat vector-cartoon children's storybook background art — solid shapes with soft rounded silhouettes, no gradients except light glows and water ripples, every object outlined in dark warm brown #3A2A1E at a consistent weight that scales with the object (about 5px at 1080p), interior patches colour-blocked with NO outline, one soft light key from the upper-left, only 5-7 hues per frame, main shapes readable as silhouettes when scaled down small, cozy gentle preschool mood.

LOCATION: Willowby's Burrow — a cozy den under the meadow: packed-earth walls with root grain, a round glowing window, a tall bookshelf full of colourful spines, a low tea table with cups, a striped rug, a blue armchair, a hanging root lamp. Palette: earth #8A6A48, wall #6B4A2E, floor #A98A5B, lamp/window glow #FFD98A, chair #4E7A9E, rug #C4453D.

TIME OF DAY — NIGHT. Light: cool blue night wash #22304F at ~45% with deep indigo #0B1026 from the top, walls and floor cooled and desaturated, the round window shows deep blue night behind its panes, and the root lamp is the only warm light — a bright #FFD98A pool over the chair, rug and tea table.

THE 4 IMAGES:
1. sky — base plate only: plain full-frame opaque vertical gradient from #A98A5B (top) to #6B4A2E (bottom), faintly cooled by blue night light, nothing else (it sits behind the wall).
2. far — transparent cutout layer: full-frame packed-earth wall #6B4A2E with wide diagonal root-grain stripes #5A3D24 running top to bottom, cooled and desaturated by night light, covering the entire canvas edge to edge (this layer is opaque full-frame by design).
3. mid — transparent cutout layer: wooden floor #A98A5B from y≈880 (63% of height) to the bottom with thin plank lines #96774C, night-cooled except for the lamp's warm pool; round window left at x≈420, y≈520 (panes deep blue with pale #F5F0DC moonlight, dark cross bars #3A2A1E, bark ring #6B4A2E); tall bookshelf right at x≈1650 (frame #7A5A38, four shelves of colourful spines #C4453D, #4E7A9E, #E8A33D, #5E8F4C, #8A5A8E, dark outlines, cooled at the edges); low tea table at x≈800, y≈1040 (top #A98A5B, two cream cups #E8DCC8 lit by the lamp); striped round rug at x≈1150, y≈1240 (rings #C4453D / #E8DCC8); blue armchair at x≈380, y≈1160 (#4E7A9E with darker #3F6579 arms, warm lamp light on one side). Everything above the floor line is transparent.
4. near — transparent cutout layer: warm floor strip #7A5A38 from y≈1350 (96%) to the bottom edge, full width, night-cooled outside the lamp pool. Everything else transparent.

RULES: images 2-4 must have a fully transparent background (alpha PNG) containing only their own objects, positioned so all four stack into one continuous scene with a shared horizon and ground line. No characters, animals, people, text, watermarks or logos anywhere. Keep object shapes, colours and layout identical across all four images. If you cannot return four images at once, generate them one at a time with this same prompt.
```
