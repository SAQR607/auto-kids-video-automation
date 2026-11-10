# Whispering Stream (`whispering_stream`) — location layer prompts

> Redesign prompts for the 4-layer background set. Tool: **Meta AI** (image gen).
> One fenced prompt per stage; each prompt generates the 4 named layers
> (`sky`, `far`, `mid`, `near`) → 16 images per location, 112 across all 7.
>
> **Outputs**: save each returned image as `<stage>/<layer>.png` (runtime path
> `assets/locations/whispering_stream/<stage>/<layer>.png`; wiring into the
> pipeline follows after review).
> **Flag failures**: after each stage tick the QC line and write any failure
> right there (wrong size/aspect, `far`/`mid`/`near` came back opaque instead
> of transparent, text/watermark, characters in frame, style drift) — re-roll
> failed images with the same prompt.
>
> Layer contract: `paint_location("whispering_stream", stage)` → `sky` opaque
> base + `far`/`mid`/`near` alpha pastes, each 2200×1400 RGBA (parallax
> 0.35/0.55/1.0/1.12). Palette hexes are binding (`universe/manifest.json`).
> All four stages must read as the same place — identical layout, only sky and
> light change.

## Stage: morning → `assets/locations/whispering_stream/morning/`

QC: ⬜ size/aspect 11:7 · ⬜ alpha on far/mid/near · ⬜ no text/watermark · ⬜ no characters · ⬜ style match

```text
Generate 4 separate landscape images (each 2200×1400, 11:7 aspect) for a kids' animation background set.

STYLE (binding): flat vector-cartoon children's storybook background art — solid shapes with soft rounded silhouettes, no gradients except light glows and water ripples, every object outlined in dark warm brown #3A2A1E at a consistent weight that scales with the object (about 5px at 1080p), interior patches colour-blocked with NO outline, one soft light key from the upper-left, only 5-7 hues per frame, main shapes readable as silhouettes when scaled down small, cozy gentle preschool mood.

LOCATION: Whispering Stream — a shallow stream running over pebbles with three flat stepping stones, round-crowned trees on the banks, tall reeds with cattails at the frame edges. Palette: water #5B8FB9 and #7EC8E3 with pale ripples #BCE8F5, stones #9A8F7E, reeds #5E8F4C with cattail heads #8A6A45, grass #6FA14C.

TIME OF DAY — MORNING. Sky: full-frame opaque vertical gradient, top warm apricot #FFD9A0 → bottom cream #FFF3D6; soft sun disc at upper-LEFT (about x=460, y=300 of 2200×1400) with glow ring #FFE9B8 and white-hot core #FFFBE8; three or four fluffy white clouds. Light: warm gold wash #FFF3D6 at ~18% over the whole scene, gentle long shadows to the right, soft glints on the water.

THE 4 IMAGES:
1. sky — the morning sky described above, fully opaque edge to edge, nothing else.
2. far — transparent cutout layer: two soft rolling hill bands (#A8C98F behind, #93B67C in front) with hilltops between y=580 and y=900. Hills fill down to the bottom edge; everything above them is transparent.
3. mid — transparent cutout layer: grassy bank #7FB069 with darker stripe #6BA05A from y≈640 (46% of height) to the bottom; a wide shallow stream winding across the full width roughly between y=700 and y=1040 (water #7EC8E3, pale ripple arcs #BCE8F5); four round-crowned trees (x≈320 and x≈1880 taller, x≈1500 and x≈700 shorter, trunks #6B4A2E, canopies #4E8A44 with #5FA34F highlights); three flat grey stepping stones #9A8F7E at y≈1060 (76%) on x≈520, x≈1080, x≈1660. Everything above the bank line outside the stream and trees is transparent.
4. near — transparent cutout layer: tall reed clusters with cattail heads at the far left (x≈120) and far right (x≈2000), bases at y≈1150–1180, plus grass tufts #5E8F4C along y≈1300. Everything else transparent.

RULES: images 2-4 must have a fully transparent background (alpha PNG) containing only their own objects, positioned so all four stack into one continuous scene with a shared horizon and ground line. No characters, animals, people, text, watermarks or logos anywhere. Keep object shapes, colours and layout identical across all four images. If you cannot return four images at once, generate them one at a time with this same prompt.
```

## Stage: day → `assets/locations/whispering_stream/day/`

QC: ⬜ size/aspect 11:7 · ⬜ alpha on far/mid/near · ⬜ no text/watermark · ⬜ no characters · ⬜ style match

```text
Generate 4 separate landscape images (each 2200×1400, 11:7 aspect) for a kids' animation background set.

STYLE (binding): flat vector-cartoon children's storybook background art — solid shapes with soft rounded silhouettes, no gradients except light glows and water ripples, every object outlined in dark warm brown #3A2A1E at a consistent weight that scales with the object (about 5px at 1080p), interior patches colour-blocked with NO outline, one soft light key from the upper-left, only 5-7 hues per frame, main shapes readable as silhouettes when scaled down small, cozy gentle preschool mood.

LOCATION: Whispering Stream — a shallow stream running over pebbles with three flat stepping stones, round-crowned trees on the banks, tall reeds with cattails at the frame edges. Palette: water #5B8FB9 and #7EC8E3 with pale ripples #BCE8F5, stones #9A8F7E, reeds #5E8F4C with cattail heads #8A6A45, grass #6FA14C.

TIME OF DAY — DAY. Sky: full-frame opaque vertical gradient, top sky blue #8ED4F5 → bottom pale #CDEFFC; bright sun disc upper-RIGHT (about x=1760, y=200) with glow #FFF6C8 and white-hot core #FFFBE8; fluffy white clouds. Light: clean neutral daylight from the upper-left, no colour wash, short soft shadows, sparkle highlights on the water.

THE 4 IMAGES:
1. sky — the day sky described above, fully opaque edge to edge, nothing else.
2. far — transparent cutout layer: two soft rolling hill bands (#A8C98F behind, #93B67C in front) with hilltops between y=580 and y=900. Hills fill down to the bottom edge; everything above them is transparent.
3. mid — transparent cutout layer: grassy bank #7FB069 with darker stripe #6BA05A from y≈640 (46% of height) to the bottom; a wide shallow stream winding across the full width roughly between y=700 and y=1040 (water #7EC8E3, pale ripple arcs #BCE8F5); four round-crowned trees (x≈320 and x≈1880 taller, x≈1500 and x≈700 shorter, trunks #6B4A2E, canopies #4E8A44 with #5FA34F highlights); three flat grey stepping stones #9A8F7E at y≈1060 (76%) on x≈520, x≈1080, x≈1660. Everything above the bank line outside the stream and trees is transparent.
4. near — transparent cutout layer: tall reed clusters with cattail heads at the far left (x≈120) and far right (x≈2000), bases at y≈1150–1180, plus grass tufts #5E8F4C along y≈1300. Everything else transparent.

RULES: images 2-4 must have a fully transparent background (alpha PNG) containing only their own objects, positioned so all four stack into one continuous scene with a shared horizon and ground line. No characters, animals, people, text, watermarks or logos anywhere. Keep object shapes, colours and layout identical across all four images. If you cannot return four images at once, generate them one at a time with this same prompt.
```

## Stage: dusk → `assets/locations/whispering_stream/dusk/`

QC: ⬜ size/aspect 11:7 · ⬜ alpha on far/mid/near · ⬜ no text/watermark · ⬜ no characters · ⬜ style match

```text
Generate 4 separate landscape images (each 2200×1400, 11:7 aspect) for a kids' animation background set.

STYLE (binding): flat vector-cartoon children's storybook background art — solid shapes with soft rounded silhouettes, no gradients except light glows and water ripples, every object outlined in dark warm brown #3A2A1E at a consistent weight that scales with the object (about 5px at 1080p), interior patches colour-blocked with NO outline, one soft light key from the upper-left, only 5-7 hues per frame, main shapes readable as silhouettes when scaled down small, cozy gentle preschool mood.

LOCATION: Whispering Stream — a shallow stream running over pebbles with three flat stepping stones, round-crowned trees on the banks, tall reeds with cattails at the frame edges. Palette: water #5B8FB9 and #7EC8E3 with pale ripples #BCE8F5, stones #9A8F7E, reeds #5E8F4C with cattail heads #8A6A45, grass #6FA14C.

TIME OF DAY — DUSK. Sky: full-frame opaque vertical gradient, top orange #F5A96B → bottom peach #FFD9B0; low sun on the RIGHT (about x=1700, y=330) with glow #FFC98A; pink-tinted clouds #FFE0C4 plus three long horizontal cloud streaks #FFD7B8. Light: warm orange wash #F5A96B at ~25% with violet #7A6FB0 falling from the top, long shadows to the left, warm reflections on the water.

THE 4 IMAGES:
1. sky — the dusk sky described above, fully opaque edge to edge, nothing else.
2. far — transparent cutout layer: two soft rolling hill bands (#A8C98F behind, #93B67C in front) with hilltops between y=580 and y=900, warmed by dusk light. Hills fill down to the bottom edge; everything above them is transparent.
3. mid — transparent cutout layer: grassy bank #7FB069 with darker stripe #6BA05A from y≈640 (46% of height) to the bottom, dusk-warmed; a wide shallow stream winding across the full width roughly between y=700 and y=1040 (water #7EC8E3 with warm orange sky reflections between the pale ripple arcs #BCE8F5); four round-crowned trees (x≈320 and x≈1880 taller, x≈1500 and x≈700 shorter, trunks #6B4A2E, canopies #4E8A44 with #5FA34F highlights, long shadows to the left); three flat grey stepping stones #9A8F7E at y≈1060 (76%) on x≈520, x≈1080, x≈1660. Everything above the bank line outside the stream and trees is transparent.
4. near — transparent cutout layer: tall reed clusters with cattail heads at the far left (x≈120) and far right (x≈2000), bases at y≈1150–1180, plus grass tufts #5E8F4C along y≈1300, in dusk light. Everything else transparent.

RULES: images 2-4 must have a fully transparent background (alpha PNG) containing only their own objects, positioned so all four stack into one continuous scene with a shared horizon and ground line. No characters, animals, people, text, watermarks or logos anywhere. Keep object shapes, colours and layout identical across all four images. If you cannot return four images at once, generate them one at a time with this same prompt.
```

## Stage: night → `assets/locations/whispering_stream/night/`

QC: ⬜ size/aspect 11:7 · ⬜ alpha on far/mid/near · ⬜ no text/watermark · ⬜ no characters · ⬜ style match

```text
Generate 4 separate landscape images (each 2200×1400, 11:7 aspect) for a kids' animation background set.

STYLE (binding): flat vector-cartoon children's storybook background art — solid shapes with soft rounded silhouettes, no gradients except light glows and water ripples, every object outlined in dark warm brown #3A2A1E at a consistent weight that scales with the object (about 5px at 1080p), interior patches colour-blocked with NO outline, one soft light key from the upper-left, only 5-7 hues per frame, main shapes readable as silhouettes when scaled down small, cozy gentle preschool mood.

LOCATION: Whispering Stream — a shallow stream running over pebbles with three flat stepping stones, round-crowned trees on the banks, tall reeds with cattails at the frame edges. Palette: water #5B8FB9 and #7EC8E3 with pale ripples #BCE8F5, stones #9A8F7E, reeds #5E8F4C with cattail heads #8A6A45, grass #6FA14C.

TIME OF DAY — NIGHT. Sky: full-frame opaque vertical gradient, top deep indigo #1B2A4A → bottom slate #31486F; crescent moon upper-RIGHT (about x=1850, y=220, disc #F5F0DC with a #1B2A4A bite); exactly 7 small stars #FFF8D8; no clouds. Light: cool blue wash #22304F at ~45% with deep indigo #0B1026 from the top, everything desaturated toward blue, moonlight glinting pale on the water.

THE 4 IMAGES:
1. sky — the night sky described above, fully opaque edge to edge, nothing else.
2. far — transparent cutout layer: two soft rolling hill bands (#A8C98F behind, #93B67C in front) desaturated to night blue-green, hilltops between y=580 and y=900. Hills fill down to the bottom edge; everything above them is transparent.
3. mid — transparent cutout layer: grassy bank #7FB069 with darker stripe #6BA05A from y≈640 (46% of height) to the bottom, desaturated to night; a wide shallow stream winding across the full width roughly between y=700 and y=1040 (water #7EC8E3 darkened to night blue with pale #BCE8F5 ripple arcs catching moonlight); four round-crowned trees (x≈320 and x≈1880 taller, x≈1500 and x≈700 shorter, trunks #6B4A2E, canopies #4E8A44 darkened); three flat grey stepping stones #9A8F7E at y≈1060 (76%) on x≈520, x≈1080, x≈1660. Everything above the bank line outside the stream and trees is transparent.
4. near — transparent cutout layer: tall reed clusters with cattail heads at the far left (x≈120) and far right (x≈2000), bases at y≈1150–1180, plus grass tufts #5E8F4C along y≈1300, in cool night light. Everything else transparent.

RULES: images 2-4 must have a fully transparent background (alpha PNG) containing only their own objects, positioned so all four stack into one continuous scene with a shared horizon and ground line. No characters, animals, people, text, watermarks or logos anywhere. Keep object shapes, colours and layout identical across all four images. If you cannot return four images at once, generate them one at a time with this same prompt.
```
