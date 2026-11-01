# YOUTUBE GROWTH PLAYBOOK — Fernwood Friends

> **Purpose:** keywords + channel settings + metadata formulas that win **views → reach → subscribers**.
> **Scope:** YouTube only (longs + Shorts). Audience: **parents first**, kids engage. **US English.**
> **Auto-apply:** every upload automatically uses §5 via `app/youtube/metadata.py` — no manual work.
> **Compliance:** all videos are **made for kids** (COPPA). No engagement bait, no links, no comments — see §7.
> Related: `CHANNEL_ASSETS.md` (logo/banner), `universe/BRAND_BIBLE.md` (brand voice), `OPERATIONS.md` (posting ops).

---

## 1. Strategy at a glance

| Lever | Decision |
|---|---|
| Who searches | **Parents** type the queries ("bedtime stories for kids ages 4-8"). Every title/description/tag speaks to them. |
| Who watches | **Kids 4-8** drive the real ranking signals: watch time, sessions, replays. Content stays calm/repeatable. |
| Language | US English keywords only (largest single search market). |
| Discovery mix | Search (parents) + Suggested/Browse (YouTube finds more kids like the current viewer) + YouTube Kids (made-for-kids channel). |
| Cadence | Mon/Wed/Fri longs, Tue/Thu/Sat Shorts, all **16:00 UTC** — consistency itself is a ranking signal. |
| Growth engine | **Search-optimized titles** + **keyword-rich first line of description** + **playlists for sessions** + **Shorts funnel into longs**. |
| Hard limits | Made-for-kids disables comments, end screens, cards. We cannot use "engage more" tactics — see §7. Growth comes from metadata + watch time. |

---

## 2. Benchmark channels (what works in this niche)

| Channel | Scale | Pattern worth copying |
|---|---|---|
| **Koala Moon – Kids Bedtime Stories** | 257K subs, 534 videos | Title formula: `hook + emotion keyword + category keyword + character`, e.g. *"The Pup Cup That Got Stuck 🐶 Cozy Autumn Bedtime Story 💤 with Hector & Sunny"*. Repeats the exact search phrase **"Bedtime Story for Kids"** in almost every title. Description = a keyword-rich paragraph targeting interests ("children who love tractors…"). |
| **Bedtime Story (BedtimeStory.TV)** | 224K subs, 58 videos | Minimalist title: `Story Name - Bedtime Story (Brand)` — brand suffix on every video; huge per-video view counts (10M+) from **search** years after upload → evergreen catalog. |
| **T-Series Kids Hut** (Kids Bedtime Stories playlist) | mega | Title keyword-stacking with pipes: `RAPUNZEL English Kids Story Animation | Fairy Tales and Bedtime Stories - Full Story`. Exact-match phrases: "Moral Stories", "Short Stories for Kids in English", "Animated Stories for Kids". |
| **Bandou Stories** | 125 subs (micro) | Disciplined suffix on every upload: *"- Bedtime Stories for Kids (Ages 2–6)"* + **compilation videos** ("Compilation – Classic Fables") to manufacture long watch time. |
| **Cocomelon – Nursery Rhymes** | 203M subs | Most-searched kids channel in the US (2025 research). Proof that **keyword-clear, episode-based, highly consistent** kids content scales on search + browse. |

**Extracted rules:**
1. Put the **exact search phrase** ("Bedtime Story for Kids" / "Gentle Story for Kids") in **every title** (first ~60 chars preferred).
2. **Brand suffix** on every title → series recognition + branded search over time.
3. Description opens with a **keyword paragraph** (who it's for, what's in it, themes) — not a greeting.
4. **Compilations** are the long-watch-time hack — future pipeline feature once 10+ longs exist (§9).
5. Consistency beats brilliance: all five channels post on a fixed schedule; Koala Moon's 534 videos = cadence × years.

---

## 3. Channel settings — one-time checklist (YouTube Studio)

- [ ] **Name:** `Fernwood Friends` · **Handle:** `@fernwoodfriends` (or current) — name already contains no keyword; that's fine, the *About* and channel keywords carry them.
- [ ] **Channel keywords** (Settings → Basic info → Keywords) — paste this exact list (fits the 500-char limit):

  ```text
  fernwood friends, bedtime stories for kids, animated stories for kids, stories for kids ages 4-8, preschool stories, kids animation, wholesome kids videos, gentle bedtime story, woodland animals cartoon, kids cartoon, friendship stories for kids, calming stories for kids, kids stories in english, social emotional learning for kids, kindergarten stories
  ```

- [ ] **Description / About** (Settings → Basic info → Description) — paste:

  ```text
  Fernwood Friends is a gentle animated story series for kids ages 4-8. Join Juni, Bramble and the woodland animals of the meadow for calm bedtime stories about friendship, kindness and patience — soft colors, cozy music and happy endings made for preschool and kindergarten viewers.

  New long stories every Monday, Wednesday and Friday at 16:00 UTC. New shorts every Tuesday, Thursday and Saturday at 16:00 UTC.
  ```

- [ ] **Made for kids (advanced settings):** channel-level flag = **"Yes, set this channel as made for kids"** — matches the per-video flag the API already sets.
- [ ] **Upload defaults** (Settings → Upload defaults): Category **Film & Animation**, Language **English (US)**, License **Standard YouTube**, Visibility **Public**, "Set this video as made for kids" **checked**. (Pipeline overrides visibility for tests — defaults are a safety net.)
- [ ] **Subtitles:** leave YouTube's **automatic English captions ON** — captions are indexed by search, they add keyword surface for free.
- [ ] **Playlists** (see §6.1): create now — `Season 1 — Full Stories`, `Season 1 — Shorts`.
- [ ] **Branding:** logo 800×800 + banner 2560×1440 per `CHANNEL_ASSETS.md`.
- [ ] **Comments:** off (auto, made-for-kids) — expected, not fixable, see §7.
- [ ] **End screens / Cards:** unavailable for made-for-kids — playlists + Shorts replace them (§6).

---

## 4. Keyword banks (US English)

### 4.1 High-volume search phrases (target these in titles/descriptions)

| Tier | Phrases |
|---|---|
| Primary (put in **every** video) | bedtime stories for kids · bedtime story for kids · animated stories for kids · stories for kids ages 4-8 · preschool stories |
| Secondary (rotate, 1-2 per video) | gentle bedtime story · calming bedtime story for kids · story for kids · kids cartoon · wholesome kids videos · kids animation · stories for kids in english · friendship stories for kids · kindness stories for kids · forest animals cartoon for kids |
| Long-tail (niche wins) | social emotional learning for kids · stories that teach kindness · patience stories for kids · gentle stories for kids ages 4-8 · quiet bedtime story for toddlers |

### 4.2 Core tag bank — live in code (`app/youtube/metadata.py` → `CORE_TAGS`)

```text
bedtime stories for kids · animated stories for kids · fernwood friends · preschool stories ·
kids stories · gentle stories for kids · stories for kids · kids animation · wholesome kids video ·
calming bedtime story · kids cartoon · ages 4-8 · woodland animals · friendship stories for kids
```

The first 6 are **priority tags** — always included first; episode-specific tags from the generator fill the rest (merged + deduped + capped to YouTube's 30-tag / ~500-char total limit).

### 4.3 Hashtags (last line of every description; first 3 display above the title)

```text
#FernwoodFriends #BedtimeStoriesForKids #AnimatedStoriesForKids #KidsStories
Shorts also start the block with #shorts.
```

### 4.4 Dynamic per-episode keywords

The episode generator (`app/content/prompts.py`) writes 8-15 tags per package — 7 core + 5-8 **episode-specific** (theme, characters, learning spine: "kindness", "patience", "sharing"). Those unique tags are what let a specific video rank on its own topic; the core bank keeps every video anchored to the big searches.

---

## 5. Per-video metadata — what the pipeline applies automatically

### 5.1 Title formula (≤70 chars, QC-enforced)

```text
<curiosity hook> | <search phrase> | Fernwood Friends S1E##

Examples:
A Quiet Kindness | Bedtime Story for Kids | Fernwood Friends S1E02
Juni's Bright Idea | Gentle Story for Kids | Fernwood Friends S1E03
The Glow in the Meadow | Animated Story for Kids | Fernwood Friends S1E01
```

Rules: exact search phrase inside the title; brand suffix always last; hook = story promise, not a keyword dump. (Older videos use `hook | Fernwood Friends S1E##` — fine, nothing to fix.)

### 5.2 Final description (assembled in `metadata.py`)

```text
Gentle bedtime stories for kids ages 4-8 — animated woodland adventures about
friendship and kindness, made for preschool viewers.          ← static keyword head (first ~150 chars = search gold)

<episode summary: what happens + series line + schedule line>  ← from the package (≤500 chars)

#FernwoodFriends #BedtimeStoriesForKids #AnimatedStoriesForKids #KidsStories
```

No links, no "subscribe/like/comment" words (§7). Cap: YouTube 5000 chars — we use <800.

### 5.3 Tags (auto-merge)

`priority core tags (6) → episode tags from package → remaining core tags`, deduped case-insensitively, capped at 30 tags / ~450 chars.

### 5.4 Shorts (auto)

- Title: `<short title> | Bedtime Story for Kids | Fernwood Friends`
- Description: short context + quote + **`Full story: <long title>`** (funnel to the long video) + keyword line + hashtag block with `#shorts`
- Tags: priority core + `shorts` + the long episode's tags

### 5.5 Every upload automatically

- `categoryId` Film & Animation, `selfDeclaredMadeForKids: true`, privacy public (private in tests)

---

## 6. Growth tactics beyond metadata

### 6.1 Playlists = the session engine (highest priority)

Made-for-kids videos have **no end screens/cards**, so playlists are the only "watch next" mechanism YouTube gives us.

- Create **`Season 1 — Full Stories`** and **`Season 1 — Shorts`**; set the long-playlist's first video to the newest episode occasionally; playlist order = release order.
- Add every new video to the right playlist (future: automate — `publish.py` already knows the season/episode).
- When 10+ longs exist: build **`Best of Fernwood — 1 Hour Stories`** compilations (pattern from Bandou/Koala Moon: 1h+ videos = session time + a browse-feature magnet). Requires a small pipeline feature — backlog item.

### 6.2 Shorts → longs funnel

Shorts already carry `Full story: <long title>`. Additional rules of thumb:
- Shorts titles keep the search phrase (done automatically) — Shorts are still indexed in search.
- A short's job = a self-contained 30-45s moment that makes the story world desirable; the long title does the converting.

### 6.3 Thumbnails (already API-set per episode)

- One character, one clear emotion, bright saturated background (brand palette), **≤3 words** of text (we currently ship **zero text** — matches top kids channels; don't add).
- `thumbnail_concept` is generated with the premise — keep the concept rule: face + action + readable at 160px.

### 6.4 The first hours matter

- 16:00 UTC = 12:00 ET / 09:00 PT — parents' lunch-scroll + kids home from school window in the US; Saturday/weekday mix covered. Keep it.
- After each post the Telegram stats message reports publish + next slot — check **CTR and views at ~24h** (§8).

### 6.5 What NOT to do

- No engagement bait aimed at children ("like, comment, subscribe" spoken to the kid viewer) — banned in content **and** against made-for-kids policy (§7). The **one approved exception**: the fixed parent-directed end-of-video CTA line (`universe.CTA_TEXT` — "Grown-ups, a gentle like and subscribe help our meadow glow brighter."), spoken by a character in the final scene and QC-enforced. Never reword it per-episode or address the child directly.
- No misleading keywords (e.g., "Cocomelon"-style brand hijacking) — grounds for removal.
- No re-uploading identical content (YouTube's inauthentic-content YPP policy); every episode is a unique story — keep it that way.
- Don't change the posting schedule — cadence signals matter more than hour-of-day tweaks.

---

## 7. Made-for-kids / COPPA guardrails (non-negotiable)

Applies to channel + every video (already enforced: `selfDeclaredMadeForKids: true` in `metadata.py`, content bans in `validate.py`).

| Consequence of made-for-kids | Effect on growth | Our counter |
|---|---|---|
| Comments disabled | No comment-section boost | Rely on watch time + playlists |
| End screens & cards disabled | No on-video "watch next" | Playlists + Shorts funnel (§6.1/6.2) |
| Personalized ads / limited monetization | Lower RPM later | Views/subs unaffected |
| No engagement solicitation toward kids | Can't say "subscribe!" | Keyword + brand-suffix growth instead |
| Videos may be limited to YouTube Kids | Extra distribution | Channel-level made-for-kids flag (§3) |

Banned words in content (enforced by QC): danger, scary, monster, kill, hate, stupid, buy, subscribe, comment, discount, weapon, gun, fight, mean, laugh at, shut up, die, freak, weirdo.

---

## 8. Measurement — monthly 15-minute review (YouTube Studio)

| Where | What | What good looks like | Action if bad |
|---|---|---|---|
| Analytics → Content → video | **CTR (impressions)** | ≥ 4-5% | Rewrite title/thumbnail of the worst performer (title first — keyword phrase missing?) |
| Analytics → Content → video | **Avg. view duration / % viewed** | Longs: 40%+; Shorts: 80%+ | Content-side: hook in first 10s; shorten shorts |
| Analytics → Reach → **Traffic source: YouTube search** | Share of search impressions | Growing month over month | Titles missing the exact search phrase (§4.1)? |
| Analytics → Reach → traffic: Suggested/Browse | | Growing | Playlist/watch-session health (§6.1) |
| Analytics → Audience | Subscribers gained per video | Steady slope > spikes | Consistency first; series brand second |
| Studio → Analytics → Research (or comments… unavailable) | **Search terms report** | Terms we already target | Add missing high-volume terms to `CORE_TAGS` (§9) |

**Decision rule:** two months of a pattern → change one thing at a time (usually titles, then tags bank), keep cadence constant so results are attributable.

---

## 9. How to change keywords later (for maintainers)

| Change | Where |
|---|---|
| Core tags / description head / hashtags / short title phrase | `app/youtube/metadata.py` (`CORE_TAGS`, `CORE_TAG_LEAD`, `DESCRIPTION_HEAD`, `HASHTAGS`, `SHORTS_TAGS`) + update expectations in `tests/test_youtube.py` |
| What the generator writes per episode (title formula, episode tags) | `app/content/prompts.py` (metadata line) |
| QC limits (title ≤70, desc ≤500, tags 8-15) | `app/content/validate.py` §metadata |
| Channel keywords / About text | YouTube Studio (§3) — not in code |
| Compilations feature (backlog) | new stage after `SHORTS_READY`; needs ~10 longs first |

*Doc owner: growth playbook. Last update: 2026-10-14.*
