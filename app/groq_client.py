"""Groq multi-key failover client (§25).

Rules (spec):
- Comma-separated key pool from GROQ_API_KEYS.
- Bounded exponential backoff — never retry forever.
- Auth errors (401/403) disable a slot for the process; rotate through slots;
  when every slot has failed once on auth -> GroqExhausted.
- Rate limits (429) rotate slot + backoff.
- Server errors/timeouts backoff on the same slot.
- Logs only `groq_key_slot_used` — never a key.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from typing import Any

from .logging_setup import get_logger

log = get_logger("groq")

API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqError(Exception):
    pass


class GroqExhausted(GroqError):
    pass


class GroqKeyPool:
    """Rotation state across a bounded set of key slots."""

    def __init__(self, keys: list[str]):
        if not keys:
            raise GroqExhausted("No Groq keys configured (GROQ_API_KEYS)")
        self._keys = list(keys)
        self._index = 0
        self._disabled: set[int] = set()
        self._auth_failed = 0

    @property
    def size(self) -> int:
        return len(self._keys)

    def current(self) -> tuple[int, str]:
        return self._index, self._keys[self._index]

    def rotate(self) -> None:
        """Move to next healthy slot; raise GroqExhausted when all auth-failed."""
        for _ in range(self.size):
            self._index = (self._index + 1) % self.size
            if self._index not in self._disabled:
                return
        raise GroqExhausted("All Groq key slots failed authentication")

    def mark_auth_failed(self) -> None:
        self._disabled.add(self._index)
        self._auth_failed += 1

    @property
    def healthy_remaining(self) -> int:
        return self.size - len(self._disabled)


def _post_chat(payload: dict[str, Any], key: str, timeout: int) -> tuple[int, str]:
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace") if exc.fp else ""
        return exc.code, body
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise GroqError(f"network error: {exc}") from exc


class GroqClient:
    def __init__(self, keys: list[str], *, model: str, max_tokens: int = 8192,
                 temperature: float = 0.8, timeout_sec: int = 120,
                 max_attempts: int = 6, backoff_base: float = 2.0,
                 backoff_max: float = 60.0, sleep=time.sleep):
        self.pool = GroqKeyPool(keys)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout_sec = timeout_sec
        self.max_attempts = max_attempts
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self._sleep = sleep

    def chat(self, messages: list[dict[str, str]], *, temperature: float | None = None,
             json_mode: bool = False) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature if temperature is None else temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        last_error: str | None = None
        for attempt in range(self.max_attempts):
            slot, key = self.pool.current()
            log.debug("groq request attempt=%d groq_key_slot_used=%d model=%s", attempt + 1, slot, self.model)
            try:
                status, body = _post_chat(payload, key, self.timeout_sec)
            except GroqError as exc:
                last_error = str(exc)
                delay = min(self.backoff_max, self.backoff_base * (2 ** attempt))
                log.warning("groq network error (slot %d): %s — backoff %.1fs", slot, exc, delay)
                self._sleep(delay)
                continue

            if status == 200:
                try:
                    data = json.loads(body)
                    return data["choices"][0]["message"]["content"]
                except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
                    raise GroqError(f"malformed Groq response: {exc}") from exc

            if status in (401, 403):
                log.error("groq auth failed groq_key_slot_used=%d status=%d", slot, status)
                self.pool.mark_auth_failed()
                try:
                    self.pool.rotate()
                except GroqExhausted:
                    raise
                last_error = f"auth failed on slot {slot}"
                continue

            if status == 429:
                log.warning("groq rate limited groq_key_slot_used=%d — rotating", slot)
                try:
                    self.pool.rotate()
                except GroqExhausted:
                    pass
                delay = min(self.backoff_max, self.backoff_base * (2 ** attempt))
                last_error = "rate limited"
                self._sleep(delay)
                continue

            # 5xx and other server-side errors: backoff, stay on slot
            last_error = f"http {status}"
            delay = min(self.backoff_max, self.backoff_base * (2 ** attempt))
            log.warning("groq server error %d (slot %d) — backoff %.1fs", status, slot, delay)
            self._sleep(delay)

        raise GroqExhausted(f"Groq call failed after {self.max_attempts} attempts: {last_error}")


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def extract_json(text: str) -> Any:
    """Pull the first valid JSON object/array out of LLM output (fences, prose)."""
    candidates: list[str] = []
    for match in _FENCE_RE.finditer(text):
        candidates.append(match.group(1).strip())
    stripped = text.strip()
    candidates.append(stripped)
    for opener, closer in (("{", "}"), ("[", "]")):
        start = stripped.find(opener)
        end = stripped.rfind(closer)
        if start != -1 and end > start:
            candidates.append(stripped[start : end + 1])
    for cand in candidates:
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            continue
    raise ValueError(f"No valid JSON found in LLM output (starts: {text[:120]!r})")
