# `app/youtube/` — YouTube Publishing

## Module Responsibilities

Publishing stages for the long episode: OAuth credentials, resumable upload with
resume-safe checkpointing, verify poll, metadata/thumbnail, channel stats, and
error classification.

## Current-layer Index

| File | Role |
|---|---|
| `oauth.py` | Credentials + API service factory from env (`YOUTUBE_CLIENT_ID/SECRET/REFRESH_TOKEN`); one-time installed-app flow via `python -m app youtube-oauth`. Single `youtube` scope covers every call |
| `publish.py` | Stage `UPLOADING` (`publish_long`): resumable upload → verify poll → thumbnail → Telegram success alert. Stage funcs **never transition** (pipeline contract) |
| `metadata.py` | `videos.insert` bodies + growth layer: made-for-kids flag, privacy (private for tests / public real), merges static keyword bank with per-episode tags from the QC-passed package |
| `channel.py` | `channels.list` stats snapshot for reporting/monitoring (`python -m app snapshot`) |
| `errors.py` | Error taxonomy: **quota** (never retried — doesn't clear in-run) vs **transient** 5xx/network (bounded backoff) vs **fatal** (fail fast) |

## Resume-Safety Contract (critical)

`youtube_video_id` is checkpointed to the registry **immediately after upload,
BEFORE verification** — a crash during YouTube processing resumes at
verify-only, so an episode is never double-uploaded. Any new publish flow must
preserve this ordering.

## Development Notes

- Reuse `errors.py` classification for any new API call; never blind-retry quota errors.
- Titles/descriptions/tags must come from the QC-passed package — do not generate
  metadata here (kids-safety rules live in `app/qc/`).
- Credentials only via env (GitHub Secrets); `python -m app youtube-patch` refreshes
  thumbnail/description on an already-published episode.
