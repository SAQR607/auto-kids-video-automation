# Stickman Revival & Dual-Channel Independence — Architecture and Migration Plan

**Version: 3 (revised 2026-11-18) · Status: APPROVED FOR IMPLEMENTATION (owner, 2026-11-18).**
Execution began 2026-11-18 — Phase 0 results are recorded under "Execution status" below,
and corrections discovered during execution are folded back into the relevant sections.

**Legend:** `[V]` = verified in this audit (file/CLI/official-doc evidence) · `[E]` = estimate ·
`[A]` = assumption · `[P]` = platform fact (GitHub/YouTube official documentation, fetched
2026-11-17).

## Execution status

### Phase 0 — executed 2026-11-18 (sole open item: dispatcher confirmation)

| Step | Result |
|---|---|
| WIP backup (§11.1) | Durable copy at `E:\projects\Bots\Auto _ Video.wip-backup-2026-11-17\` (temp copy retained until Phase 7) |
| WIP integration (§11.2) | Groups A–F committed as `ad6f2b2`; the exact pre-fix tree remains preserved in the backup |
| Step 0 — `hook_text` fixtures (§11.2) | `dd62e70`: valid distinct `hook_text` in all three package builders + new negative test (missing/overlong/duplicate still rejected) → **suite green (exit 0)** |
| Sync (C6) | `git pull --rebase` onto `e526112` (7 state-only commits, zero overlap with WIP) — clean; suite re-verified green |
| Full-history secret scan (§12.1) | gitleaks v8.30.1, 148 commits: **6 findings — all verified false positives** (`REPLACE_WITH_GROQ_KEY_*` placeholders in `.env.example`; synthetic `ya29.…`/`AIza…` vectors in `tests/test_redaction.py`) → **green; no rotation required** |
| Episode-ID scan (§4.1) | Stickman union (public + private registries **and** episode dirs) = {`s01e001`} only, `counters.season_1_next = 2` → **next ID = `s01e002`** `[V]`; the earlier `s01e017` expectation was corrected above (Fernwood conflation — the scan requirement caught it) |
| External dispatcher (§15) | **Confirmed by owner 2026-11-18: external cron service** holding an owner token; kept as primary, in-repo crons as backstops, not disabled. Action item before Phase 6: narrow its token to a fine-grained PAT (this repo only, Actions: read/write). **Phase 0 EXIT complete** |

### Phase 1 — executed 2026-11-20 (engine foundation)

| Step | Result |
|---|---|
| Vendored pinned subset (§1.1) | `1f91942`: MIT subset @ `00a7f9e` (25 files hash-verified) + `VENDOR.md` + repo `NOTICE`; upstream `*.md` docs (CC BY-NC) excluded |
| Engine runtime + driver | `25ef7e9`: `engine-js/` page (rig, damped springs, seeded phases; `READY`/`DUR`/`render(t)` contract) + `app/render/engine/` driver over the pinned `still.mjs`/`video.mjs` |
| Determinism gate (§9.1) | `tests/test_engine_determinism.py`: same mini-plan twice → identical SHA-256 frames, frames must also differ over time (blank-canvas guard) + video smoke; skips without the Node stack → Fernwood-only suites unaffected |
| Local verification | Full suite **361 passed**; sample still rendered and visually checked |
| CI | New `.github/workflows/engine.yml` (read-only token, actions pinned to SHAs, `npm ci`, lock-hash Chromium cache) → **green** (5m52s). Benchmark regression gate: first run red on `perf.render_ms_per_frame` 70.3 vs 60 — runner-CPU variance only (all scenes uniformly ~1.25× slower than the green 2026-11-18 run at 55.6; no render-path code changed), **green on rerun** |
| Pipeline files | **Untouched**: the only workflow change is the new test-only `engine.yml`; `production*.yml`, `manual.yml`, `benchmark.yml`, `health_check.yml` unchanged. **Phase 1 EXIT complete** |

### Phase 2 — executed 2026-11-24 (content & research)

| Step | Result |
|---|---|
| `topics/` pool | `be84620`: curated `topics/pool.json` (5 topics; every source hand-verified 2026-11-24 — HTTP 200 **and** extractable body text, JS shells rejected; Wikipedia = discovery only). Rotation record `state_stickman/topics_record.json` — deliberately under `state_stickman/` because workflows only `git add state_stickman`, so a repo-root record would be lost every run |
| Research stage (§7) | `app/content/research.py`: stdlib fetch (bounded timeout/bytes) → Groq claim extraction (closed classes `fact\|interpretation\|legend\|myth\|dramatization`, summarizing only from fetched text) → claim↔evidence gate: ≥2 excerpts from 2 independent sources (different publisher AND registrable domain), Wikipedia-derivative drop (shingle Jaccard ≥0.8 vs discovery article), syndication dedup (pairwise Jaccard ≥0.8), excerpts mechanical (best-overlap sentence, substring of received bytes, ≤250 chars) → `research.json` beside the package (never full text). Missing link / <2 usable sources → `ResearchError` → existing FAILED + Telegram + attempt budget; topic marked blocked and never re-issued; same episode re-claims its topic on retry |
| Wiring (Fernwood unchanged) | `engine.run_generation` hook gated by `research.enabled` — only `config/config.stickman.json` has it; Fernwood configs have no key → byte-for-byte same path. Research facts reach the script via `research_block` (`None` → identical prompt); additive claim-coverage check in `script_qc` (no `research.json` → no-op); `validate_config` requires `research.pool_path` to exist when enabled |
| Scene-directive seam (§2) | `app/content/directives.py`: `directive_messages` prompt + `validate_directives` schema (poses mirrored from engine-js `POSES`, `bible_version` lock, strictly increasing beats, x∈0..1, ≤2 actors, `scNN` ids) → `scene_plan()` emits the `buildScene` contract. Prompt + schema only per Phase 2 scope; pipeline wiring is Phase 4 |
| Tests | 32 new (`test_content_research.py` 21 + `test_content_directives.py` 11): block/retry budget via the §33 FAILED path, rotation + no-duplicates + exhaustion, independence pass/fail (same publisher, syndicated, Wikipedia-derivative), excerpt size + substring enforcement, claim coverage, profile gating → full suite **393 passed** (baseline 361 unchanged) |
| CI | `benchmark` **green first run** on `be84620` (no re-run needed); no workflow files changed — `production*.yml`, `manual.yml`, `benchmark.yml`, `health_check.yml`, `engine.yml` untouched |
| Pre-existing issue (not Phase 2) | Fernwood `production` hourly runs red since 2026-11-23: `s01e019` TERMINAL at `SCRIPTED` (script validation, 3/3 attempts exhausted) — fails on the state commit *before* this phase; remedy is the documented manual `attempts` reset, owner's call |
| | **Phase 2 EXIT complete** |

## Changelog v2 → v3 (owner final review)

| # | Owner requirement | Change in V3 |
|---|---|---|
| 1 | **Runtime publishing-day guard (mandatory)** | New §5.1: claim-time + publish-time double guard, 96 h missed-slot horizon, Friday hard block, deferral semantics; §9.1 test matrix covers 26 h delay, missed full day, Friday recovery, backlogged Shorts, cross-channel failure isolation, and a 2-week behavior property test (beyond config arrays) |
| 2 | **Permissions corrected to job level** | v2's "contents: write on the state-push step" was wrong — permissions exist only at workflow/job level. §6.2: read-all workflow default, dedicated `state-persist` job with job-level write (or a documented GitHub App), path-guard required check as proof; workflow-code protection argument included |
| 3 | **Quota arithmetic + provisioning** | §5.4: weekly total corrected 4,535 → **4,525 units** (avg ≈646/day); one-time `playlists.insert` (P×50) and backfill (N×50) added to provisioning; captions approved for all videos with a private-test-upload verification path (dry-run cannot call the API) and burned-in fallback |
| 4 | **Storage safeguards** | §10.2: strict 400 MB pilot-artifact cap with pre-upload enforcement, ≤1 pilot artifact retained, billing/budget review as a Phase 5 exit check |
| 5 | **WIP disposition** | §11: backup moved to a durable location outside the repo (performed); A–F retained; `hook_text` fixture fix as implementation step 0 with QC kept strict; Group C hunk-level selective review with regression proof; no discard without dependency check |
| 6 | **External dispatcher** | §15: investigation results (ruled out local machine + all owner repos), still unidentified, NOT disabled, GitHub-native fallback options, owner confirmation required |
| 7 | **GCP isolation** | Separate Stickman project approved (§1.3); Fernwood's project untouched; provision after Gate 2 / before Phase 6 (§13) |
| 8 | **Episode IDs** | §4.1: allocator rejects duplicates across **both** current and backup registries (hard error + permanent tests) |
| 9 | **Locked decisions** | §13 expanded with all items from owner §9 |
| 10 | **V3 deliverable** | Architecture §1 · calendar §5 · resource/cost §10 · dispatcher §15 · WIP §11 · migration sequence + gates §4 |

---

## 0. Contradiction ledger (resolved before proposals)

| # | Contradiction / issue | Evidence | Resolution |
|---|---|---|---|
| C1 | Both channels published Shorts on **Saturday** → violates no-shared-day rule | `[V]` both configs | New calendar §5.2 (owner-approved days) |
| C2 | Long days inverted: Fernwood Mon/Wed/Fri, Stickman Sun/Tue/Thu | `[V]` configs | Swap in §5.2 (config-only; `schedule.py` config-driven `[V]`) |
| C3 | "2 Shorts per long" vs "one Shorts day" — both true | `[V]` `shorts_per_long=2`; one weekly slot; hourly re-check drains rest | 2/long kept; 3 slots/week per channel (§5.2) |
| C4 | Stickman Pillow rendering broken at HEAD (`get_sprite` TypeError) `[V]` | dead path | Superseded by engine; removed in Phase 7 |
| C5 | WIP: 20 modified + 2 untracked; 14 tests failing | `[V]` | **Disposition approved (§11)**: A–F retained, fixture fix pending implementation |
| C6 | Local checkout behind origin; **audit conflation:** "16 episodes / s01e016 Shorts pending" describes **Fernwood's** `state/` registry (now s01e017), not stickman's — stickman union (public + private) = {`s01e001`} | `[V]` Phase 0 scan | `git pull` done in Phase 0; no stickman Shorts backlog exists — Fernwood's pending Shorts are its own runtime concern |
| C7 | `STICKMAN_YOUTUBE_*` / `STICKMAN_TELEGRAM_*` unset → stickman no-ops | `[V]` | Secrets after Gate 2, before Phase 6 (§13) |
| C8 | Playlists, end-screen plumbing, subtitles absent from codebase | `[V]` grep | New builds: §5.4 (playlists), §9.2 (SRT); explicitly new work |
| C9 | Shared `models-…` cache key across workflows | `[V]` | Kept (immutable, identical inputs `[P]`); new caches namespaced (§6.3) |
| C10 | Dual state-push race (same branch, both workflows) | `[V]` | Safe: disjoint paths + rebase + 3 retries; residual risk accepted (§6.1) |
| C11 | Duration: stickman 480 s vs owner 5–7 min openness | `[V]` configs | Pilot metrics decide (§9.3, §13) |
| C12 | Lemo pin drift | `[V]` clone clean at `00a7f9e` = origin/main HEAD | Pin `00a7f9e` (§2) |
| C13 | Stale workflow comments (old schedule wording) | `[V]` | Comment-only updates in Phase 6 |
| C14 | `s01e001` stuck at `RENDER_QC` since 2026-10-22 | `[V]` registry | Superseded (record preserved, publish permanently blocked, §4.1) |
| C15 | Fernwood published a Friday long; Friday must be buffer | `[V]` config | Removed by §5.2 **and blocked at runtime by §5.1** |
| C16 | **External hourly dispatcher:** 76/76 recent `workflow_dispatch` runs target `production.yml`, fired at **:00:01–:00:02 UTC**, actor SAQR607; stickman workflow = 10/10 `schedule`, zero dispatches | `[V]` Actions API | **Investigated, source unidentified (§15)**; not disabled; owner confirmation required; in-repo crons remain backstops |

---

## 1. Complete proposed architecture

### 1.1 One repo, two fully isolated production channels

```
SAQR607/auto-kids-video-automation (public, authoritative) — visibility must not change
├── shared Python package app/            — profile-dispatched, Fernwood behavior-preserving
│   ├── cli / pipeline / state / schedule / config     (APP_PROFILE switch)
│   │     schedule.py: due_slots() + publish-day guard (§5.1)  [NEW guard]
│   ├── content  (+ research stage, stickman-gated)     [NEW §7]
│   ├── audio    (Kokoro, mix, music/SFX, timing.json)  ← shared unchanged
│   ├── render
│   │   ├── scene.py / video.py / thumbnail.py          ← Fernwood Pillow path UNTOUCHED
│   │   └── engine/                    [NEW]            ← Narrative Stickman Engine (Python driver)
│   ├── qc       (script QC + video QC)                 ← shared, gates not weakened
│   ├── youtube  (upload, verify, metadata) (+ playlists.py [NEW], captions [NEW],
│   │            publish_long/publish_shorts gain the publish-day guard §5.1)
│   └── tiktok   (Fernwood only)
├── engine-js/                         [NEW]  ← engine runtime (our JS, MIT rig techniques)
├── vendor/lemo-opuscar/               [NEW]  ← pinned MIT subset @ 00a7f9e
├── topics/                            [NEW]  ← curated topic pool + used/pending record
├── universe_stickman/                 (exists) ← Character Bible [NEW file] + brief/manifest
├── state/ (Fernwood)      state_stickman/ (Stickman)     — disjoint, rebase-safe
├── config/config.json     config/config.stickman.json
├── .env                   .env.stickman
├── logs/app.log           logs/stickman/                 [V]
└── .github/workflows/
    ├── production.yml            group: production         cron 17 * * * *
    │     jobs: produce (READ-ONLY) → state-persist (write, §6.2) → state-path-guard
    ├── production-stickman.yml   group: production-stickman cron 41 * * * *  (same job split)
    └── manual / health_check / benchmark                   (Fernwood-oriented; untouched)
```

### 1.2 Isolation matrix (channel mechanics — all verified `[V]`)

| Dimension | Fernwood | Stickman |
|---|---|---|
| Workflow / cron | `production.yml` / `17 * * * *` | `production-stickman.yml` / `41 * * * *` |
| External hourly dispatch | yes (76/76 runs — §15) | **none** (schedule only) |
| Concurrency | `production`, no cancel | `production-stickman`, no cancel — **no shared lock** |
| Config / env | `config.json`, `.env` | `config.stickman.json`, `.env.stickman` |
| State | `state/` | `state_stickman/` |
| Logs | `logs/app.log` | `logs/stickman/` |
| Artifacts | `qc-reports`, build artifact | `qc-reports-stickman`, `stickman-build-*` |
| Secrets | `YOUTUBE_*`, `TELEGRAM_*` | `STICKMAN_YOUTUBE_*`, `STICKMAN_TELEGRAM_*` |
| GCP / quota project | **current project — untouched** | **separate new project** (approved §13) |
| Retry budget | per-episode attempts in `state/` | per-episode attempts in `state_stickman/` |
| Publishing days | **Sun / Tue / Thu** (runtime-guarded) | **Mon / Wed / Sat** (runtime-guarded) |

### 1.3 Shared external resources — cross-channel risk register

| Shared resource | Risk | Control (plan) |
|---|---|---|
| **Groq API key pool** (`GROQ_API_KEYS` shared `[V]`) | One channel's retry storm consumes rate limit, starving the other | Per-episode attempt budgets bound total calls (existing `[V]`); **new:** per-run hard call ceiling logged in run metrics — hitting it blocks + Telegram instead of retrying further; both ceilings sum < pool capacity `[E]`; optional key partitioning not needed at current volume |
| **GCP / YouTube quota project** | Shared project = shared `videos.insert` bucket (100/day) + 10,000-unit pool | **Resolved: separate GCP projects** (approved §13) — full quota-accounting isolation; Fernwood's project untouched; even if ever shared, disjoint days keep worst day ≈23 % of pool (§5.4) |
| **Repository caches (10 GB/repo)** | Cache pressure/eviction across channels | Shared `models-…` key immutable + content-identical `[P]`; new `stickman-browser-…` namespaced (§6.3); total ≪ 10 GB, monitored (§10.2) |
| **State-push concurrency** | Push races on shared branch | Disjoint paths + `pull --rebase` + 3 retries; worst case = that run red, its own state local, idempotent rerun — never the other channel's (§6.1) `[V]` |
| **Runner capacity / locks** | Cross-channel cancellation | Separate concurrency groups, `cancel-in-progress: false` `[V]` |
| **Telegram bot** | Shared alerting could mute one channel | Separate `STICKMAN_TELEGRAM_*` secrets `[V]` |
| **Workflow bypass token (§6.2)** | State-push credential abused to touch code | Path-guard required check + App without Workflows permission (§6.2 proof) |

---

## 2. Integration design: current project ↔ Lemo-Opuscar (unchanged from v1/v2)

- **Pin: `00a7f9e`** (= `origin/main` HEAD, tree clean `[V]`), recorded in
  `vendor/lemo-opuscar/VENDOR.md` with source, date, update procedure.
- **Vendored (MIT code only):** `core/lib.js`, `core/render/{browser,events,page,readcheck,serve,slot,still,video}.mjs`,
  `core/fonts/*` (OFL), rig/spring techniques adapted from `styles/stick-explainer/demo/{index.html,full.js}`
  (both MIT), attributed in repo `NOTICE` + verbatim upstream `LICENSE`/`REUSE.toml`.
- **Not vendored:** every `*.md` (CC BY-NC, incompatible with a public repo `[V]`);
  `.srt`/posters/stills (CC BY); `core/audio/**`, `core/tts/**`, `mux.sh` (we keep our own
  FFmpeg mix), demo media, `tools/`.
- **Runtime:** Node ≥ 20 `[P]` on the runner; exact locked dependencies (§12.4); Chromium cached
  under namespaced key; existing apt FFmpeg.
- **Seam:** Groq emits JSON scene directives → Python validates into scene-plan JSON →
  `video.mjs` (N worker browsers, `window.render(t)`, JPEG piped to ffmpeg `[V]`) → silent
  picture → **existing** audio mix/mux → existing QC → publish. Groq never writes JS/HTML.
  Shorts: same engine, vertical canvas.

---

## 3. Narrative Stickman Engine architecture

Components, scene-plan schema, determinism and parallelism as in v2 §3 (rig/face/costume/
actor/camera/stage JS + `plan.py`/`render.py`/`sheets.py`/`srt.py`/`page.html`; seeded RNG;
schema validation boundary; `bible_version` lock).

### 3.4 Render budget

- Job `timeout-minutes: 360` `[V]`; runner disk 14 GB `[V]`; JPEG frames piped, not stored `[V]`.
- 6 min × 24 fps = 8,640 frames `[E]`; 4 workers → allowed ≈ 2.08 s/frame after a 60-min
  reserve `[E]`. Expected well under 1 s/frame `[E]` — Gate 2 measures.

### 3.5 Exact rendering-throughput metric (owner requirement, unchanged)

> **`seconds_per_frame = T_render / N_frames`**, where
> **`N_frames = round(duration_sec × fps)`** and **`T_render`** = wall-clock time of the
> engine render invocation only — from node process start (first worker browser ready) to
> final segment concat completion; **excludes** checkout, dependency install, audio/TTS, QC,
> upload, and state push. Reported per run as: overall `seconds_per_frame`, per-worker mean,
> and max worker time. Budget = `(360 − 60) × 60 / N_frames` seconds/frame (2.08 s at
> 8,640 frames / 4 workers).

- **12 fps is an unapproved fallback.** Any fps/duration/quality reduction requires rendered
  visual A/B comparison submitted to the owner **and explicit approval** (§13).

---

## 4. Migration sequence and approval gates

| Phase | Work | Exit criteria (gate) |
|---|---|---|
| **0 — Prereqs** | Owner approves V3 → **separate implementation approval**; **step 0: `hook_text` fixture fix (§11)**; `git pull` (C6); full-history secret scan (§12.1); episode-ID scan (§4.1); **dispatcher confirmation from owner (§15)** | Clean sync, suite green, scan report reviewed, IDs enumerated, dispatcher source known |
| **1 — Engine foundation** | Vendor pinned subset + `NOTICE`; engine JS; driver; sample render locally + CI | Deterministic frame-hash test green; no pipeline files touched |
| **2 — Content & research** | `topics/` pool; research stage (stickman on / Fernwood off); scene-directive prompts + schema | Research block/retry tests green; Fernwood suite unchanged |
| **3 — Bible + Gate 1** | Character Bible; model-sheet set (§8) | **GATE 1: owner approves visual direction** |
| **4 — Pipeline integration** | Profile dispatch to engine (long + shorts); SRT; engine thumbnail; QC on engine output; §5.1 publish-day guard implemented + test matrix green; calendar config prepared, not activated | Sample + dry build green; Fernwood regression green; guard tests green; QC gates unchanged |
| **5 — Gate 2 pilot** | Full DRY_RUN on Actions (§9.2), artifacts uploaded (≤400 MB, §10.2), no YouTube upload; **owner reviews billing/budget page (§10.3)** | All QC PASS + metrics captured + owner reviews billing posture → **GATE 2: owner approves production** |
| **6 — Activation (explicit approval)** | Schedule config flip (§5.2); `STICKMAN_*` secrets; **separate GCP project provisioning**; **private test upload verifying `captions.insert`** (§5.4); playlist ensure-run; stale comments (C13) + description strings; §6.2 ruleset/App/path-guard applied; SHA pins (§12.3) | First auto episode verified `PUBLISHED` (existing verify-before-mark `[V]`); 2-week observation |
| **7 — Cleanup (post-validation)** | Remove legacy stickman Pillow path after grep/import reference check; retire private `stickman-stories` duplicate cron **and** the stale `release`-repo pipeline copy (§15) only after validation; docs/memory updates | `python -m app assets` green for Fernwood; suite green; both channels publishing on schedule |

### 4.1 Episode ID plan (owner-approved; reconciles C6 + C14)

1. **Supersede `s01e001` (stickman):** entry preserved in `state_stickman/registry.json`
   with an explicit `superseded: true` marker; a permanent guard refuses
   `publish_long`/`publish_shorts` for superseded entries (unit-tested) — it can never upload.
2. **No assumed next ID.** After Phase 0 sync, enumerate **all** episode IDs across public
   `state_stickman/` **and** the private backup repo's registry (read-only). The first
   genuinely unused `s01eNNN` (smallest positive integer absent from the union) becomes the
   next ID. **Phase 0 scan result (2026-11-18):** public and private `state_stickman/`
   registries and episode dirs each contain only `s01e001`, and `counters.season_1_next = 2`
   corroborates → **first unused stickman ID = `s01e002`** `[V]` (the earlier `s01e017`
   expectation was wrong — it counted Fernwood's registry; the scan requirement caught it).
   Re-scan immediately before Phase 6 activation (episodes may publish in between).
3. **Never reuse / never overwrite:** the allocator returns only IDs absent from the union
   set; **creating an episode whose ID exists in either registry is a hard error** — the
   allocator rejects duplicates across both current and backup registries.
4. **Permanent tests:** `test_episode_ids_unique_in_registry` (no duplicate keys in either
   registry) + `test_new_episode_id_skips_used_and_superseded` + `test_allocator_rejects_id_present_in_backup_registry`.

---

## 5. Publishing calendar, runtime guard, and quota

### 5.1 Runtime publishing-day guard — MANDATORY (owner requirement 1)

The 26-hour catch-up window alone could publish a missed Thursday Fernwood slot on Friday,
or a missed Saturday Stickman slot on Sunday (a Fernwood day). A **runtime guard** now
governs all public publishing. Design:

**Allowed days are derived from config** — `publish_days(cfg)` = the set of weekdays in
`config.schedule.long ∪ config.schedule.shorts` (single source of truth; `app/config.py`
already validates these against `VALID_DAYS` `[V]`). By configuration: Fernwood =
{Sun, Tue, Thu}, Stickman = {Mon, Wed, Sat}, Friday absent for both (§5.2).

**Layer 1 — claim-time guard** (`app/schedule.py: due_slots()`):
- A slot is claimable only when **`now.weekday() ∈ publish_days(cfg)`** — checked for both
  `long` and `shorts` kinds, on every path (scheduled runs, external dispatch, manual
  `--episode` runs, retries). Catch-up can never bypass it because every retry re-enters
  `plan_due()`.
- **Missed-slot horizon:** the 26 h window is replaced by `MISSED_SLOT_HORIZON_HOURS = 96`
  (4 days) — long enough for the largest permitted-day gap (Thu→Sun = 75 h) plus one missed
  full day, short enough that stale content lapses (same "forget" semantics as today's 26 h,
  just widened). Slots older than the horizon **lapse silently with a log line** — never
  published late.
- A missed slot therefore stays **pending** and is claimed at the **first run on the
  channel's next permitted day** (e.g., a missed Thursday 16:00 slot is claimed Sunday,
  earliest Sunday run). Backlog drains **oldest-first, one long claim per run**; a recovery
  day may carry two longs (recovered + regular), both on permitted days.

**Layer 2 — publish-time guard** (`app/youtube/publish.py: publish_long()` line 149 /
`publish_shorts()` line 311):
- Immediately before any YouTube write (`videos.insert`, `captions.insert`,
  `thumbnails.set`, `playlistItems.insert`), assert `now.weekday() ∈ publish_days`; on
  violation raise `PublishDayError`.
- The runner treats `PublishDayError` as a **clean deferral**: exit 0, no state mutation,
  clear log line, upload resumes on the next permitted day. This is defense-in-depth for
  manual `--episode` runs — the `episode` input's "regardless of schedule" wording is
  amended (Phase 6) to mean *build/resume regardless of schedule, **publish only on
  permitted days***.
- **Preparation is never blocked:** research, script, TTS, render, QC, thumbnails, SRT all
  run any day; only the public upload is day-gated.

**Explicit non-goals:** `next_posting()` reporting already derives from config days (no
change); superseded IDs (§4.1) remain unpublishable regardless of day.

**Test matrix (§9.1) — required cases:**

| # | Case | Assertion (mocked YouTube, fake clock) |
|---|---|---|
| G1 | **26-hour delayed execution** | Fernwood slot Thu 16:00, run executes Fri 18:01 (age 26 h) → `plan_due()` returns nothing; stays pending; Sunday run claims it (age ≤ 96 h) and publishes **on Sunday** |
| G2 | **Missed full publishing day** | Fernwood fails all Sunday → Tuesday's first run claims Sunday's slot; Stickman claim/publish unaffected (separate config/registry) |
| G3 | **Friday recovery** | For every Friday timestamp (00:00–23:59, any backlog age): both channels claim nothing; direct `publish_long`/`publish_shorts` call raises `PublishDayError` → deferred, zero API calls, state unchanged |
| G4 | **Backlogged Shorts** | 3 episodes with pending shorts → one episode's pair per run, only on permitted days, never Friday; per-Short checkpoints preserved (Short 1 status saved before Short 2 attempts) |
| G5 | **One channel failing, other continues** | Fernwood claim/publish raises → Stickman run completes its claim + (mocked) publish in the same simulated window; guard is per-profile, registries disjoint |
| G6 | **Behavior property test** (replaces config-array-only test) | Simulated 168 h of hourly `now` values per channel: **every claimed slot and every mocked publish falls on that channel's permitted weekday; zero Friday publishes for either channel** — plus the existing config-level disjointness assertions |

### 5.2 Final publishing calendar (owner-approved)

| | Fernwood Friends | Stickman Stories |
|---|---|---|
| Longs | **Sun, Tue, Thu — 16:00 UTC** | **Mon, Wed, Sat — 16:00 UTC** |
| Shorts (2 per long) | **Sun, Tue, Thu — 19:00 UTC** | **Mon, Wed, Sat — 19:00 UTC** |
| Friday | **buffer — no publishing, both channels (runtime-enforced, §5.1)** | same |

Day sets are disjoint for all content. 16:00 UTC kept — no technical reason found to move
`[V]`. Changeover is config-only; completed slot keys stay in registries (history intact);
stickman has **no pending Shorts** (its only episode, `s01e001`, never reached shorts and is
superseded); Fernwood's own pending Shorts drain on Fernwood's schedule as today `[V]`.

### 5.3 Exact publish times — long, Short 1, Short 2 (owner requirement, unchanged)

Triggering reality `[V]`: external `workflow_dispatch` fires at :00:01–:00:02 UTC for
Fernwood (§15); Stickman relies on its `41 * * * *` cron (GitHub delays observed `[V]`);
in-repo crons are backstops. `plan_due()` is idempotent, so **first trigger at/after the
slot claims it** — now also subject to §5.1.

| Item | Slot | Typical actual publish (UTC) | Hard bound |
|---|---|---|---|
| Long episode | 16:00 on channel day | claimed 16:00–16:41; build+QC+upload → **live ≈16:10–17:10** `[E]` (observed builds 10–21 min `[V]`) | next permitted run within 96 h (§5.1) |
| **Short 1** | 19:00 on channel day | claimed at first permitted trigger ≥19:00 → **live ≈19:03–19:50** `[E]` | same run; else next hourly trigger on a permitted day |
| **Short 2** | 19:00 on channel day | **Short 1 + ~30–90 s, same run, separate per-Short status checkpoint** → **live ≈19:04–19:52** `[E]` | if the run dies between them, next hourly trigger finishes it (per-short checkpoints `[V]`) |

Both Shorts of a long always publish on the same channel-owned day. Backlog rule unchanged:
one episode's pair per hourly trigger, draining hour by hour (observed 2026-11-14: three
episodes drained 16:00/17:00/17:06 `[V]`).

### 5.4 YouTube API quota — final corrected estimate (owner requirement 3)

Official quota-cost table, fetched from Google's docs 2026-11-17 `[P]`:
`videos.insert` own bucket **100 calls/day @ 1 unit**; `captions.insert` **400**;
`thumbnails.set` **50**; `playlistItems.insert` **50**; `playlists.insert` **50**;
verify/list reads **1**; everything else from the shared **10,000 units/day** pool
(reset midnight PT); `search.list` own bucket — never called by us.

**Per channel, per week** (9 videos = 3 longs + 6 shorts; captions on **all** videos —
approved; arithmetic corrected):

| Operation | Calls/week | Units/week |
|---|---|---|
| `videos.insert` (own bucket) | 9 | 9 of the 100/day bucket |
| `captions.insert` | 9 | 3,600 |
| `thumbnails.set` | 9 | 450 |
| `playlistItems.insert` (auto-playlist) | 9 | 450 |
| `videos.list` verify (≈2/video) | 18 | 18 |
| playlist ensure/list (idempotent) | 7 | 7 |
| **10k-pool subtotal** | | **4,525/week ≈ 646/day average** `[E]` |

**Worst publishing day** (1 long + 2 Shorts, all features, +50 % retry headroom):
captions 1,200 + thumbnails 150 + playlistItems 150 + reads ~10 = 1,510 × 1.5 ≈
**2,265 units ≈ 23 % of 10,000** `[E]`; `videos.insert` ≤ 6 of the 100/day bucket `[E]`.
Captions disabled (fallback path) would drop the worst day to ≈465 units (≈4.7 %).

**One-time initial provisioning (per channel):**

| Item | Units |
|---|---|
| `playlists.insert` — create channel playlists (P ≤ 10, budgeted at 10) | ≤ 500 |
| Optional backfill `playlistItems.insert` for the existing catalog (N ≤ 100 videos) | ≤ 5,000 |
| **Captions verification** (private/unlisted test upload: 1 `videos.insert` + 1 `captions.insert` + 1 `thumbnails.set`) | 1 (own bucket) + 450 |
| **Worst combined day** (backfill + normal ops + retries) | ≤ ~7,750 → still < 10,000 `[E]` |

**Captions verification path (owner condition):** Gate 2 is a DRY_RUN that never uploads, so
it cannot exercise `captions.insert`. Verification therefore happens in Phase 6 provisioning
via a **private test video** before the first public episode; if the API call fails, the
pipeline keeps **burned-in subtitles** (already produced from SRT `[V]`) as the guaranteed
fallback, and captions are disabled in config (quota halves — table above).

- **Days in §5.2 stay as approved — they are a channel requirement, not a quota constraint.**
- Retries bounded by per-episode attempt budgets `[V]`; separate GCP projects (§13) make
  these per-channel figures literally independent.

### 5.5 Example first week after activation (illustrative `[E]`)

```
Sun 16:00 Fernwood long · 19:00 Fernwood shorts (Short 1, then Short 2 ~1 min later)
Mon 16:00 Stickman long · 19:00 Stickman shorts
Tue 16:00 Fernwood long · 19:00 Fernwood shorts
Wed 16:00 Stickman long · 19:00 Stickman shorts
Thu 16:00 Fernwood long · 19:00 Fernwood shorts
Fri — buffer, nothing scheduled, runtime guard refuses any publish —
Sat 16:00 Stickman long · 19:00 Stickman shorts
```

---

## 6. GitHub Actions isolation, permissions, and concurrency

### 6.1 Verified already-compliant (unchanged)

Separate workflows/staggered crons; separate concurrency groups, `cancel-in-progress: false`
(no shared lock, mid-flight builds never killed); namespaced secrets with production gate;
disjoint state dirs with per-profile `git add`; distinct artifact names; separate logs;
independent attempt budgets — all `[V]`. State-push: stage profile dir only → commit →
`git pull --rebase` + push ×3 `[V]`; disjoint paths → rebase cannot conflict across
channels; residual risk (all 3 retries fail → that run red, idempotent rerun, no duplicate
uploads) accepted.

### 6.2 Job-level permissions design (owner requirement 2 — corrected)

**Correction:** GitHub `GITHUB_TOKEN` permissions can be set only at **workflow or job
level**, never per step (v2's wording was wrong). Today `production.yml` grants
`permissions: contents: write` workflow-wide `[V]`; the new design splits jobs:

```yaml
permissions:            # workflow default: READ-ONLY for every job
  contents: read

jobs:
  produce:              # research → script → TTS → render → QC → upload
    # no permissions override → inherits contents: read  (cannot push, ever)
    # ... uploads state-bundle-<run_id> artifact (retention-days: 1, KBs)
  state-persist:
    needs: produce
    if: always()        # partial progress must still persist (matches today's behavior)
    permissions:        # JOB-level: the only job in the repo that can write
      contents: write
    # checkout fetch-depth: 0 → download state-bundle → copy over state/ or
    # state_stickman/ → commit (stages ONLY the profile state dirs) → rebase+push ×3
    # also owns the TikTok secret-rotation step (it mutates repo secrets via its own PAT)
  state-path-guard:
    # required status check: fails + alerts if any commit pushed by the state-persist
    # actor touches paths outside state/ or state_stickman/
```

Production, research, rendering, and QC remain in the read-only `produce` job (YouTube
publishing uses OAuth refresh tokens in env — completely independent of `GITHUB_TOKEN`).
State moves between jobs via a KB-size artifact with `retention-days: 1` (no storage
concern, §10.2). The same split applies to `production-stickman.yml`.

**Branch protection (ruleset on the default branch):** require pull request + required
status checks [`health-check`, `state-path-guard`]; block force-push and deletion.
Bypass actor, in order of preference:

1. **Dedicated GitHub App `state-pusher`** (recommended — owner invited this option):
   - **Exact permissions:** Contents **Read & Write**; Metadata Read (implicit);
     **Workflows: NOT granted**; no Administration, Secrets, Actions, or Members.
   - **Bypass scope:** listed as the single bypass actor in this repository's ruleset;
     App installation is scoped to `auto-kids-video-automation` only.
   - **Token lifecycle:** short-lived installation token minted **only inside
     `state-persist`** via SHA-pinned `actions/create-github-app-token`; never available to
     `produce`; expires in ~1 h.
2. **Fallback:** `GITHUB_TOKEN` job-level `contents: write` + github-actions[bot] as bypass
   actor **if** it is selectable in rulesets (to be verified at implementation). If it is
   not selectable, the App is required — this dependency is stated honestly rather than
   assumed.

**Proof that code/workflow protection is not weakened:**
1. **Workflow files:** changed only via PR with required checks; the persist credential
   lacks the Workflows permission, so GitHub **platform-rejects** any push that touches
   `.github/workflows/*` from the bypass actor — the token physically cannot rewrite its own
   protection.
2. **Application code:** the persist job stages only hard-coded `git add state
   state_stickman` (never `git add -A`); that job's script is itself workflow code under PR
   protection; the bypass token exists nowhere else (job-scoped secret, auto-expiring).
3. **Detection:** `state-path-guard` runs on every push and fails + alerts (Telegram) if the
   bypass actor's commit range contains any non-state path — immediate visibility, zero
   silent writes.
4. **All other jobs** hold `contents: read` only; `GITHUB_TOKEN` is job-scoped and expires
   at job end. Widening any of this requires passing the very PR checks being protected.

### 6.3 Planned workflow changes (Phase 6, approved in bulk with this plan)

| Change | Why |
|---|---|
| Job split + permissions per §6.2 (both production workflows) | Owner requirement 2 |
| Chromium cache step in `production-stickman.yml` only, key `stickman-browser-${{hashFiles('package-lock.json')}}` | Namespaced cache (§1.3) |
| **Artifact retention matrix:** `qc-reports*` → 30 d; `stickman-build-*` / pilot media → **7 d**; `state-bundle-*` → 1 d; `pilot-metrics` → 30 d | §10.2 |
| Pin **all** `uses:` actions to full commit SHAs | §12.3 |
| Update stale schedule comments (C13), the `episode` input wording (§5.1), channel `description_short`/`schedule_line` strings still advertising old days (§11 Group D) | Accuracy |
| Keep shared `models-…` cache (comment documenting why) | Immutable identical entries `[P]` |
| **No change** to cron minutes, concurrency groups, Fernwood steps, state-push retry logic, QC gates | Preservation requirements |

---

## 7. Research and fact-checking (owner-approved, unchanged from v2 §7)

Stage design, `topics/` pool, rotation rules, block+Telegram+bounded-retry policy stand as
approved. Evidence rules (all retained):

- **Minimal excerpts:** `research.json` stores per claim: claim text, class, and per source
  URL/title/publisher/access-date + a **≤ ~250-char excerpt of only the supporting
  sentence(s)**. Never full pages, HTML, articles, or raw scrapes — full text exists only
  ephemerally in run memory.
- **Genuine independence:** different publishing organization (not subdomains/mirrors/
  editions); Wikipedia-derivative check (normalized shingle similarity against the discovery
  article); syndication/duplicate detection across candidates (pairwise Jaccard ≈0.8
  threshold, local + free); preferred tiers: primary texts, museum/university/library/
  scholarly, `.edu`/`.gov`; Wikipedia = discovery only, never sufficient alone.
- **Claim↔evidence linkage:** every significant factual claim needs ≥2 excerpts from 2
  genuinely independent sources; missing/weak links → episode **blocked**
  (`FAILED` via bounded-retry budget + Telegram; topic marked blocked). Groq summarizes only
  from fetched text; excerpts extracted mechanically from received bytes → citations cannot
  be fabricated. Script QC gains an additive claim-coverage check; existing gates untouched.
- Classification `fact | interpretation | legend | myth | dramatization` retained.
- **All services free** — stdlib HTTP + local computation + existing Groq keys, ever.

Tests (offline/mocked): independence pass/fail (same-publisher, syndicated,
Wikipedia-derivative), excerpt-size enforcement, missing-link blocking, retry budget,
schema, rotation, no-duplicates.

---

## 8. Character Bible and visual approval (Gate 1 — unchanged)

Three-tier cast with stable IDs/proportions/colors/expressions/accessories/clips;
`bible_version` hash required in every scene plan, locked by owner approval;
`python -m app sheets` produces narrator + recurring model sheets (front/side/¾, expression
grid, pose grid, walk/run, talk/react), interaction sheets, 4+ environments, 4–6 cinematic
scene samples with camera/animation examples, thumbnail + end-card samples. Rejected
iterations archived outside loader paths, never reused (§13). **No production standard
before owner approval.**

---

## 9. Test and pilot production plan

### 9.1 Test layers

| Layer | Scope |
|---|---|
| Existing suite | baseline restored after the §11 fixture fix; **must stay green every phase** |
| **Publish-day guard** | matrix **G1–G6** (§5.1) — includes the 2-week behavior property test that replaces config-array-only coverage |
| New unit tests | research block/independence/syndication, topic pool rules, scene-plan schema, SRT, playlist idempotency (mocked), config-level calendar disjointness (retained), **episode-ID uniqueness + allocator rejection across both registries + superseded-publish-block** (§4.1) |
| Determinism | same mini-plan twice → identical frame hashes (sample, CI) |
| Engine smoke | real-runner `sample` render via `manual.yml` |
| Fernwood regression | `benchmark.yml` untouched, green on every `app/**` push |
| Cross-channel isolation | G5 (§5.1) + shared-resource controls (§1.3) |

### 9.2 Gate 2 — full DRY_RUN pilot

`workflow_dispatch production-stickman mode=dry-run` (works without YouTube secrets `[V]`);
state stops at `RENDER_QC` `[V]` → **no upload possible**. Exercises: research → script →
script QC → narration (`am_fenrir`) → music/SFX → engine animation (long **and** one short)
→ SRT subtitles → thumbnail → final video → all QC reports. Pronunciation clips of
historical names attached for owner listening.

**Artifacts:** `stickman-build-<run_id>` (video, thumb, SRT, script, scene plan,
research.json) — **7 days, ≤ 400 MB enforced before upload (§10.2)**;
`qc-reports-stickman` — 30 days; `pilot-metrics.json` — 30 days. Owner reviews → approve
(→ Phase 6) or reject (→ bounded revision, re-pilot; the previous pilot artifact is deleted
when the new attempt uploads, so **at most one pilot artifact exists at a time**).
Thereafter ordinary episodes publish automatically with no per-episode approval (§13).

### 9.3 Pilot metrics

Per-stage wall time; `seconds_per_frame` per §3.5 (+ per-worker mean/max); peak RSS; disk
high-water; cache hit/miss; **API call counts** (Groq calls/tokens, YouTube calls by method
vs §5.4 quotas, HTTP fetches); total runner minutes. Written to `pilot-metrics.json` + job
summary → drives duration recommendation and go/no-go.

---

## 10. Final resource and zero-additional-cost assessment (owner requirement 4)

### 10.1 Compute (verified)

| Fact | Value |
|---|---|
| Standard GitHub-hosted runners in **public** repos | **Free** — explicitly excluded from included-compute draw `[P]` (billing docs fetched 2026-11-17) |
| Recent run volume | 257 runs / ≈11 days: idle 2–4 min, builds 10–21 min, worst failure 60 min `[V]` |
| Estimate (both channels, steady state) | ≈4,000–7,000 runner min/month `[E]` → **$0** while public |
| Private `stickman-stories` duplicate cron + stale `release`-repo pipeline (§15) | retired in Phase 7 (owner-approved cleanup) |

### 10.2 Storage — runner compute ≠ artifacts ≠ caches

| Storage class | Applicable allowance | Our usage | Posture |
|---|---|---|---|
| **Artifacts** (shared with Packages) | Free plan **500 MB included**; overage $0.25/GB/month `[P]`; no public-repo exemption stated in billing docs `[P]` → treated as binding; account's actual billing page checked at Phase 5 (§10.3) | QC JSON ≈ KBs; state bundles ≈ KBs (1-day retention); pilot media ≈ 100–300 MB `[E]` | **Strict pilot cap: ≤ 400 MB per pilot artifact**, enforced by a pre-upload size check that **fails + alerts** if exceeded (never silently uploads over cap); **≤ 1 pilot artifact retained** (re-pilot deletes the prior attempt's); media retention **7 d**, QC/metrics **30 d**, state bundles **1 d**; production runs never artifact videos; **rendered videos never stored permanently in artifacts or git** `[V]` |
| **Caches** | **10 GB per repository** included; charges only if the limit is raised; overage $0.07/GB/month `[P]` | `models-…` ≈1–2 GB + `stickman-browser-…` ≈0.5 GB ≈ **< 3 GB** `[E]` | Keep well under 10 GB; reviewed at every phase gate + quarterly; **never raise the limit**; trim/evict rather than expand |
| **Runner compute** | Free for public repos `[P]` | §10.1 | standard runners only |

### 10.3 Charge-prevention guards (zero additional cost is non-negotiable)

1. **No limit increases** anywhere; never enable larger/paid runners (billed even for
   public repos `[P]`).
2. **No paid services** — no paid APIs, tiers, or add-ons in any phase (§13).
3. **Retention everywhere:** explicit `retention-days` on every artifact (§6.3); the
   90-day default is never relied on `[P]`.
4. **Billing review before activation (Phase 5 exit):** owner opens Settings → Billing and
   confirms (a) whether a payment method is on file (with none, compute overage is *blocked*
   not charged `[P]`; storage overage *can* charge if a card exists `[P]]), (b) free budget
   alerts enabled (90 %/100 % usage emails `[P]` — recommended, zero cost).
5. **Visibility lock:** repository **remains public**; no visibility change (§13). Private
   would cost ≈$32–48/month compute `[E]` + storage → re-planning required first.
6. **Cache monitoring:** phase gates + quarterly; response to pressure = delete/trim keys,
   never increase the limit.

---

## 11. WIP preservation and disposition (owner requirement 5 — APPROVED, fix pending)

### 11.1 Backup — preserved and moved to a durable location (performed this session)

| Location | Contents |
|---|---|
| **`E:\projects\Bots\Auto _ Video.wip-backup-2026-11-17\`** ← durable, outside the repo (created 2026-11-18 per owner instruction) | `tracked.patch` (binary-safe diff of all 20 modified files), `files/` (byte copies of all 20 modified + 2 untracked files, original paths), `git-status.txt`, `HEAD.txt` = `a064004e` — 34 entries, verified |
| `C:\Users\SAQR7\AppData\Local\Temp\opencode\wip-backup-2026-11-17\` | original copy, retained until implementation completes (no deletion) |

No git state was ever touched: no stash, no commit, no reset, no clean — only read + copy.
The working tree is exactly as the owner left it.

### 11.2 Disposition (owner decision, recorded)

- **Groups A–F: RETAINED** (analysis table unchanged from v2 §11.2: A content
  restructure incl. `hook_text`; B QC; C render/thumbnail; D config; E docs/memory; F test
  expectation updates). Nothing judged unnecessary.
- **`hook_text` fixture fix — implementation step 0** (not done now, pending
  implementation approval): add valid `hook_text` (1–6 words, distinct between the two
  shorts) to the short fixtures in `tests/qc_fixtures.py`. **QC is not weakened:** the rule
  in `validate.py:493–496, 531` stays exactly as written, and negative tests keep asserting
  that missing, over-long, and identical hooks are rejected. Expected outcome: the 14
  failures (5 `test_content_validate` + 2 `test_profile_stickman` + 7 `test_qc_script`) go
  green with zero production-code change.
- **Group C — selective review at implementation:** retain the general improvements
  (transitions/dissolves, thumbnail close-up, watch-next end card, any Fernwood-affecting
  hunks) **only where regression tests prove them safe** (`test_render_parallel`,
  `benchmark.yml`, new `test_thumbnail`/`test_transitions`); **do not carry obsolete
  Pillow-specific Stickman rendering logic into the new engine** — those hunks are hunk-level
  classified, kept only while the legacy path lives (Phase 7), and never ported to
  `engine/`.
- **No WIP file is discarded without a dependency check** (grep imports/callers first).
  Any discard requires an explicit owner instruction, executed manually — never by us
  implicitly.

### 11.3 Recovery procedure (any time)

Copy `files/*` back over the working tree, or `git apply tracked.patch` from the durable
backup — both non-destructive; no history changes.

---

## 12. Technical safeguards (owner requirement, retained + expanded)

1. **Full-history secret scan (Phase 0 gate):** free open-source scanner (e.g. gitleaks)
   over the complete git history of the public repo **before** relying on it as production
   source. Findings → rotate those credentials immediately and document; history rewrite
   only on separate owner instruction. Scan-green report is a Phase 0 exit criterion.
2. **Branch protection + permissions:** per §6.2 — ruleset with PR requirement, required
   checks, job-level permissions, documented App (or verified bot) bypass, path-guard.
3. **Pin third-party Actions to immutable SHAs:** every `uses:` replaced with full commit
   SHA + trailing version comment; floating tags forbidden.
4. **Exact Node/Playwright lock:** exact versions (no `^`), committed `package-lock.json`,
   `npm ci`, Chromium pinned via the playwright version, cached under the lock-hash key →
   reproducible installs.
5. **12 fps = unapproved fallback:** any fps/duration/quality reduction requires visual A/B
   output compared side-by-side and explicit owner approval (§3.5, §13).
6. **Throughput metric defined exactly** in §3.5 — used for the 2.08 s/frame budget and
   Gate 2 reporting.

---

## 13. Locked decisions (owner §8 + §9 — not reopened)

| Decision | Status |
|---|---|
| Weekday separation: Fernwood Sun/Tue/Thu, Stickman Mon/Wed/Sat, Friday buffer | **Approved** (+ runtime-enforced §5.1) |
| **Runtime publishing-day guard: catch-up/retries never bypass it; missed slots wait for the next permitted day; Friday hard block** | **Approved (mandatory)** |
| Option 1: vendor pinned Lemo subset → dedicated Narrative Stickman Engine | **Approved** |
| Supersede `s01e001` (record preserved, permanently unpublishable); next ID by full registry scan; duplicates rejected across both registries | **Approved** (§4.1) |
| Separate GCP project for Stickman; Fernwood's project/YouTube integration untouched; independent quota, OAuth, state, failure handling | **Approved** |
| Provision `STICKMAN_YOUTUBE_*` / `STICKMAN_TELEGRAM_*` after Gate 2, before Phase 6 | **Approved** |
| Final episode duration = pilot-metrics decision | **Approved** (pending metrics) |
| Gate 1 (visual) and Gate 2 (DRY_RUN pilot) owner approvals mandatory | **Approved** |
| Fernwood's current production pipeline untouched | **Approved** |
| Research-first content production | **Approved** |
| Character Bible + reusable recurring characters | **Approved** |
| Three long episodes per week per channel | **Approved** |
| Two Shorts per long episode; Short 1 → Short 2 sequential in the same slot with per-Short checkpoints | **Approved** |
| `am_fenrir` as Stickman narrator; Kokoro for all speech | **Approved** |
| English-only content | **Approved** |
| **English caption tracks on all longs and Shorts** (verified via private test upload; burned-in fallback if API fails) | **Approved** |
| Automatic publishing after successful QC and one-time pilot approval (no per-episode approval) | **Approved** |
| No reuse of rejected legacy Stickman visuals | **Approved** |
| Repo stays public; standard runners only; no paid services; zero additional cost non-negotiable; Lemo commit pinned; QC gates never weakened | **Standing** |
| Artifact rules: 7 d media / 30 d QC+metrics / 1 d state; ≤ 400 MB pilot cap; ≤ 1 pilot artifact; no permanent video storage in artifacts or git; caches < 10 GB; no limit increases | **Approved** |

---

## 14. Remaining owner decisions

| # | Decision needed | Our recommendation |
|---|---|---|
| 1 | **Review and approve V3** → then give the separate explicit **implementation approval** | Approve as written |
| 2 | **Dispatcher (§15): RESOLVED 2026-11-18 — external cron service (owner-confirmed)**; remaining action before Phase 6: narrow its token to a fine-grained PAT (this repo only, Actions: read/write) | Dispatcher stays primary; in-repo crons remain backstops |
| 3 | **State-push credential:** create the `state-pusher` GitHub App (recommended, §6.2) vs. verify github-actions[bot] bypass | GitHub App — platform-enforceable Workflows-permission denial |
| 4 | **Pilot artifact cap value** (400 MB) and ≤ 1 retained pilot artifact | Accept as proposed |
| 5 | **Billing/budget review** performed by you at Phase 5 exit (§10.3) | Confirm timing |
| 6 | Episode **duration** after Gate 2 metrics | Decide from data (starting hypothesis 360 s, window 300–420 s `[E]`) |
| 7 | Gate 1 model sheets, Gate 2 pilot artifacts (future, mandatory) | — |

---

## 15. External dispatcher — investigation findings (owner requirement 6)

**Status: not disabled. In-repo hourly crons remain backstops. Owner confirmation required.**

**What is verified `[V]`:**
- 76 of 86 recent `production` workflow runs are `workflow_dispatch`, **all targeting
  `production.yml` only**, created at **:00:01 (28×) or :00:02 (48×) UTC** — second-level
  precision over ~3 weeks.
- Triggering actor is always **SAQR607** (your account), i.e. the calls carry a token
  belonging to you (direct REST `workflow_dispatch`, not `repository_dispatch`).
- **`production-stickman.yml` is never dispatched** (10/10 runs are `schedule`) — the
  external trigger only accelerates Fernwood.
- In-repo workflows contain **no** dispatch calls (grep of all 5 workflow files).

**What has been ruled out on this machine `[V]`:**
- Windows Task Scheduler: no matching task (only Microsoft/Google/Rainmeter entries; the
  Startup folder holds only `Rainmeter.lnk`).
- WSL crontab: empty. No local script or loop is firing the trigger.

**What has been ruled out in your GitHub account `[V]`:**
- All ~45 accessible repos were enumerated for workflows: only `auto-kids-video-automation`,
  `stickman-stories` (private copy), and **`release`** (a **stale full copy of the old
  pipeline** with its own `5 16 * * 1-6` cron — it runs its own build; it does **not**
  dispatch) have relevant workflows; none reference `auto-kids` or call `gh workflow run`.
- Remaining workflows (`static.yml`, `rdp.yml`, `deploy.yml`, `render-video.yml`,
  `paper-session.yml`) contain no dispatch to this repo.

**Conclusion:** the trigger comes from **outside this machine and outside your visible GitHub
repos** — most consistent with a hosted external scheduler (cron service, NAS, second
device/account) using a token of yours. Its authentication cannot be inspected from here.

**Owner answer (2026-11-18): external cron service.** The Phase 0 exit gate is met.
Remaining action item before Phase 6: narrow the service's token — a fine-grained PAT
limited to this repository with **Actions: read/write only** (a classic PAT with
`repo`+`workflow` would be over-privileged), or a scoped App. The service keeps triggering
`production.yml` only; rendering, research, audio, and video production remain 100 % on
GitHub-hosted runners (a trigger is not compute — the runner-only requirement holds).

**GitHub-native fallback (if it proves PC-dependent):** production already runs 100 % on
GitHub-hosted runners — only the *trigger* would be PC-dependent. Options, in order:
(a) rely on the in-repo `17`/`41` hourly crons as primary (delay bounded by GitHub's
scheduler; the §5.1 guard makes any delay safe — worst case the post lands on the next
permitted run); (b) add a second in-repo schedule at `0 * * * *` as an independent trigger
(same GitHub scheduler, partial independence); (c) a free external cron service with a
narrowly-scoped token — still only *triggers*; all compute stays on runners (does not
violate the runner-only requirement).

**Related cleanup finding:** the `release` repo contains a stale pipeline copy with live
YouTube secrets and its own cron — listed for retirement in Phase 7 (owner-approved), after
validation.

---

*Prepared for owner review (V3). Verified facts are tagged; estimates and assumptions are
tagged. No application code, configuration, workflow, asset, repository setting, or secret
was modified; no git state was altered; the only created/updated repository file is this
document. The WIP backup was copied (not moved destructively) to a durable location outside
the repository per owner instruction.*
