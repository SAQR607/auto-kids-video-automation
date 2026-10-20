"""Telegram notifications: publish success + failure alerts, sanitized (§36)."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .config import env_str
from .logging_setup import get_logger, redact

log = get_logger("telegram")


class TelegramError(Exception):
    pass


def _api(method: str, payload: dict[str, Any], timeout: int = 20) -> dict[str, Any]:
    token = env_str("TELEGRAM_BOT_TOKEN")
    if not token:
        raise TelegramError("TELEGRAM_BOT_TOKEN not configured")
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        raise TelegramError(f"telegram HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise TelegramError(f"telegram network error: {exc}") from exc
    if not body.get("ok"):
        raise TelegramError(f"telegram api error: {body.get('description', 'unknown')}")
    return body


def send_message(text: str, *, max_len: int = 4000,
                 buttons: list[list[dict[str, str]]] | None = None) -> bool:
    """Send a message (optionally with inline keyboard buttons); returns True
    on success. Failures are logged, never raised (notification must not
    break the pipeline)."""
    chat_id = env_str("TELEGRAM_CHAT_ID")
    if not chat_id:
        log.warning("telegram disabled: TELEGRAM_CHAT_ID not set")
        return False
    if len(text) > max_len:
        text = text[: max_len - 1] + "…"
    payload: dict[str, Any] = {"chat_id": chat_id, "text": redact(text)}
    if buttons:
        payload["reply_markup"] = json.dumps({"inline_keyboard": buttons})
    try:
        _api("sendMessage", payload)
        return True
    except TelegramError as exc:
        log.error("telegram send failed: %s", redact(str(exc)))
        return False


def send_file(path: str, *, caption: str = "") -> bool:
    chat_id = env_str("TELEGRAM_CHAT_ID")
    if not chat_id:
        return False
    try:
        boundary = "----fernwoodupload"
        with open(path, "rb") as fh:
            file_bytes = fh.read()
        import os

        parts: list[bytes] = []
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n".encode())
        if caption:
            parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{redact(caption)}\r\n".encode())
        name = os.path.basename(path)
        ctype = "video/mp4" if path.endswith(".mp4") else "application/octet-stream"
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"document\"; filename=\"{name}\"\r\n"
            f"Content-Type: {ctype}\r\n\r\n".encode()
            + file_bytes
            + b"\r\n"
        )
        parts.append(f"--{boundary}--\r\n".encode())
        body = b"".join(parts)
        token = env_str("TELEGRAM_BOT_TOKEN")
        if not token:
            return False
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendDocument",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8", "replace"))
        return bool(result.get("ok"))
    except Exception as exc:
        log.error("telegram file send failed: %s", redact(str(exc)))
        return False


def get_me() -> dict[str, Any]:
    return _api("getMe", {})


# --- message formatters (pure — no network; shared by publish + pipeline) ---


def format_success_long(episode_id: str, title: str, video_id: str, privacy: str,
                        script_qc: str, video_qc: str) -> str:
    return (
        "✅ SUCCESS — Long video published\n"
        "\n"
        f"🎬 {title}\n"
        f"🆔 {episode_id}\n"
        f"🔗 https://youtu.be/{video_id}\n"
        f"👁 Privacy: {privacy}\n"
        f"🧼 QC: script {script_qc} · video {video_qc}\n"
        "📣 CTA: parent-facing like/subscribe line spoken (end of video)"
    )


def format_success_shorts(episode_id: str, uploaded: list[str], total: int) -> str:
    nums = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]
    links = "\n".join(
        f"{nums[i] if i < len(nums) else '▫️'} https://youtu.be/{vid}"
        for i, vid in enumerate(uploaded)
    )
    return (
        "✅ SUCCESS — Shorts published\n"
        "\n"
        f"🆔 {episode_id}\n"
        f"📱 Uploaded: {len(uploaded)}/{total}"
        + (f"\n\n{links}" if links else "")
    )


def format_tiktok_draft(episode_id: str, short_id: str, title: str, publish_id: str) -> str:
    return (
        "📮 TikTok draft ready — tap to publish\n"
        "\n"
        f"🆔 {episode_id}/{short_id}\n"
        f"✏️ {title}\n"
        f"🧾 {publish_id}\n"
        "👉 Open TikTok → Inbox → finish & publish"
    )


def format_tiktok_warning(episode_id: str, short_id: str, error: str) -> str:
    return (
        "⚠️ TikTok draft FAILED (YouTube upload unaffected)\n"
        "\n"
        f"🆔 {episode_id}/{short_id}\n"
        f"error: {error}\n"
        "Will retry on the next shorts run"
    )


def format_stats(totals: dict[str, int], next_info: dict[str, Any] | None) -> str:
    """Channel totals + time until the next posting event (UTC + local)."""
    from .schedule import humanize_remaining

    lines = [
        "📊 Channel Stats",
        "",
        f"📹 Total videos: {totals.get('total', 0)}",
        f"   🎬 Long: {totals.get('longs', 0)}",
        f"   📱 Shorts: {totals.get('shorts', 0)}",
        "",
    ]
    if not next_info:
        lines.append("⏭ Next post: none scheduled")
        return "\n".join(lines)
    at = next_info["at"]
    when = at.strftime("%a %d %b %H:%M UTC")
    local = at.astimezone()
    if local.utcoffset() != at.utcoffset():
        when += f" ({local.strftime('%a %d %b %H:%M')} local)"
    if next_info["kind"] == "long":
        eps = next_info.get("episode_ids") or []
        label = f"🎬 Long — {eps[0]}" if eps else "🎬 Long (new episode)"
    else:
        eps = next_info.get("episode_ids") or []
        ep_label = f" — {'/'.join(eps)}" if eps else ""
        label = f"📱 Shorts ×{next_info.get('count', 0)}{ep_label}"
    lines.append(f"⏭ Next post: {label}")
    lines.append(f"🕐 in {humanize_remaining(next_info['remaining_sec'])} — {when}")
    return "\n".join(lines)


def format_alert(episode_id: str, stage: str, error: str, attempts: int,
                 max_attempts: int | None = None) -> str:
    att = f"{attempts}/{max_attempts}" if max_attempts else str(attempts)
    return (
        "🚨 RED ALERT — production failed\n"
        "\n"
        f"episode: {episode_id or '-'}\n"
        f"stage: {stage}\n"
        f"error: {error}\n"
        f"attempts: {att}"
    )
