# Mossy Ravine (`mossy_ravine`) — location layer prompts

> Redesign prompts for the 4-layer background set. Tool: **Meta AI** (image gen).
> One fenced prompt per stage; each prompt generates the 4 named layers
> (`sky`, `far`, `mid`, `near`) → 16 images per location, 112 across all 7.
>
> **Outputs**: save each returned image as `<stage>/<layer>.png` (runtime path
> `assets/locations/mossy_ravine/<stage>/<layer>.png`; wiring into the
> pipeline follows after review).
> **Flag failures**: after each stage tick the QC line and write any failure
> right there (wrong size/aspect, `far`/`mid`/`near` came back opaque instead
> of transparent, text/watermark, characters in frame, style drift) — re-roll
> failed images with the same prompt.
>
> Layer contract: `paint_location("mossy_ravine", stage)` → `sky` opaque
> base + `far`/`mid`/`near` alpha pastes, each 2200×1400 RGBA (parallax
> 0.35/0.55/1.0/1.12). Palette hexes are binding (`universe/manifest.json`).
> All four stages must read as the same place — identical layout, only sky and
> light change. The `near` layer's mist is the one intentionally
> semi-transparent element (white at ~40–55% alpha).

## Stage: morning → `assets/locations/mossy_ravine/morning/`

QC: ⬜ size/aspect 11:7 · ⬜ alpha on far/mid/near · ⬜ no text/watermark · ⬜ no characters · ⬜ style match

```text
Generate 4 separate landscape images (each 2200×1400, 11:7 aspect) for a kids' animation background set.

STYLE (binding): flat vector-cartoon children's storybook background art — solid shapes with soft rounded silhouettes, no gradients except light glows and water ripples, every object outlined in dark warm brown #3A2A1E at a consistent weight that scales with the object (about 5px at 1080p), interior patches colour-blocked with NO outline, one soft light key from the upper-left, only 5-7 hues per frame, main shapes readable as silhouettes when scaled down small, cozy gentle preschool mood.

LOCATION: Mossy Ravine & Old Root Bridge — a rocky cut with mossy cliff walls, an old bridge made of two arched roots with rope lashings spanning the gap, small trees on the rim, drifting mist low in the ravine. Palette: cliff #7E8A7A, rock #59645A, moss #4F7A45 and #6FA35E, bridge wood #8A6A45, rope #A98A5B, mist #DCE7EA.

TIME OF DAY — MORNING. Sky: full-frame opaque vertical gradient, top warm apricot #FFD9A0 → bottom cream #FFF3D6; soft sun disc at upper-LEFT (about x=460, y=300 of 2200×1400) with glow ring #FFE9B8 and white-hot core #FFFBE8; three or four fluffy white clouds. Light: warm gold wash #FFF3D6 at ~18% over the whole scene, gentle long shadows to the right, mist glowing faintly gold.

THE 4 IMAGES:
1. sky — the morning sky described above, fully opaque edge to edge, nothing else.
2. far — transparent cutout layer: full-frame grey-green cliff wall #7E8A7A with a darker ridge silhouette #6E7A6C across the top third (peaks between y=260 and y=350), covering the entire canvas edge to edge (this layer is opaque full-frame by design; the sky shows only if the wall is cut away).
3. mid — transparent cutout layer: ravine floor #6E7E62 with darker stripe #5E6E52 from y≈980 (70% of height) to the bottom; two dark rock masses #59645A hugging the far left and far right edges (cliff faces rising out of frame); old root bridge arcing across the centre — thick arc #8A6A45 spanning x≈600–1600 with apex at y≈600, vertical rope lashings #6B4A2E along its length, two thick root posts #5A3D24 at the ends; two round-crowned trees at x≈300 and x≈1900 (trunks #6B4A2E, canopies #4E8A44); three moss patches #6FA35E / #5E8F4C on the cliff faces at (680,620), (1520,600), (420,430). Everything above the floor line outside these objects is transparent.
4. near — transparent cutout layer: two or three soft semi-transparent white mist banks (#DCE7EA at ~40–55% alpha) drifting across y≈1180 (84%), long and low, plus nothing else. Everything else fully transparent.

RULES: images 2-4 must have a fully transparent background (alpha PNG) containing only their own objects, positioned so all four stack into one continuous scene with a shared horizon and ground line. No characters, animals, people, text, watermarks or logos anywhere. Keep object shapes, colours and layout identical across all four images. If you cannot return four images at once, generate them one at a time with this same prompt.
```

## Stage: day → `assets/locations/mossy_ravine/day/`

QC: ⬜ size/aspect 11:7 · ⬜ alpha on far/mid/near · ⬜ no text/watermark · ⬜ no characters · ⬜ style match

```text
Generate 4 separate landscape images (each 2200×1400, 11:7 aspect) for a kids' animation background set.

STYLE (binding): flat vector-cartoon children's storybook background art — solid shapes with soft rounded silhouettes, no gradients except light glows and water ripples, every object outlined in dark warm brown #3A2A1E at a consistent weight that scales with the object (about 5px at 1080p), interior patches colour-blocked with NO outline, one soft light key from the upper-left, only 5-7 hues per frame, main shapes readable as silhouettes when scaled down small, cozy gentle preschool mood.

LOCATION: Mossy Ravine & Old Root Bridge — a rocky cut with mossy cliff walls, an old bridge made of two arched roots with rope lashings spanning the gap, small trees on the rim, drifting mist low in the ravine. Palette: cliff #7E8A7A, rock #59645A, moss #4F7A45 and #6FA35E, bridge wood #8A6A45, rope #A98A5B, mist #DCE7EA.

TIME OF DAY — DAY. Sky: full-frame opaque vertical gradient, top sky blue #8ED4F5 → bottom pale #CDEFFC; bright sun disc upper-RIGHT (about x=1760, y=200) with glow #FFF6C8 and white-hot core #FFFBE8; fluffy white clouds. Light: clean neutral daylight from the upper-left, no colour wash, short soft shadows, mist pale white.

THE 4 IMAGES:
1. sky — the day sky described above, fully opaque edge to edge, nothing else.
2. far — transparent cutout layer: full-frame grey-green cliff wall #7E8A7A with a darker ridge silhouette #6E7A6C across the top third (peaks between y=260 and y=350), covering the entire canvas edge to edge (this layer is opaque full-frame by design; the sky shows only if the wall is cut away).
3. mid — transparent cutout layer: ravine floor #6E7E62 with darker stripe #5E6E52 from y≈980 (70% of height) to the bottom; two dark rock masses #59645A hugging the far left and far right edges (cliff faces rising out of frame); old root bridge arcing across the centre — thick arc #8A6A45 spanning x≈600–1600 with apex at y≈600, vertical rope lashings #6B4A2E along its length, two thick root posts #5A3D24 at the ends; two round-crowned trees at x≈300 and x≈1900 (trunks #6B4A2E, canopies #4E8A44); three moss patches #6FA35E / #5E8F4C on the cliff faces at (680,620), (1520,600), (420,430). Everything above the floor line outside these objects is transparent.
4. near — transparent cutout layer: two or three soft semi-transparent white mist banks (#DCE7EA at ~40–55% alpha) drifting across y≈1180 (84%), long and low, plus nothing else. Everything else fully transparent.

RULES: images 2-4 must have a fully transparent background (alpha PNG) containing only their own objects, positioned so all four stack into one continuous scene with a shared horizon and ground line. No characters, animals, people, text, watermarks or logos anywhere. Keep object shapes, colours and layout identical across all four images. If you cannot return four images at once, generate them one at a time with this same prompt.
```

## Stage: dusk → `assets/locations/mossy_ravine/dusk/`

QC: ⬜ size/aspect 11:7 · ⬜ alpha on far/mid/near · ⬜ no text/watermark · ⬜ no characters · ⬜ style match

```text
Generate 4 separate landscape images (each 2200×1400, 11:7 aspect) for a kids' animation background set.

STYLE (binding): flat vector-cartoon children's storybook background art — solid shapes with soft rounded silhouettes, no gradients except light glows and water ripples, every object outlined in dark warm brown #3A2A1E at a consistent weight that scales with the object (about 5px at 1080p), interior patches colour-blocked with NO outline, one soft light key from the upper-left, only 5-7 hues per frame, main shapes readable as silhouettes when scaled down small, cozy gentle preschool mood.

LOCATION: Mossy Ravine & Old Root Bridge — a rocky cut with mossy cliff walls, an old bridge made of two arched roots with rope lashings spanning the gap, small trees on the rim, drifting mist low in the ravine. Palette: cliff #7E8A7A, rock #59645A, moss #4F7A45 and #6FA35E, bridge wood #8A6A45, rope #A98A5B, mist #DCE7EA.

TIME OF DAY — DUSK. Sky: full-frame opaque vertical gradient, top orange #F5A96B → bottom peach #FFD9B0; low sun on the RIGHT (about x=1700, y=330) with glow #FFC98A; pink-tinted clouds #FFE0C4 plus three long horizontal cloud streaks #FFD7B8. Light: warm orange wash #F5A96B at ~25% with violet #7A6FB0 falling from the top, long shadows to the left, mist picking up a warm rose tint.

THE 4 IMAGES:
1. sky — the dusk sky described above, fully opaque edge to edge, nothing else.
2. far — transparent cutout layer: full-frame grey-green cliff wall #7E8A7A warmed by the orange dusk wash with a darker ridge silhouette #6E7A6C across the top third (peaks between y=260 and y=350), covering the entire canvas edge to edge (this layer is opaque full-frame by design).
3. mid — transparent cutout layer: ravine floor #6E7E62 with darker stripe #5E6E52 from y≈980 (70% of height) to the bottom, dusk-warmed with long shadows to the left; two dark rock masses #59645A hugging the far left and far right edges (cliff faces rising out of frame); old root bridge arcing across the centre — thick arc #8A6A45 spanning x≈600–1600 with apex at y≈600, vertical rope lashings #6B4A2E along its length, two thick root posts #5A3D24 at the ends; two round-crowned trees at x≈300 and x≈1900 (trunks #6B4A2E, canopies #4E8A44 warmed by dusk); three moss patches #6FA35E / #5E8F4C on the cliff faces at (680,620), (1520,600), (420,430). Everything above the floor line outside these objects is transparent.
4. near — transparent cutout layer: two or three soft semi-transparent white mist banks (#DCE7EA at ~40–55% alpha, faintly rose-tinted by dusk) drifting across y≈1180 (84%), long and low, plus nothing else. Everything else fully transparent.

RULES: images 2-4 must have a fully transparent background (alpha PNG) containing only their own objects, positioned so all four stack into one continuous scene with a shared horizon and ground line. No characters, animals, people, text, watermarks or logos anywhere. Keep object shapes, colours and layout identical across all four images. If you cannot return four images at once, generate them one at a time with this same prompt.
```

## Stage: night → `assets/locations/mossy_ravine/night/`

QC: ⬜ size/aspect 11:7 · ⬜ alpha on far/mid/near · ⬜ no text/watermark · ⬜ no characters · ⬜ style match

```text
Generate 4 separate landscape images (each 2200×1400, 11:7 aspect) for a kids' animation background set.

STYLE (binding): flat vector-cartoon children's storybook background art — solid shapes with soft rounded silhouettes, no gradients except light glows and water ripples, every object outlined in dark warm brown #3A2A1E at a consistent weight that scales with the object (about 5px at 1080p), interior patches colour-blocked with NO outline, one soft light key from the upper-left, only 5-7 hues per frame, main shapes readable as silhouettes when scaled down small, cozy gentle preschool mood.

LOCATION: Mossy Ravine & Old Root Bridge — a rocky cut with mossy cliff walls, an old bridge made of two arched roots with rope lashings spanning the gap, small trees on the rim, drifting mist low in the ravine. Palette: cliff #7E8A7A, rock #59645A, moss #4F7A45 and #6FA35E, bridge wood #8A6A45, rope #A98A5B, mist #DCE7EA.

TIME OF DAY — NIGHT. Sky: full-frame opaque vertical gradient, top deep indigo #1B2A4A → bottom slate #31486F; crescent moon upper-RIGHT (about x=1850, y=220, disc #F5F0DC with a #1B2A4A bite); exactly 7 small stars #FFF8D8; no clouds. Light: cool blue wash #22304F at ~45% with deep indigo #0B1026 from the top, everything desaturated toward blue, mist glowing faintly pale blue in the moonlight.

THE 4 IMAGES:
1. sky — the night sky described above, fully opaque edge to edge, nothing else.
2. far — transparent cutout layer: full-frame grey-green cliff wall #7E8A7A desaturated to night blue-grey with a darker ridge silhouette #6E7A6C across the top third (peaks between y=260 and y=350), covering the entire canvas edge to edge (this layer is opaque full-frame by design).
3. mid — transparent cutout layer: ravine floor #6E7E62 with darker stripe #5E6E52 from y≈980 (70% of height) to the bottom, desaturated to night; two dark rock masses #59645A hugging the far left and far right edges (cliff faces rising out of frame); old root bridge arcing across the centre — thick arc #8A6A45 spanning x≈600–1600 with apex at y≈600, vertical rope lashings #6B4A2E along its length, two thick root posts #5A3D24 at the ends, moonlit along its top edge; two round-crowned trees at x≈300 and x≈1900 (trunks #6B4A2E, canopies #4E8A44 darkened); three moss patches #6FA35E / #5E8F4C on the cliff faces at (680,620), (1520,600), (420,430), cooled by night light. Everything above the floor line outside these objects is transparent.
4. near — transparent cutout layer: two or three soft semi-transparent white mist banks (#DCE7EA at ~40–55% alpha, faintly blue in the moonlight) drifting across y≈1180 (84%), long and low, plus nothing else. Everything else fully transparent.

RULES: images 2-4 must have a fully transparent background (alpha PNG) containing only their own objects, positioned so all four stack into one continuous scene with a shared horizon and ground line. No characters, animals, people, text, watermarks or logos anywhere. Keep object shapes, colours and layout identical across all four images. If you cannot return four images at once, generate them one at a time with this same prompt.
```
