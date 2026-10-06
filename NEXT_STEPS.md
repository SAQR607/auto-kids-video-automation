# NEXT_STEPS.md — Where The Project Stands And What To Do Next

Prepared at release: `Release production-ready automation system`.
Repository: `https://github.com/SAQR607/auto-kids-video-automation` (public).

---

## CURRENT STATUS

- All phases implemented; the system is feature-complete and packaged for
  release. Nothing in the codebase is awaiting development.
- 169/169 unit tests pass; `python -m app doctor` (offline) PASS with only the
  two expected WARNs (missing optional secrets in local `.env`).
- Repository uploaded to GitHub with workflows `production`, `manual`,
  `health-check` present; secrets are NOT configured yet (user's step).
- The `production` workflow ships **disabled** — nothing runs on a schedule
  until you enable it (see PRODUCTION ACTIVATION below).

---

## COMPLETED

- **Implementation:** content engine (Groq), Kokoro TTS audio, 2D render +
  FFmpeg, dual QC gates (`SCRIPT_QC`, `RENDER_QC`), YouTube publishing
  (resumable upload, processing verification, thumbnails, Made-for-Kids),
  Shorts pipeline, Telegram SUCCESS/RED ALERT reporting, idempotent + resumable
  state machine (`state/`), bounded retries.
- **Automation:** GitHub Actions — `production` (schedule + 3 input modes),
  `manual` (7 read-only/test commands), `health-check` (daily tests + doctor).
- **Quality:** 169 tests green; doctor offline PASS; secret scans clean across
  working tree and full git history (fixtures use FAKE values only).
- **Documentation:** `README.md`, `PROJECT.md`, `SETUP.md`,
  `SETUP_AR.md` (Arabic, 21 sections), `ARCHITECTURE.md`, `OPERATIONS.md`,
  `TROUBLESHOOTING.md`, `SECURITY.md`, `CONTENT_SYSTEM.md`,
  `RELEASE_REPORT.md`, this file.
- **Release packaging:** duplicate `release/` tree untracked (excluded from
  upload), `.env` never tracked, release commit pushed.

---

## REMAINING USER ACTIONS

1. **Add the six GitHub secrets** (Settings → Secrets and variables →
   Actions → New repository secret), names exactly:
   - `GROQ_API_KEYS` — https://console.groq.com → API Keys (comma-separate two
     keys for failover)
   - `TELEGRAM_BOT_TOKEN` — via `@BotFather` → `/newbot`
   - `TELEGRAM_CHAT_ID` — from `https://api.telegram.org/bot<TOKEN>/getUpdates`
   - `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET` — Google Cloud Console →
     APIs & Services → Credentials (OAuth Desktop app)
   - `YOUTUBE_REFRESH_TOKEN` — run locally:
     `python -m app youtube-oauth` (browser consent once)
2. **Grant the Google OAuth app access to your channel** (consent screen in
   Testing expires after 7 days): either press "Publish app" to In production,
   or re-run `python -m app youtube-oauth` and refresh the secret weekly.
3. **Keep the local machine out of production** — run only light commands
   locally (`doctor`, `pytest`, `status`, `schedule`); everything heavy runs
   on GitHub Actions.
4. **Store your six secret values outside this machine** (password manager).
   They exist only in GitHub Secrets and your local `.env`.

---

## FIRST TEST

Run these in order (each step proves exactly one thing — full detail in
`SETUP_AR.md` §10 / `SETUP.md`):

| # | Where | What | Success looks like |
|---|---|---|---|
| 1 | Actions → `health-check` → Run workflow | baseline | green run, Tests + Doctor (offline) pass |
| 2 | Actions → `manual` → command `doctor`, then `doctor-online` | environment + connectivity | `✓ PASS` lines; `groq_api`, `telegram`, `youtube` pass online |
| 3 | Actions → `production` → mode `sample` | content + audio + render + QC | green run, episode created under `state/episodes/` |
| 4 | Repeat step 3 unchanged | idempotency/resume | second run resumes the same episode, still green |
| 5 | Actions → `production` → mode `dry-run` | full render + `RENDER_QC`, no upload | green up to `RENDER_QC`; `long.mp4` + `qc/*.json` produced |
| 6 | Actions → `manual` → command `snapshot` | YouTube OAuth really works | channel handle/videos/subscribers printed |
| 7 | Your Telegram chat | live notification | `SUCCESS ...` or doctor report arrives |

---

## PRODUCTION ACTIVATION

1. Enable the workflow: Actions → `production` → (⋯) → **Enable workflow**
   (it ships disabled).
2. First real run: Actions → `production` → Run workflow → mode `production`
   (mode `dry-run` first if you want a no-upload rehearsal).
3. Schedule after enablement: `5 16 * * 1-6` (16:05 UTC, Mon–Sat) —
   long episodes Mon/Wed/Fri, Shorts Tue/Thu/Sat. Convert UTC to your local
   time before relying on it.
4. Pause/resume any time: (⋯) → **Disable/Enable workflow**. Never empty the
   `schedule` arrays in `config/config.json` — config validation rejects
   empty schedules.

---

## KNOWN LIMITATIONS

- QC is exactly two gates: `SCRIPT_QC` (pre-audio) and `RENDER_QC` (post-render;
  includes the audio-loudness check). There is no separate audio-QC or
  Shorts-QC stage.
- Groq free tier (30 RPM / 1K RPD per account), YouTube API quota
  (10,000 units/day ≈ 100 uploads/day to your own bucket), GitHub Actions
  free for public repos — all provider-controlled, may change; no
  permanent-free promise.
- Extra Groq keys add failover, not quota.
- Long-form Shorts metadata beyond the generated title/description is not
  customized per Short (shorts reuse episode metadata).
- Local full production (TTS/render/whisper) is intentionally unsupported on
  this machine (8 GB RAM; documented in `SETUP_AR.md` §16).

---

## IMPORTANT WARNINGS

- **Never commit secrets.** Secrets live only in GitHub Secrets and local
  `.env` (gitignored). If a key is ever pasted into a file or log, revoke and
  rotate it immediately at the provider, then scrub history.
- **`production` publishes publicly.** A `production`-mode run uploads to
  your YouTube channel and sets Made-for-Kids; use mode `dry-run` (no upload)
  until you are ready.
- **Do not delete or edit `state/`** during a run — it is the resume point.
  To retry a locked episode, set `"attempts": 0` in `state/registry.json`
  after fixing the root cause.
- **Provider limits are real:** hitting the daily Groq/YouTube quota is not a
  bug; the system waits or fails with `RED ALERT` and resumes later.
- Google OAuth consent in **Testing** mode stops refreshing after 7 days —
  publish the app or re-run OAuth weekly, or uploads fail with
  `invalid_grant`.
