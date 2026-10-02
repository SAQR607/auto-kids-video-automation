# SETUP.md — One-time Setup Guide

You will: create the GitHub repo, add secrets, run the YouTube OAuth flow once,
and trigger the first run. ~30 minutes, all manual steps in a browser.

> Local machine rule: everything below runs **on GitHub Actions** except the
> OAuth helper (`youtube-oauth`), which needs your browser once. Never run
> production (full TTS/render/publish) on your laptop.

## 1. Prerequisites

- GitHub account (public repo = free unlimited Actions)
- Groq API key(s): https://console.groq.com → API Keys
- Telegram bot: talk to [@BotFather](https://t.me/BotFather) → `/newbot`
- Google Cloud project (for YouTube OAuth)
- Local dev machine with Python 3.12 (only for tests + the OAuth helper)

## 2. Push the code

```bash
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin master
```

## 3. GitHub Secrets

Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Name | Value |
|---|---|
| `GROQ_API_KEYS` | Your Groq key. With 2+ keys (comma-separated) the client gets failover |
| `TELEGRAM_BOT_TOKEN` | From BotFather (`123456:ABC...`) |
| `TELEGRAM_CHAT_ID` | Your chat/channel ID (see step 4) |
| `YOUTUBE_CLIENT_ID` | From Google Cloud (step 5) |
| `YOUTUBE_CLIENT_SECRET` | From Google Cloud (step 5) |
| `YOUTUBE_REFRESH_TOKEN` | From `python -m app youtube-oauth` (step 5) |

`GROQ_API_KEYS` is mandatory; Telegram is strongly recommended; the three
YouTube secrets become mandatory at publish time (doctor WARNs until then).

## 4. Telegram chat ID

1. Send any message to your bot (or add it to a channel as admin).
2. Open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser.
3. Read `result[].message.chat.id` (channels are negative numbers).

## 5. YouTube OAuth (one-time, local browser)

1. Google Cloud Console → create project → **enable YouTube Data API v3**.
2. **OAuth consent screen**: External, add yourself under Test users.
3. **Credentials → Create → OAuth client ID → Desktop app** → copy Client ID
   and Client Secret.
4. Locally:

   ```bash
   python -m app init
   # put YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET into .env, then:
   python -m app youtube-oauth
   ```

5. Open the printed URL, approve access, paste the code back into the
   terminal. The command prints `YOUTUBE_REFRESH_TOKEN` — put it in GitHub
   Secrets (and optionally `.env`).

## 6. Verify before the first real run

Trigger in this order (Actions → workflow → **Run workflow**):

1. **`health_check`** → command runs the full test suite + doctor. Must be green.
2. **`production`** with `mode=sample` → builds seconds of an episode end-to-end
   (Groq → audio → render → QC, no publishing).
3. **`production`** with `mode=dry-run` → full-length build + QC, nothing
   published; state stops at `RENDER_QC`.
4. Real run: `mode=production`, or just wait for the Mon–Sat 16:05 UTC cron.

Watch the Telegram chat: a **SUCCESS** message with the YouTube link means the
loop is closed; a **RED ALERT** message names the failing stage.

## 7. Channel housekeeping (YouTube Studio, once)

- Set the channel's made-for-kids setting (the API also sends
  `selfDeclaredMadeForKids=true` per video).
- Verify the channel (required before videos > 15 min — our longs are ≤10 min,
  but verification also unlocks custom thumbnails if you ever set them).

## Checklist

- [ ] Repo pushed, `master` default branch
- [ ] Secrets: `GROQ_API_KEYS` (+ Telegram, + YouTube ×3)
- [ ] `health_check` green
- [ ] `production` `mode=sample` green
- [ ] `production` `mode=dry-run` green (state shows `RENDER_QC`)
- [ ] First real run publishes and reports SUCCESS on Telegram
