# CHANNEL_ASSETS.md — Fernwood Friends

> Ready-to-copy prompts for the channel logo and banner (correct dimensions),
> plus copy-paste channel descriptions. Prompts embed the binding brand
> palette and canonical cast from `universe/BRAND_BIBLE.md` and
> `universe/CHARACTER_BIBLE.md`.

**Brand palette** (already embedded in every prompt below):

| role | hex |
|---|---|
| leaf green (primary) | `#5C8A3A` |
| warm amber (accent) | `#E9973A` |
| sky blue | `#7FB3D5` |
| bark brown | `#6B4A2E` |
| cream (paper) | `#FFF3DD` |
| night indigo | `#2E3448` |

**How to use:** paste a prompt block into your image tool (ChatGPT/DALL·E,
Ideogram, Midjourney, Leonardo…). For Midjourney, add the `--ar` flags shown.
Wordmark text renders best in Ideogram or DALL·E; mascot-only prompts work
everywhere.

---

## 1. Channel logo (profile picture)

**Dimensions:** 800 × 800 px (square PNG/JPEG, max 4 MB). YouTube displays it
as a circle — keep everything important centered with a little margin.

### Variant A — wordmark (canonical brand concept)

Best in: Ideogram / DALL·E / ChatGPT (Midjourney renders text unreliably).

```text
Cute rounded kids-channel wordmark logo reading "Fernwood Friends" on two stacked lines: "Fernwood" on top in soft leaf green #5C8A3A, "Friends" below in warm amber #E9973A, a tiny oak leaf replacing the dot on the letter "i", bubbly friendly rounded sans-serif letters, centered inside a cream #FFF3DD circle, flat vector style, clean and readable even at very small sizes, preschool brand logo, nothing else in the image
```

### Variant B — five friends badge (works in any generator)

```text
Circular kids channel logo badge: five cute woodland friends peeking together in one tight happy group — a russet red squirrel wearing a pointed green leaf cap, a stocky grey badger with a black-and-white striped face, a playful chocolate-brown river otter holding a smooth blue pebble, a tiny warm-brown wren wearing an amber scarf, and a gentle old dust-brown hare with round silver spectacles and a green waistcoat — soft rounded 2D children's storybook style, warm friendly smiles, cream #FFF3DD circle background with a leaf green #5C8A3A ring border, flat vector, readable at small size, no text
```

Midjourney: append `--ar 1:1 --stylize 250`

### Variant C — Juni solo (minimal, mascot-first)

```text
Minimal kids channel logo: one cheerful russet red squirrel with an enormous bushy cream-tipped tail and a pointed green leaf cap, head and shoulders, waving hello, centered in a soft cream #FFF3DD circle with a leaf green #5C8A3A border, soft rounded 2D children's storybook style, warm and friendly, flat vector, no text
```

Midjourney: append `--ar 1:1 --stylize 250`

---

## 2. Channel banner (channel art)

**Dimensions:** upload 2560 × 1440 px (min 2048 × 1152, JPEG/PNG, max 6 MB).
The safe area visible on every device is only **1235 × 338 px in the exact
center** — keep the important subject matter in the left third and leave the
center calm; the channel name/logo overlays the center automatically.

### Variant A — golden-hour hill (canonical brand concept)

```text
Wide kids animation channel banner: golden-hour woodland meadow, a great old village oak tree silhouette on the left third, five small friendly woodland animal silhouettes standing together on a grassy hill — squirrel, badger, otter, wren, and hare — warm amber #E9973A and soft sky blue #7FB3D5 gradient evening sky, rolling green hills, a few gentle clouds, soft rounded 2D children's storybook illustration, cozy and calm mood, large quiet empty sky space on the right side, no text, no watermark
```

Midjourney: append `--ar 16:9 --stylize 250`

### Variant B — woodland village at dusk

```text
Wide kids animation channel banner: a cozy woodland village at dusk among big friendly oak trees, round treehouses with warm glowing windows, fireflies drifting, night indigo #2E3448 to warm amber #E9973A sky gradient, a winding soft path with tiny animal silhouettes walking home, soft rounded 2D children's storybook illustration, composition weighted to the left third, calm negative space on the right, no text, no watermark
```

Midjourney: append `--ar 16:9 --stylize 250`

---

## 3. Channel description (copy-paste)

### Short version (fits anywhere, matches video descriptions)

```text
Fernwood Friends: gentle animated woodland adventures for kids ages 4-8. New long stories Monday, Wednesday and Friday - fresh Shorts every Tuesday, Thursday and Saturday.
```

### Full version (YouTube "About" section — safe for made-for-kids channels:
no links, no engagement bait)

```text
Welcome to Fernwood Friends — small friends, big wonder.

Join Juni the squirrel, Bramble the badger, Marlow the otter, Wren the wren, and Willowby the hare in gentle animated woodland adventures made for children ages 4-8.

Every story starts with a small question and ends with a warm feeling — patience, kindness, sharing, trying again. Our friends laugh, explore, and help each other through everyday moments that young viewers recognize from their own lives.

New long stories every Monday, Wednesday and Friday.
Fresh Shorts every Tuesday, Thursday and Saturday.

Cozy, calm, and safe to watch — no scary moments, no loud surprises. Just a soft place to wonder together.

See you in the meadow.
```

---

## Upload checklist (YouTube Studio → Customization → Branding)

1. **Picture** → Variant A, B, or C logo (800 × 800).
2. **Banner image** → Variant A or B (2560 × 1440; center safe area stays calm).
3. **Optional video watermark** → reuse the logo as a transparent-background
   PNG (800 × 800), shown on long videos.
4. **About** → paste the full description version.
5. Audience setting during channel setup: **made for kids** (matches the
   API uploads, which already send `madeForKids: true`).
