# Glimmer Meadow (`glimmer_meadow`) — location layer prompts

> Redesign prompts for the 4-layer background set. Tool: **Meta AI** (image gen).
> One fenced prompt per stage; each prompt generates the 4 named layers
> (`sky`, `far`, `mid`, `near`) → 16 images per location, 112 across all 7.
>
> **Outputs**: save each returned image as `<stage>/<layer>.png` (runtime path
> `assets/locations/glimmer_meadow/<stage>/<layer>.png`; wiring into the
> pipeline follows after review).
> **Flag failures**: after each stage tick the QC line and write any failure
> right there (wrong size/aspect, `far`/`mid`/`near` came back opaque instead
> of transparent, text/watermark, characters in frame, style drift) — re-roll
> failed images with the same prompt.
>
> Layer contract: `paint_location("glimmer_meadow", stage)` → `sky` opaque
> base + `far`/`mid`/`near` alpha pastes, each 2200×1400 RGBA (parallax
> 0.35/0.55/1.0/1.12). Palette hexes are binding (`universe/manifest.json`).
> All four stages must read as the same place — identical layout, only sky and
> light change. Glimmer lights are low over the grass by day and drift upward
> at dusk/night.

## Stage: morning → `assets/locations/glimmer_meadow/morning/`

QC: ⬜ size/aspect 11:7 · ⬜ alpha on far/mid/near · ⬜ no text/watermark · ⬜ no characters · ⬜ style match

```text
Generate 4 separate landscape images (each 2200×1400, 11:7 aspect) for a kids' animation background set.

STYLE (binding): flat vector-cartoon children's storybook background art — solid shapes with soft rounded silhouettes, no gradients except light glows and water ripples, every object outlined in dark warm brown #3A2A1E at a consistent weight that scales with the object (about 5px at 1080p), interior patches colour-blocked with NO outline, one soft light key from the upper-left, only 5-7 hues per frame, main shapes readable as silhouettes when scaled down small, cozy gentle preschool mood.

LOCATION: Glimmer Meadow — a wonder-site meadow of tall grass with big flat-topped flowers and small round-crowned trees on a hill line; three soft Glimmer lights (tiny glowing aqua-white orbs) hover low over the grass. Palette: meadow #87B85A, hills #8FC98A, flower petals #F5E6B8 with centers #F0A5C0, Glimmer glow #B8FFE8 with #FFF7C4 cores, grass #5E8F4C.

TIME OF DAY — MORNING. Sky: full-frame opaque vertical gradient, top warm apricot #FFD9A0 → bottom cream #FFF3D6; soft sun disc at upper-LEFT (about x=460, y=300 of 2200×1400) with glow ring #FFE9B8 and white-hot core #FFFBE8; three or four fluffy white clouds. Light: warm gold wash #FFF3D6 at ~18% over the whole scene, gentle long shadows to the right.

THE 4 IMAGES:
1. sky — the morning sky described above, fully opaque edge to edge, nothing else.
2. far — transparent cutout layer: two soft hill bands (#8FC98A behind, #7AB677 in front) with hilltops between y=580 and y=780, plus a row of five small round-crowned trees along y≈840 (trunks #6B4A2E, canopies #4E8A44). Hills and trees fill down to the bottom edge; everything above them is transparent.
3. mid — transparent cutout layer: tall-grass meadow ground #79B268 with darker stripe #6BA05A from y≈820 (59% of height) to the bottom; five big flat-topped flowers spread across x=300–2050 at y=640–720 (cream petals #F5E6B8 around pink centers #F0A5C0, green stems #5E8F4C); three Glimmer lights low over the grass at (420,1160), (980,1220), (1540,1150) — soft aqua-white glowing orbs (#FFF7C4 core, #B8FFE8 halo). Everything above the ground line outside the flowers is transparent.
4. near — transparent cutout layer: grass tufts #5E8F4C along y≈1240 (89%), cropped by the bottom edge. Everything else transparent.

RULES: images 2-4 must have a fully transparent background (alpha PNG) containing only their own objects, positioned so all four stack into one continuous scene with a shared horizon and ground line. No characters, animals, people, text, watermarks or logos anywhere. Keep object shapes, colours and layout identical across all four images. If you cannot return four images at once, generate them one at a time with this same prompt.
```

## Stage: day → `assets/locations/glimmer_meadow/day/`

QC: ⬜ size/aspect 11:7 · ⬜ alpha on far/mid/near · ⬜ no text/watermark · ⬜ no characters · ⬜ style match

```text
Generate 4 separate landscape images (each 2200×1400, 11:7 aspect) for a kids' animation background set.

STYLE (binding): flat vector-cartoon children's storybook background art — solid shapes with soft rounded silhouettes, no gradients except light glows and water ripples, every object outlined in dark warm brown #3A2A1E at a consistent weight that scales with the object (about 5px at 1080p), interior patches colour-blocked with NO outline, one soft light key from the upper-left, only 5-7 hues per frame, main shapes readable as silhouettes when scaled down small, cozy gentle preschool mood.

LOCATION: Glimmer Meadow — a wonder-site meadow of tall grass with big flat-topped flowers and small round-crowned trees on a hill line; three soft Glimmer lights (tiny glowing aqua-white orbs) hover low over the grass. Palette: meadow #87B85A, hills #8FC98A, flower petals #F5E6B8 with centers #F0A5C0, Glimmer glow #B8FFE8 with #FFF7C4 cores, grass #5E8F4C.

TIME OF DAY — DAY. Sky: full-frame opaque vertical gradient, top sky blue #8ED4F5 → bottom pale #CDEFFC; bright sun disc upper-RIGHT (about x=1760, y=200) with glow #FFF6C8 and white-hot core #FFFBE8; fluffy white clouds. Light: clean neutral daylight from the upper-left, no colour wash, short soft shadows.

THE 4 IMAGES:
1. sky — the day sky described above, fully opaque edge to edge, nothing else.
2. far — transparent cutout layer: two soft hill bands (#8FC98A behind, #7AB677 in front) with hilltops between y=580 and y=780, plus a row of five small round-crowned trees along y≈840 (trunks #6B4A2E, canopies #4E8A44). Hills and trees fill down to the bottom edge; everything above them is transparent.
3. mid — transparent cutout layer: tall-grass meadow ground #79B268 with darker stripe #6BA05A from y≈820 (59% of height) to the bottom; five big flat-topped flowers spread across x=300–2050 at y=640–720 (cream petals #F5E6B8 around pink centers #F0A5C0, green stems #5E8F4C); three Glimmer lights low over the grass at (420,1160), (980,1220), (1540,1150) — soft aqua-white glowing orbs (#FFF7C4 core, #B8FFE8 halo). Everything above the ground line outside the flowers is transparent.
4. near — transparent cutout layer: grass tufts #5E8F4C along y≈1240 (89%), cropped by the bottom edge. Everything else transparent.

RULES: images 2-4 must have a fully transparent background (alpha PNG) containing only their own objects, positioned so all four stack into one continuous scene with a shared horizon and ground line. No characters, animals, people, text, watermarks or logos anywhere. Keep object shapes, colours and layout identical across all four images. If you cannot return four images at once, generate them one at a time with this same prompt.
```

## Stage: dusk → `assets/locations/glimmer_meadow/dusk/`

QC: ⬜ size/aspect 11:7 · ⬜ alpha on far/mid/near · ⬜ no text/watermark · ⬜ no characters · ⬜ style match

```text
Generate 4 separate landscape images (each 2200×1400, 11:7 aspect) for a kids' animation background set.

STYLE (binding): flat vector-cartoon children's storybook background art — solid shapes with soft rounded silhouettes, no gradients except light glows and water ripples, every object outlined in dark warm brown #3A2A1E at a consistent weight that scales with the object (about 5px at 1080p), interior patches colour-blocked with NO outline, one soft light key from the upper-left, only 5-7 hues per frame, main shapes readable as silhouettes when scaled down small, cozy gentle preschool mood.

LOCATION: Glimmer Meadow — a wonder-site meadow of tall grass with big flat-topped flowers and small round-crowned trees on a hill line; three soft Glimmer lights (tiny glowing aqua-white orbs) drift upward at dusk. Palette: meadow #87B85A, hills #8FC98A, flower petals #F5E6B8 with centers #F0A5C0, Glimmer glow #B8FFE8 with #FFF7C4 cores, grass #5E8F4C.

TIME OF DAY — DUSK. Sky: full-frame opaque vertical gradient, top orange #F5A96B → bottom peach #FFD9B0; low sun on the RIGHT (about x=1700, y=330) with glow #FFC98A; pink-tinted clouds #FFE0C4 plus three long horizontal cloud streaks #FFD7B8. Light: warm orange wash #F5A96B at ~25% with violet #7A6FB0 falling from the top, long shadows to the left, the far hills carry a subtle dark veil (near-black navy at ~15% opacity), the Glimmer lights glow brighter and sit higher than by day.

THE 4 IMAGES:
1. sky — the dusk sky described above, fully opaque edge to edge, nothing else.
2. far — transparent cutout layer: two soft hill bands (#8FC98A behind, #7AB677 in front) warmed and slightly darkened by a subtle near-black navy veil (~15% opacity), hilltops between y=580 and y=780, plus a row of five small round-crowned trees along y≈840 (trunks #6B4A2E, canopies #4E8A44). Hills and trees fill down to the bottom edge; everything above them is transparent.
3. mid — transparent cutout layer: tall-grass meadow ground #79B268 with darker stripe #6BA05A from y≈820 (59% of height) to the bottom, dusk-warmed; five big flat-topped flowers spread across x=300–2050 at y=640–720 (cream petals #F5E6B8 around pink centers #F0A5C0, green stems #5E8F4C, long shadows to the left); three Glimmer lights drifting mid-height at (420,1010), (980,1060), (1540,980) — bright aqua-white glowing orbs (#FFF7C4 core, wide #B8FFE8 halo). Everything above the ground line outside the flowers is transparent.
4. near — transparent cutout layer: grass tufts #5E8F4C along y≈1240 (89%), cropped by the bottom edge, in dusk light. Everything else transparent.

RULES: images 2-4 must have a fully transparent background (alpha PNG) containing only their own objects, positioned so all four stack into one continuous scene with a shared horizon and ground line. No characters, animals, people, text, watermarks or logos anywhere. Keep object shapes, colours and layout identical across all four images. If you cannot return four images at once, generate them one at a time with this same prompt.
```

## Stage: night → `assets/locations/glimmer_meadow/night/`

QC: ⬜ size/aspect 11:7 · ⬜ alpha on far/mid/near · ⬜ no text/watermark · ⬜ no characters · ⬜ style match

```text
Generate 4 separate landscape images (each 2200×1400, 11:7 aspect) for a kids' animation background set.

STYLE (binding): flat vector-cartoon children's storybook background art — solid shapes with soft rounded silhouettes, no gradients except light glows and water ripples, every object outlined in dark warm brown #3A2A1E at a consistent weight that scales with the object (about 5px at 1080p), interior patches colour-blocked with NO outline, one soft light key from the upper-left, only 5-7 hues per frame, main shapes readable as silhouettes when scaled down small, cozy gentle preschool mood.

LOCATION: Glimmer Meadow — a wonder-site meadow of tall grass with big flat-topped flowers and small round-crowned trees on a hill line; three soft Glimmer lights (tiny glowing aqua-white orbs) drift upward at night. Palette: meadow #87B85A, hills #8FC98A, flower petals #F5E6B8 with centers #F0A5C0, Glimmer glow #B8FFE8 with #FFF7C4 cores, grass #5E8F4C.

TIME OF DAY — NIGHT. Sky: full-frame opaque vertical gradient, top deep indigo #1B2A4A → bottom slate #31486F; crescent moon upper-RIGHT (about x=1850, y=220, disc #F5F0DC with a #1B2A4A bite); exactly 7 small stars #FFF8D8; no clouds. Light: cool blue wash #22304F at ~45% with deep indigo #0B1026 from the top, everything desaturated toward blue, the far hills carry a subtle dark veil (near-black navy at ~15% opacity), the Glimmer lights are the brightest thing in the frame.

THE 4 IMAGES:
1. sky — the night sky described above, fully opaque edge to edge, nothing else.
2. far — transparent cutout layer: two soft hill bands (#8FC98A behind, #7AB677 in front) desaturated to night blue-green under a subtle near-black navy veil (~15% opacity), hilltops between y=580 and y=780, plus a row of five small round-crowned trees along y≈840 (trunks #6B4A2E, canopies #4E8A44 darkened). Hills and trees fill down to the bottom edge; everything above them is transparent.
3. mid — transparent cutout layer: tall-grass meadow ground #79B268 with darker stripe #6BA05A from y≈820 (59% of height) to the bottom, desaturated to night; five big flat-topped flowers spread across x=300–2050 at y=640–720 (cream petals #F5E6B8 around pink centers #F0A5C0, green stems #5E8F4C, both cooled by night light); three Glimmer lights high over the grass at (420,860), (980,900), (1540,830) — brilliant aqua-white glowing orbs (#FFF7C4 core, wide #B8FFE8 halo lighting the grass beneath them). Everything above the ground line outside the flowers is transparent.
4. near — transparent cutout layer: grass tufts #5E8F4C along y≈1240 (89%), cropped by the bottom edge, in cool night light with a faint aqua rim where Glimmer light reaches. Everything else transparent.

RULES: images 2-4 must have a fully transparent background (alpha PNG) containing only their own objects, positioned so all four stack into one continuous scene with a shared horizon and ground line. No characters, animals, people, text, watermarks or logos anywhere. Keep object shapes, colours and layout identical across all four images. If you cannot return four images at once, generate them one at a time with this same prompt.
```
