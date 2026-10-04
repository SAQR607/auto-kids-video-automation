# RELEASE_REPORT.md — Final Delivery Report

Date: 2026-10-02 (UTC+03 local) · Branch: `master` · Release commit: `2a0d431`
Prepared for: final hand-off of the Fernwood Friends automated content system.

---

## 1. Deliverables

| Artifact | Path | Size |
|---|---|---|
| Release package | `release/PROJECT_FINAL_2026-10-02.zip` | 3,582,565 bytes (≈3.4 MB) |
| This report | `release/RELEASE_REPORT.md` | — |

SHA-256 of the ZIP:

```
F37829822C4688B64BC982853932F6651EB2F0EE0103FA5F221ECD97B9F62B9A
```

Built with `git archive --format=zip HEAD` — only tracked files from the release
commit, therefore byte-identical to the repository tree (no local-only files,
no `.env`, no build artifacts).

## 2. Pre-package validation (repository)

| Check | Result |
|---|---|
| `git status` | clean before and after packaging |
| Unit tests (`python -m pytest -q`) | **169 passed, exit 0** |
| `python -m app doctor` (offline) | **PASS** — 13 checks PASS, 2 expected WARNs (single Groq key slot; YouTube secrets not set locally) |
| Secret scan of working tree + git history | clean (history previously scrubbed; fixtures use FAKE values) |
| `config/config.json` vs `config.example.json` | identical, no secrets |
| Tracked files | 448 |

## 3. ZIP validation (12-point checklist)

| # | Check | Result |
|---|---|---|
| 1 | Entry inventory | 511 entries = 448 files + 63 directories |
| 2 | Root structure | clean root (no wrapper folder): `app/`, `tests/`, `config/`, `state/`, `assets/`, `universe/`, `.github/`, docs, `requirements.txt`, `pytest.ini` |
| 3 | `.env` excluded | only `.env.example` (placeholder template) present; no `.env`/`.env.*` |
| 4 | Forbidden artifacts excluded | 0 matches for `*.zip`, `*.pyc`, `__pycache__/`, `.venv/`, `logs/`, `models/` |
| 5 | Secret scan (content of every file) | **0 hits** across Groq-key, Telegram-token, Google-API-key and `client_secret/refresh_token/bot_token` assignment patterns |
| 6 | GitHub workflows included | `production.yml`, `manual.yml`, `health_check.yml` (3 files) |
| 7 | Documentation set included | `README.md`, `PROJECT.md`, `SETUP.md`, `SETUP_AR.md`, `ARCHITECTURE.md`, `OPERATIONS.md`, `TROUBLESHOOTING.md`, `SECURITY.md`, `CONTENT_SYSTEM.md` |
| 8 | Arabic manual | `SETUP_AR.md` present with all 30 sections (incl. §26 local-machine safety rule); it is the only Arabic file |
| 9 | Config example | `config/config.example.json` valid JSON, no secret values |
| 10 | Test suite included | `tests/` (169 tests) + `pytest.ini` |
| 11 | `release/` not self-included | 0 entries under `release/` (report/zip are not part of the package payload) |
| 12 | Extraction succeeds | ZIP expands cleanly to a fresh directory (Windows `Expand-Archive`) |

## 4. Fresh-extraction test run

Environment: extracted copy in a clean temp directory, using Python 3.12 venv —
no `.env`, no seeded secrets, no pre-existing `state/` writes.

| Step | Command | Result |
|---|---|---|
| CLI entry | `python -m app --help` | exit 0; all 11 subcommands listed |
| Scaffolding | `python -m app init` | exit 0; created `workspace/` and `.env` from example (placeholders only) |
| Doctor | `python -m app doctor` | 13 PASS, `groq_keys` **FAIL (expected — no secrets in fresh copy)**, YouTube WARN, exit 1 as designed |
| State read | `python -m app status` | lists tracked episode state from the package |
| Schedule | `python -m app schedule` | `nothing due` (correct outside slots) |
| Full suite | `python -m pytest -q` | **169 passed, exit 0** |

Notes:

- The only failing check (`groq_keys`) is the designed gate for missing secrets;
  adding `GROQ_API_KEYS` flips it to PASS (WARN with one key, PASS with 2+).
- Models are intentionally not shipped (Kokoro ≈120 MB downloads to `models/`
  on first production run; Whisper tiny downloads on demand when
  `QC_TRANSCRIBE=1`).

## 5. What is intentionally inside / outside the package

**Inside (by design):**

- `state/` — git carries state, never media bytes: `registry.json`, episode
  `package.json`, story memory are committed so a fresh checkout resumes
  exactly where the previous run stopped. They contain content data only.
- `config/config.json` — identical to the example; no secrets ever live in
  config files.
- `.env.example` — placeholder template (`REPLACE...` values).

**Outside (never packaged):**

- `.env`, any real Groq/Telegram/Google credential, `logs/`, `models/`,
  `__pycache__`, virtual environments, previous ZIP archives.

**Secret status:** repository history and package content verified secret-free;
secrets are supplied only at runtime via GitHub Secrets / `.env`
(`GROQ_API_KEYS`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `YOUTUBE_CLIENT_ID`,
`YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN` — names only, no values).

## 6. Audit findings carried into the manual (SETUP_AR.md)

The final audit compared documentation with implementation; `SETUP_AR.md`
documents actual behavior, including:

- Exactly two QC gates exist (`SCRIPT_QC`, `RENDER_QC`) — no standalone audio or
  shorts QC stage; audio loudness (≥ −45 dB) is checked inside `RENDER_QC`.
- Long-day pipeline ends at `SHORTS_READY`; shorts upload on their own day
  (Tue/Thu/Sat) → `COMPLETE`.
- Config keys read by code vs. informational-only keys are classified per key
  (e.g. `qc.max_stage_retries` and `telegram.notify_failure` are live;
  `telegram.enabled/notify_publish/channel_snapshot`, `youtube.privacy_*`,
  `render.crf/preset`, `duration.*_target_sec` etc. are not read — documented
  honestly, no application code was modified).
- Config validation requires non-empty `schedule` arrays — pausing production is
  done by disabling the workflow, never by emptying the schedule (SETUP_AR §28).
- Local-machine safety rule (§26): production work runs only on GitHub Actions.

## 7. How to use the package

1. Unzip `PROJECT_FINAL_2026-10-02.zip` to a target folder.
2. `python -m venv .venv` + activate + `pip install -r requirements.txt`.
3. `python -m app init`, fill `.env`, then `python -m app doctor`.
4. `python -m pytest -q` (169 tests) — must be green.
5. Push to GitHub, add the six secrets, follow `SETUP_AR.md` (Arabic) or
   `SETUP.md` (English): `health-check` → `production` `sample` →
   `production` `dry-run` → first real run.

## 8. Validation summary

```
ZIP entries ......... 511 (448 files + 63 dirs), root-level layout
Secret scan ......... 0 hits (4 pattern families, every file content)
Forbidden files ..... 0 (.env / *.zip / logs / models / pycache / venv)
Fresh extract ....... CLI ok · init ok · doctor gated on secrets (expected) · 169/169 tests pass
Repo pre-package .... 169/169 tests pass · doctor PASS (2 expected WARNs) · git clean
Release commit ...... 2a0d431 (master)
```

RELEASE STATUS: **READY** — package passes every structural, secret, and
functional check; no blockers found.
