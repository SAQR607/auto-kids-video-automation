# TikTok distribution (inbox drafts)

The pipeline uploads each YouTube short **also to TikTok as an inbox draft**
(via the Content Posting API, `video.upload` scope — no TikTok audit needed).
You get a Telegram message per draft and finish the post with one tap in the
TikTok app. Config: `tiktok.enabled` in `config/config.json`.

## 1. Account (one-time)

- Create the account, e.g. handle `@fernwoodfriends`, display name **Fernwood Friends**
- Bio (≤80 chars): `🌿 Gentle woodland bedtime stories · New tales Mon/Wed/Fri + shorts`
- Consider a Business account (free analytics) — switching later is fine.

## 2. Developer app (one-time, ~10 min)

1. https://developers.tiktok.com → sign in with the account above → **Manage apps → Create app**.
2. Add the product **Content Posting API** (choose **Upload**, not Direct Post).
3. Under the product config, register the redirect URI: `http://localhost:8766/`.
4. Copy the **Client Key** and **Client Secret** into `.env`
   (`TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`) and GitHub Secrets.

## 3. Connect (one-time)

```powershell
& ".\.venv\Scripts\python.exe" -X utf8 -m app tiktok-auth
```

A browser opens; approve access. The command prints `TIKTOK_ACCESS_TOKEN` /
`TIKTOK_REFRESH_TOKEN` — put them in `.env` **and** GitHub Secrets
(`gh secret set TIKTOK_ACCESS_TOKEN ...`, `gh secret set TIKTOK_REFRESH_TOKEN ...`).

## 4. Token rotation (CI)

TikTok access tokens live 24 h; refresh tokens rotate **on every refresh**.
The pipeline persists the latest pair to `state/secrets/tiktok_tokens.json`
(gitignored). In CI, set one extra secret — a classic PAT with `repo` scope —
so the workflow writes rotated tokens back into secrets automatically:

```
gh secret set TIKTOK_ROTATE_PAT --body ghp_...
```

Without it, every shorts run still works, but you will eventually get a
`TIKTOK draft FAILED … invalid_grant` warning: re-run `python -m app
tiktok-auth` and update the two secrets.

## Day-to-day

- Shorts days (Tue/Thu/Sat 16:00 UTC): after each YouTube short uploads, the
  same file lands in your TikTok inbox with title/description/hashtags filled
  in. Open TikTok → Inbox → tap the notification → publish.
- Telegram shows `📮 TikTok draft ready — tap to publish` per short.
- Failures are isolated: YouTube success is never rolled back; the draft is
  retried on the next shorts run; you get `⚠️ TikTok draft FAILED` with the
  exact TikTok error code.

## Limits & facts

- Max **5 pending inbox drafts / 24 h** (we send 2 per shorts day).
- Upload URL valid 1 h; 6 API requests/min per token.
- Unaudited apps: fine for the inbox path. Direct posting (fully automatic)
  requires TikTok's app audit — flip later without changing this pipeline.
- Videos are marked `is_aigc` (honest AI-content disclosure).

## Backlog (not built yet)

- **Clip extractor**: pull the best 30–60 s from each long video → 5–7 TikTok
  posts/week (the cadence TikTok's algorithm rewards).
- Direct post after passing TikTok's audit (`video.publish` scope).
- On-screen keyword text in the first second (render-layer change).
