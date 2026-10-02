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


def send_message(text: str, *, max_len: int = 4000) -> bool:
    """Send a message; returns True on success. Failures are logged, never raised
    (notification must not break the pipeline)."""
    chat_id = env_str("TELEGRAM_CHAT_ID")
    if not chat_id:
        log.warning("telegram disabled: TELEGRAM_CHAT_ID not set")
        return False
    if len(text) > max_len:
        text = text[: max_len - 1] + "…"
    try:
        _api("sendMessage", {"chat_id": chat_id, "text": redact(text)})
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
