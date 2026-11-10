# Hollow Oak Village (`hollow_oak_village`) — location layer prompts

> Redesign prompts for the 4-layer background set. Tool: **Meta AI** (image gen).
> One fenced prompt per stage; each prompt generates the 4 named layers
> (`sky`, `far`, `mid`, `near`) → 16 images per location, 112 across all 7.
>
> **Outputs**: save each returned image as `<stage>/<layer>.png` (runtime path
> `assets/locations/hollow_oak_village/<stage>/<layer>.png`; wiring into the
> pipeline follows after review).
> **Flag failures**: after each stage tick the QC line and write any failure
> right there (wrong size/aspect, `far`/`mid`/`near` came back opaque instead
> of transparent, text/watermark, characters in frame, style drift) — re-roll
> failed images with the same prompt.
>
> Layer contract: `paint_location("hollow_oak_village", stage)` → `sky` opaque
> base + `far`/`mid`/`near` alpha pastes, each 2200×1400 RGBA (parallax
> 0.35/0.55/1.0/1.12). Palette hexes are binding (`universe/manifest.json`).
> All four stages must read as the same place — identical layout, only sky and
> light change.

## Stage: morning → `assets/locations/hollow_oak_village/morning/`

QC: ⬜ size/aspect 11:7 · ⬜ alpha on far/mid/near · ⬜ no text/watermark · ⬜ no characters · ⬜ style match

```text
Generate 4 separate landscape images (each 2200×1400, 11:7 aspect) for a kids' animation background set.

STYLE (binding): flat vector-cartoon children's storybook background art — solid shapes with soft rounded silhouettes, no gradients except light glows and water ripples, every object outlined in dark warm brown #3A2A1E at a consistent weight that scales with the object (about 5px at 1080p), interior patches colour-blocked with NO outline, one soft light key from the upper-left, only 5-7 hues per frame, main shapes readable as silhouettes when scaled down small, cozy gentle preschool mood.

LOCATION: Hollow Oak Village — a village green under a giant ancient oak with a round arched door in its trunk, small round cottages, mushroom-cap lamps, flowers. Palette: bark #6B4A2E, door green #4E7A4A, grass #6FA14C, lamp glow #FFD98A.

TIME OF DAY — MORNING. Sky: full-frame opaque vertical gradient, top warm apricot #FFD9A0 → bottom cream #FFF3D6; soft sun disc at upper-LEFT (about x=460, y=300 of 2200×1400) with glow ring #FFE9B8 and white-hot core #FFFBE8; three or four fluffy white clouds. Light: warm gold wash #FFF3D6 at ~18% over the whole scene, gentle long shadows to the right.

THE 4 IMAGES:
1. sky — the morning sky described above, fully opaque edge to edge, nothing else.
2. far — transparent cutout layer: two rolling hill bands (#9CC77E behind, #87B36B in front) with hilltops between y=580 and y=900, plus one round-crowned oak tree at far left (x≈180) and one at far right (x≈2050), trunks #6B4A2E, canopies #4E8A44 with #5FA34F highlights. Hills fill down to the bottom edge; everything above them is transparent.
3. mid — transparent cutout layer: grassy ground #7FB069 with darker stripe #6BA05A from y≈860 (61% of height) to the bottom; centered giant hollow oak (two thick trunks #6B4A2E, huge canopy of overlapping circles #4E8A44 with #5FA34F highlights, round arched door #8A6A45 with dark #3A2A1E opening, two round windows glowing #FFD98A); small round cottage left at x≈520 (walls #C98A5B) and right at x≈1720 (walls #B97A6B) with triangular roofs #8A5A3B, doors #5A3D24, round windows glowing #FFE9C8; five mushroom lamps at x=330, 760, 1440, 1960, 2100 (cream stems #E8DCC8, red caps #E2574C with cream dots). Everything above the ground line is transparent.
4. near — transparent cutout layer: grass tufts #5E8F4C along y≈1240 (89%) and six simple five-petal flowers (#F0A5C0 and #F7D774) at y=1300–1345, cropped by the bottom edge. Everything else transparent.

RULES: images 2-4 must have a fully transparent background (alpha PNG) containing only their own objects, positioned so all four stack into one continuous scene with a shared horizon and ground line. No characters, animals, people, text, watermarks or logos anywhere. Keep object shapes, colours and layout identical across all four images. If you cannot return four images at once, generate them one at a time with this same prompt.
```

## Stage: day → `assets/locations/hollow_oak_village/day/`

QC: ⬜ size/aspect 11:7 · ⬜ alpha on far/mid/near · ⬜ no text/watermark · ⬜ no characters · ⬜ style match

```text
Generate 4 separate landscape images (each 2200×1400, 11:7 aspect) for a kids' animation background set.

STYLE (binding): flat vector-cartoon children's storybook background art — solid shapes with soft rounded silhouettes, no gradients except light glows and water ripples, every object outlined in dark warm brown #3A2A1E at a consistent weight that scales with the object (about 5px at 1080p), interior patches colour-blocked with NO outline, one soft light key from the upper-left, only 5-7 hues per frame, main shapes readable as silhouettes when scaled down small, cozy gentle preschool mood.

LOCATION: Hollow Oak Village — a village green under a giant ancient oak with a round arched door in its trunk, small round cottages, mushroom-cap lamps, flowers. Palette: bark #6B4A2E, door green #4E7A4A, grass #6FA14C, lamp glow #FFD98A.

TIME OF DAY — DAY. Sky: full-frame opaque vertical gradient, top sky blue #8ED4F5 → bottom pale #CDEFFC; bright sun disc upper-RIGHT (about x=1760, y=200) with glow #FFF6C8 and white-hot core #FFFBE8; fluffy white clouds. Light: clean neutral daylight from the upper-left, no colour wash, short soft shadows.

THE 4 IMAGES:
1. sky — the day sky described above, fully opaque edge to edge, nothing else.
2. far — transparent cutout layer: two rolling hill bands (#9CC77E behind, #87B36B in front) with hilltops between y=580 and y=900, plus one round-crowned oak tree at far left (x≈180) and one at far right (x≈2050), trunks #6B4A2E, canopies #4E8A44 with #5FA34F highlights. Hills fill down to the bottom edge; everything above them is transparent.
3. mid — transparent cutout layer: grassy ground #7FB069 with darker stripe #6BA05A from y≈860 (61% of height) to the bottom; centered giant hollow oak (two thick trunks #6B4A2E, huge canopy of overlapping circles #4E8A44 with #5FA34F highlights, round arched door #8A6A45 with dark #3A2A1E opening, two round windows glowing #FFD98A); small round cottage left at x≈520 (walls #C98A5B) and right at x≈1720 (walls #B97A6B) with triangular roofs #8A5A3B, doors #5A3D24, round windows glowing #FFE9C8; five mushroom lamps at x=330, 760, 1440, 1960, 2100 (cream stems #E8DCC8, red caps #E2574C with cream dots). Everything above the ground line is transparent.
4. near — transparent cutout layer: grass tufts #5E8F4C along y≈1240 (89%) and six simple five-petal flowers (#F0A5C0 and #F7D774) at y=1300–1345, cropped by the bottom edge. Everything else transparent.

RULES: images 2-4 must have a fully transparent background (alpha PNG) containing only their own objects, positioned so all four stack into one continuous scene with a shared horizon and ground line. No characters, animals, people, text, watermarks or logos anywhere. Keep object shapes, colours and layout identical across all four images. If you cannot return four images at once, generate them one at a time with this same prompt.
```

## Stage: dusk → `assets/locations/hollow_oak_village/dusk/`

QC: ⬜ size/aspect 11:7 · ⬜ alpha on far/mid/near · ⬜ no text/watermark · ⬜ no characters · ⬜ style match

```text
Generate 4 separate landscape images (each 2200×1400, 11:7 aspect) for a kids' animation background set.

STYLE (binding): flat vector-cartoon children's storybook background art — solid shapes with soft rounded silhouettes, no gradients except light glows and water ripples, every object outlined in dark warm brown #3A2A1E at a consistent weight that scales with the object (about 5px at 1080p), interior patches colour-blocked with NO outline, one soft light key from the upper-left, only 5-7 hues per frame, main shapes readable as silhouettes when scaled down small, cozy gentle preschool mood.

LOCATION: Hollow Oak Village — a village green under a giant ancient oak with a round arched door in its trunk, small round cottages, mushroom-cap lamps, flowers. Palette: bark #6B4A2E, door green #4E7A4A, grass #6FA14C, lamp glow #FFD98A.

TIME OF DAY — DUSK. Sky: full-frame opaque vertical gradient, top orange #F5A96B → bottom peach #FFD9B0; low sun on the RIGHT (about x=1700, y=330) with glow #FFC98A; pink-tinted clouds #FFE0C4 plus three long horizontal cloud streaks #FFD7B8. Light: warm orange wash #F5A96B at ~25% with violet #7A6FB0 falling from the top, long shadows to the left, cottage windows and mushroom lamps glowing brighter.

THE 4 IMAGES:
1. sky — the dusk sky described above, fully opaque edge to edge, nothing else.
2. far — transparent cutout layer: two rolling hill bands (#9CC77E behind, #87B36B in front) with hilltops between y=580 and y=900, plus one round-crowned oak tree at far left (x≈180) and one at far right (x≈2050), trunks #6B4A2E, canopies #4E8A44 with #5FA34F highlights, all warmed by the dusk light. Hills fill down to the bottom edge; everything above them is transparent.
3. mid — transparent cutout layer: grassy ground #7FB069 with darker stripe #6BA05A from y≈860 (61% of height) to the bottom, warmed by dusk light; centered giant hollow oak (two thick trunks #6B4A2E, huge canopy of overlapping circles #4E8A44 with #5FA34F highlights, round arched door #8A6A45 with dark #3A2A1E opening, two round windows glowing #FFD98A); small round cottage left at x≈520 (walls #C98A5B) and right at x≈1720 (walls #B97A6B) with triangular roofs #8A5A3B, doors #5A3D24, round windows glowing #FFE9C8; five mushroom lamps at x=330, 760, 1440, 1960, 2100 (cream stems #E8DCC8, red caps #E2574C with cream dots, glow spots #FFD98A). Everything above the ground line is transparent.
4. near — transparent cutout layer: grass tufts #5E8F4C along y≈1240 (89%) and six simple five-petal flowers (#F0A5C0 and #F7D774) at y=1300–1345, cropped by the bottom edge, in dusk light. Everything else transparent.

RULES: images 2-4 must have a fully transparent background (alpha PNG) containing only their own objects, positioned so all four stack into one continuous scene with a shared horizon and ground line. No characters, animals, people, text, watermarks or logos anywhere. Keep object shapes, colours and layout identical across all four images. If you cannot return four images at once, generate them one at a time with this same prompt.
```

## Stage: night → `assets/locations/hollow_oak_village/night/`

QC: ⬜ size/aspect 11:7 · ⬜ alpha on far/mid/near · ⬜ no text/watermark · ⬜ no characters · ⬜ style match

```text
Generate 4 separate landscape images (each 2200×1400, 11:7 aspect) for a kids' animation background set.

STYLE (binding): flat vector-cartoon children's storybook background art — solid shapes with soft rounded silhouettes, no gradients except light glows and water ripples, every object outlined in dark warm brown #3A2A1E at a consistent weight that scales with the object (about 5px at 1080p), interior patches colour-blocked with NO outline, one soft light key from the upper-left, only 5-7 hues per frame, main shapes readable as silhouettes when scaled down small, cozy gentle preschool mood.

LOCATION: Hollow Oak Village — a village green under a giant ancient oak with a round arched door in its trunk, small round cottages, mushroom-cap lamps, flowers. Palette: bark #6B4A2E, door green #4E7A4A, grass #6FA14C, lamp glow #FFD98A.

TIME OF DAY — NIGHT. Sky: full-frame opaque vertical gradient, top deep indigo #1B2A4A → bottom slate #31486F; crescent moon upper-RIGHT (about x=1850, y=220, disc #F5F0DC with a #1B2A4A bite); exactly 7 small stars #FFF8D8; no clouds. Light: cool blue wash #22304F at ~45% with deep indigo #0B1026 from the top, everything desaturated toward blue, cottage windows and mushroom lamps are the only warm bright light sources with soft #FFD98A glows.

THE 4 IMAGES:
1. sky — the night sky described above, fully opaque edge to edge, nothing else.
2. far — transparent cutout layer: two rolling hill bands (#9CC77E behind, #87B36B in front) desaturated to night blue-green, hilltops between y=580 and y=900, plus one round-crowned oak tree at far left (x≈180) and one at far right (x≈2050), trunks #6B4A2E, canopies darkened. Hills fill down to the bottom edge; everything above them is transparent.
3. mid — transparent cutout layer: grassy ground #7FB069 with darker stripe #6BA05A from y≈860 (61% of height) to the bottom, desaturated to night; centered giant hollow oak (two thick trunks #6B4A2E, huge canopy of overlapping circles #4E8A44 darkened, round arched door #8A6A45 with dark #3A2A1E opening, two round windows glowing #FFD98A); small round cottage left at x≈520 (walls #C98A5B) and right at x≈1720 (walls #B97A6B) with triangular roofs #8A5A3B, doors #5A3D24, round windows glowing #FFE9C8; five mushroom lamps at x=330, 760, 1440, 1960, 2100 (cream stems #E8DCC8, red caps #E2574C with cream dots, each lamp casting a warm #FFD98A pool of light). Everything above the ground line is transparent.
4. near — transparent cutout layer: grass tufts #5E8F4C along y≈1240 (89%) and six simple five-petal flowers (#F0A5C0 and #F7D774) at y=1300–1345, cropped by the bottom edge, in cool night light. Everything else transparent.

RULES: images 2-4 must have a fully transparent background (alpha PNG) containing only their own objects, positioned so all four stack into one continuous scene with a shared horizon and ground line. No characters, animals, people, text, watermarks or logos anywhere. Keep object shapes, colours and layout identical across all four images. If you cannot return four images at once, generate them one at a time with this same prompt.
```
