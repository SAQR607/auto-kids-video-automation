# Glimmer Cave (`glimmer_cave`) — location layer prompts

> Redesign prompts for the 4-layer background set. Tool: **Meta AI** (image gen).
> One fenced prompt per stage; each prompt generates the 4 named layers
> (`sky`, `far`, `mid`, `near`) → 16 images per location, 112 across all 7.
>
> **Outputs**: save each returned image as `<stage>/<layer>.png` (runtime path
> `assets/locations/glimmer_cave/<stage>/<layer>.png`; wiring into the
> pipeline follows after review).
> **Flag failures**: after each stage tick the QC line and write any failure
> right there (wrong size/aspect, `far`/`mid`/`near` came back opaque instead
> of transparent, text/watermark, characters in frame, style drift) — re-roll
> failed images with the same prompt.
>
> Layer contract: `paint_location("glimmer_cave", stage)` → `sky` opaque
> base + `far`/`mid`/`near` alpha pastes, each 2200×1400 RGBA (parallax
> 0.35/0.55/1.0/1.12). Palette hexes are binding (`universe/manifest.json`).
> All four stages must read as the same place — identical layout, only light
> changes. This is a sealed cave interior: the `sky` base is a plain dark
> gradient the `far` wall covers, and the `near` layer is legitimately empty
> (fully transparent — the pipeline paints no foreground here).

## Stage: morning → `assets/locations/glimmer_cave/morning/`

QC: ⬜ size/aspect 11:7 · ⬜ alpha on far/mid/near · ⬜ no text/watermark · ⬜ no characters · ⬜ style match

```text
Generate 4 separate landscape images (each 2200×1400, 11:7 aspect) for a kids' animation background set.

STYLE (binding): flat vector-cartoon children's storybook background art — solid shapes with soft rounded silhouettes, no gradients except light glows and water ripples, every object outlined in dark warm brown #3A2A1E at a consistent weight that scales with the object (about 5px at 1080p), interior patches colour-blocked with NO outline, one soft light key from the upper-left, only 5-7 hues per frame, main shapes readable as silhouettes when scaled down small, cozy gentle preschool mood.

LOCATION: Glimmer Cave — a sealed hillside cave: root-lattice door, glowing stone heart, aqua light veins pulsing in the walls, concentric stone rings. Palette: cave #2E3448, wall #2E3A4E, veins #7FE3D0 with cores #C8F5FF, heart stone #6E5E8E with glow line #C9B8F0, door #5A4A3A with gold knob #E8C84E.

TIME OF DAY — MORNING. Light: this cave has no daylight — ambient cool cave light with a faint warm gold hint (#FFF3D6 at ~8%) near the entrance, the aqua veins and the heart stone glow steadily, soft mist in the air.

THE 4 IMAGES:
1. sky — base plate only: plain full-frame opaque vertical gradient from #2E3448 (top) to #1B2A4A (bottom), nothing else (it sits behind the cave wall).
2. far — transparent cutout layer: full-frame cave wall #2E3A4E; jagged stalactites hanging down from the top edge (#26303F, varying heights 140–340px) and rounded stalagmites rising from the bottom edge (#39465C), covering the entire canvas edge to edge (this layer is opaque full-frame by design).
3. mid — transparent cutout layer: cave floor #3E4A5E from y≈1020 (73% of height) to the bottom; sealed root-lattice door centre-right at x≈1100 (dark arch #5A4A3A with vertical root slats #43372B, thick bark arc #3A2A1E, gold knob #E8C84E); glowing heart stone left at x≈560, y≈900 (rounded purple-grey stone #6E5E8E, luminous crack #C9B8F0, highlight #E6DDFB, ringed by small orbit dots #B8A8E8); six aqua light veins glowing on the walls (#7FE3D0 halo with #C8F5FF cores) at scattered positions (300,760), (840,640), (1450,700), (1950,660), (1700,880), (180,950); three tiny Glimmer sparkles (#FFF7C4) near the floor at (700,1100), (1600,1150), (1250,1240). Everything above the floor line outside these objects is transparent.
4. near — transparent cutout layer: leave fully transparent — no foreground objects (this location has no near layer). If the tool insists on content, only 3–4 tiny aqua spark motes (#C8F5FF) at the very bottom edge.

RULES: image 4 must be fully transparent (alpha PNG) with no objects; images 2-3 must have a fully transparent background (alpha PNG) containing only their own objects, positioned so all four stack into one continuous scene with a shared horizon and ground line. No characters, animals, people, text, watermarks or logos anywhere. Keep object shapes, colours and layout identical across all four images. If you cannot return four images at once, generate them one at a time with this same prompt.
```

## Stage: day → `assets/locations/glimmer_cave/day/`

QC: ⬜ size/aspect 11:7 · ⬜ alpha on far/mid/near · ⬜ no text/watermark · ⬜ no characters · ⬜ style match

```text
Generate 4 separate landscape images (each 2200×1400, 11:7 aspect) for a kids' animation background set.

STYLE (binding): flat vector-cartoon children's storybook background art — solid shapes with soft rounded silhouettes, no gradients except light glows and water ripples, every object outlined in dark warm brown #3A2A1E at a consistent weight that scales with the object (about 5px at 1080p), interior patches colour-blocked with NO outline, one soft light key from the upper-left, only 5-7 hues per frame, main shapes readable as silhouettes when scaled down small, cozy gentle preschool mood.

LOCATION: Glimmer Cave — a sealed hillside cave: root-lattice door, glowing stone heart, aqua light veins pulsing in the walls, concentric stone rings. Palette: cave #2E3448, wall #2E3A4E, veins #7FE3D0 with cores #C8F5FF, heart stone #6E5E8E with glow line #C9B8F0, door #5A4A3A with gold knob #E8C84E.

TIME OF DAY — DAY. Light: even cool cave ambient (no daylight inside), neutral and clear, the aqua veins and the heart stone glow steadily, short soft shadows under the stones.

THE 4 IMAGES:
1. sky — base plate only: plain full-frame opaque vertical gradient from #2E3448 (top) to #1B2A4A (bottom), nothing else (it sits behind the cave wall).
2. far — transparent cutout layer: full-frame cave wall #2E3A4E; jagged stalactites hanging down from the top edge (#26303F, varying heights 140–340px) and rounded stalagmites rising from the bottom edge (#39465C), covering the entire canvas edge to edge (this layer is opaque full-frame by design).
3. mid — transparent cutout layer: cave floor #3E4A5E from y≈1020 (73% of height) to the bottom; sealed root-lattice door centre-right at x≈1100 (dark arch #5A4A3A with vertical root slats #43372B, thick bark arc #3A2A1E, gold knob #E8C84E); glowing heart stone left at x≈560, y≈900 (rounded purple-grey stone #6E5E8E, luminous crack #C9B8F0, highlight #E6DDFB, ringed by small orbit dots #B8A8E8); six aqua light veins glowing on the walls (#7FE3D0 halo with #C8F5FF cores) at scattered positions (300,760), (840,640), (1450,700), (1950,660), (1700,880), (180,950); three tiny Glimmer sparkles (#FFF7C4) near the floor at (700,1100), (1600,1150), (1250,1240). Everything above the floor line outside these objects is transparent.
4. near — transparent cutout layer: leave fully transparent — no foreground objects (this location has no near layer). If the tool insists on content, only 3–4 tiny aqua spark motes (#C8F5FF) at the very bottom edge.

RULES: image 4 must be fully transparent (alpha PNG) with no objects; images 2-3 must have a fully transparent background (alpha PNG) containing only their own objects, positioned so all four stack into one continuous scene with a shared horizon and ground line. No characters, animals, people, text, watermarks or logos anywhere. Keep object shapes, colours and layout identical across all four images. If you cannot return four images at once, generate them one at a time with this same prompt.
```

## Stage: dusk → `assets/locations/glimmer_cave/dusk/`

QC: ⬜ size/aspect 11:7 · ⬜ alpha on far/mid/near · ⬜ no text/watermark · ⬜ no characters · ⬜ style match

```text
Generate 4 separate landscape images (each 2200×1400, 11:7 aspect) for a kids' animation background set.

STYLE (binding): flat vector-cartoon children's storybook background art — solid shapes with soft rounded silhouettes, no gradients except light glows and water ripples, every object outlined in dark warm brown #3A2A1E at a consistent weight that scales with the object (about 5px at 1080p), interior patches colour-blocked with NO outline, one soft light key from the upper-left, only 5-7 hues per frame, main shapes readable as silhouettes when scaled down small, cozy gentle preschool mood.

LOCATION: Glimmer Cave — a sealed hillside cave: root-lattice door, glowing stone heart, aqua light veins pulsing in the walls, concentric stone rings. Palette: cave #2E3448, wall #2E3A4E, veins #7FE3D0 with cores #C8F5FF, heart stone #6E5E8E with glow line #C9B8F0, door #5A4A3A with gold knob #E8C84E.

TIME OF DAY — DUSK. Light: no daylight inside, but the sealed door leaks a warm orange rim (#F5A96B at ~20%) around its edges; overall frame carries a faint violet dusk cast (#7A6FB0 at ~15%), and the aqua veins and heart stone glow brighter against the dimming walls.

THE 4 IMAGES:
1. sky — base plate only: plain full-frame opaque vertical gradient from #2E3448 (top) to #1B2A4A (bottom), faintly violet-cast, nothing else (it sits behind the cave wall).
2. far — transparent cutout layer: full-frame cave wall #2E3A4E with a faint violet dusk cast; jagged stalactites hanging down from the top edge (#26303F, varying heights 140–340px) and rounded stalagmites rising from the bottom edge (#39465C), covering the entire canvas edge to edge (this layer is opaque full-frame by design).
3. mid — transparent cutout layer: cave floor #3E4A5E from y≈1020 (73% of height) to the bottom, violet-cast; sealed root-lattice door centre-right at x≈1100 (dark arch #5A4A3A with vertical root slats #43372B, thick bark arc #3A2A1E, gold knob #E8C84E, warm orange light rim leaking around its edges); glowing heart stone left at x≈560, y≈900 (rounded purple-grey stone #6E5E8E, bright luminous crack #C9B8F0, highlight #E6DDFB, ringed by small orbit dots #B8A8E8); six aqua light veins glowing strongly on the walls (#7FE3D0 halo with #C8F5FF cores) at scattered positions (300,760), (840,640), (1450,700), (1950,660), (1700,880), (180,950); three tiny Glimmer sparkles (#FFF7C4) near the floor at (700,1100), (1600,1150), (1250,1240). Everything above the floor line outside these objects is transparent.
4. near — transparent cutout layer: leave fully transparent — no foreground objects (this location has no near layer). If the tool insists on content, only 3–4 tiny aqua spark motes (#C8F5FF) at the very bottom edge.

RULES: image 4 must be fully transparent (alpha PNG) with no objects; images 2-3 must have a fully transparent background (alpha PNG) containing only their own objects, positioned so all four stack into one continuous scene with a shared horizon and ground line. No characters, animals, people, text, watermarks or logos anywhere. Keep object shapes, colours and layout identical across all four images. If you cannot return four images at once, generate them one at a time with this same prompt.
```

## Stage: night → `assets/locations/glimmer_cave/night/`

QC: ⬜ size/aspect 11:7 · ⬜ alpha on far/mid/near · ⬜ no text/watermark · ⬜ no characters · ⬜ style match

```text
Generate 4 separate landscape images (each 2200×1400, 11:7 aspect) for a kids' animation background set.

STYLE (binding): flat vector-cartoon children's storybook background art — solid shapes with soft rounded silhouettes, no gradients except light glows and water ripples, every object outlined in dark warm brown #3A2A1E at a consistent weight that scales with the object (about 5px at 1080p), interior patches colour-blocked with NO outline, one soft light key from the upper-left, only 5-7 hues per frame, main shapes readable as silhouettes when scaled down small, cozy gentle preschool mood.

LOCATION: Glimmer Cave — a sealed hillside cave: root-lattice door, glowing stone heart, aqua light veins pulsing in the walls, concentric stone rings. Palette: cave #2E3448, wall #2E3A4E, veins #7FE3D0 with cores #C8F5FF, heart stone #6E5E8E with glow line #C9B8F0, door #5A4A3A with gold knob #E8C84E.

TIME OF DAY — NIGHT (the cave's mystery hour — its own variant only, deep indigo). Light: deep cool wash #22304F at ~45% with indigo #0B1026 from the top, walls darkest at the edges, the aqua veins and the heart stone are the dominant light sources casting soft #7FE3D0 pools on the floor, faint echo ripples of light around the heart.

THE 4 IMAGES:
1. sky — base plate only: plain full-frame opaque vertical gradient from #2E3448 (top) to #1B2A4A (bottom), deepest of the four stages, nothing else (it sits behind the cave wall).
2. far — transparent cutout layer: full-frame cave wall #2E3A4E desaturated and darkened toward night; jagged stalactites hanging down from the top edge (#26303F, varying heights 140–340px) and rounded stalagmites rising from the bottom edge (#39465C), covering the entire canvas edge to edge (this layer is opaque full-frame by design).
3. mid — transparent cutout layer: cave floor #3E4A5E from y≈1020 (73% of height) to the bottom, night-dark with aqua pools of vein light; sealed root-lattice door centre-right at x≈1100 (dark arch #5A4A3A with vertical root slats #43372B, thick bark arc #3A2A1E, gold knob #E8C84E glinting); glowing heart stone left at x≈560, y≈900 (rounded purple-grey stone #6E5E8E, brilliant luminous crack #C9B8F0, highlight #E6DDFB, ringed by small orbit dots #B8A8E8, pulsing halo); six aqua light veins blazing on the walls (#7FE3D0 halo with #C8F5FF cores, widest glow of the four stages) at scattered positions (300,760), (840,640), (1450,700), (1950,660), (1700,880), (180,950); three Glimmer sparkles (#FFF7C4) floating near the floor at (700,1100), (1600,1150), (1250,1240). Everything above the floor line outside these objects is transparent.
4. near — transparent cutout layer: leave fully transparent — no foreground objects (this location has no near layer). If the tool insists on content, only 3–4 tiny aqua spark motes (#C8F5FF) at the very bottom edge.

RULES: image 4 must be fully transparent (alpha PNG) with no objects; images 2-3 must have a fully transparent background (alpha PNG) containing only their own objects, positioned so all four stack into one continuous scene with a shared horizon and ground line. No characters, animals, people, text, watermarks or logos anywhere. Keep object shapes, colours and layout identical across all four images. If you cannot return four images at once, generate them one at a time with this same prompt.
```
