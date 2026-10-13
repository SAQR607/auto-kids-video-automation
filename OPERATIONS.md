# OPERATIONS.md — Runbook

## Weekly schedule (config-driven, UTC)

Defined in `config/config.json` → `schedule` — change times there, not in YAML:

| Day | 16:00 UTC slot | Job |
|---|---|---|
| Monday | `long` | Episode: generate → QC → upload → split shorts |
| Tuesday | `shorts` | Monday's 2 Shorts: render → upload |
| Wednesday | `long` | Episode |
| Thursday | `shorts` | Wednesday's 2 Shorts |
| Friday | `long` | Episode |
| Saturday | `shorts` | Friday's 2 Shorts |

`production.yml` checks **hourly** (`17 * * * *`) and claims any due slot
within a 26-hour catch-up window, so a delayed GitHub scheduled run recovers
within the hour instead of sliding many hours. Slots themselves are 16:00 UTC
Mon–Sat. Jobs are idempotent — an episode already at
`SHORTS_READY`/`COMPLETE` is skipped.

## Everyday monitoring

- **Telegram**: `✅ SUCCESS` (with YouTube link), `📊 Channel Stats` (totals
  + time until the next post), or `🚨 RED ALERT` (stage + error + attempts).
  This is the intended touchpoint.
- `health_check.yml` runs daily; check it's green.
- `python -m app status` (or **Actions → manual → status**) lists episodes and
  stages; `schedule --json` shows what's due now.

## Dispatch modes (production workflow)

| Mode | Effect |
|---|---|
| `production` | Real run: builds, QCs, publishes publicly |
| `dry-run` | Builds + QCs everything, **never publishes**; state stops at `RENDER_QC` — the next real run resumes *at* publish |
| `sample` | Like dry-run but renders only N seconds (fast validation) |

## Resuming after failures

Nothing to do manually in the common cases — the next scheduled run resumes:

- Crash mid-upload **after** the ID checkpoint → resume is verify-only
  (never double-uploads).
- Crash mid-upload **before** the checkpoint, or fresh checkout with missing
  media → the media guard rebuilds audio/render automatically.
- Shorts: only shorts whose status is `rendered`/`upload_failed` are uploaded;
  each short checkpoints independently.

## When an episode goes terminal

After `qc.max_stage_retries` (default 3) failed attempts the pipeline refuses
to retry and sends a final RED ALERT. To re-arm:

```bash
# state/registry.json → episodes.<id>:
{ "stage": "FAILED", "failed_stage": "<stage>", "attempts": 0, "error": "..." }
```

Set `"attempts": 0` (and optionally `"stage"` back to the stage you want to
re-enter). Commit/push the registry. If you need a clean slate for the slot
instead, delete that episode entry — the next due slot creates a fresh
`s01eNNN`.

## Manual interventions

| Goal | How |
|---|---|
| Re-run one episode now | `python -m app run --episode s01e00N` (local) or dispatch `production` |
| Re-upload its Shorts | `python -m app run-shorts --episode s01e00N` |
| Rebuild art assets | `python -m app assets` |
| Check credentials | `python -m app doctor [--online]` |
| Channel snapshot to Telegram | `python -m app snapshot --telegram` |
| Inspect a QC report | `state/episodes/<id>/qc/*.json` (uploaded as an artifact on failure) |

## Quota / limits budget (design headroom)

| API | Free limit | Our load |
|---|---|---|
| Groq `openai/gpt-oss-120b` | 30 RPM, 1K RPD, 8K TPM, 200K TPD (org-wide) | ~20–30 calls/episode-day; 429/413 → same-slot wait honoring `Retry-After` |
| YouTube `videos.insert` | 100/day (own bucket, 1 unit each) | 3 longs + 6 Shorts = 9 |
| YouTube daily pool | 10,000 units (thumbnails.set 50, videos.update 50) | ≈910/day incl. metadata calls |
| Telegram | 30 msg/s | 2–4 messages/day |

## Runner notes

- `ubuntu-latest`: 4 vCPU / 16 GB / 14 GB SSD. Workflows free disk (~6 GB),
  check ≥ 4 GB free before building, and cap threads
  (`TTS_THREADS=2 FFMPEG_THREADS=2 WHISPER_THREADS=2`).
- Caches: pip (setup-python) + `models/` + `~/.cache/huggingface`
  (kokoro ~120 MB, whisper tiny) — keyed on `requirements.txt`.
- Job timeout 360 min; worst case (cold TTS + render + 3 uploads) is well
  under it.
- Pushes made with `GITHUB_TOKEN` do not re-trigger workflows (no loops);
  state commits are tagged `[skip ci]` anyway.

## External scheduler (punctuality hardening)

GitHub's own `schedule:` dispatcher is unreliable — observed dispatching up
to ~8 h late and, on 2026-10-13, never firing at all. The hourly cron absorbs
moderate delays; for on-time posting an external ping service triggers the
same workflow via API, bypassing GitHub's internal scheduler entirely:

- **Endpoint**: `POST https://api.github.com/repos/SAQR607/auto-kids-video-automation/actions/workflows/production.yml/dispatches`
- **Headers**: `Authorization: Bearer <PAT>`, `Accept: application/vnd.github+json`
- **Body**: `{"ref": "master"}`
- **PAT**: fine-grained personal access token, this repo only, Repository
  permissions → **Workflows: Read and write** (the dispatch API's required
  scope). Never commit it; store it only in the ping service.
- **Cadence**: hourly (safe — `plan_due()` is idempotent and the `production`
  concurrency group queues overlap; extra triggers become "nothing due").
- Success response is **HTTP 204**. The internal hourly cron stays enabled as
  a backup; double-firing is harmless.

## Storage hygiene

- `state/` grows a few KB per episode — fine forever.
- Media is rebuilt per run and never stored; the repo stays small.
- QC artifacts on failure: 14-day retention.
