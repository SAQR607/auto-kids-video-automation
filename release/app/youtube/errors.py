"""YouTube API error taxonomy: quota vs transient vs fatal (§49).

Quota errors must NEVER be retried (they don't clear within a run); transient
5xx/network errors get bounded backoff; everything else fails fast.
"""

from __future__ import annotations

import json
from typing import Any


class YouTubeError(RuntimeError):
    """Base error for the publishing layer."""


class QuotaExceeded(YouTubeError):
    """Daily/minute quota exhausted — retrying now is pointless (§50)."""


class UploadFailed(YouTubeError):
    """Resumable upload could not complete."""


def _status_of(exc: BaseException) -> int | None:
    resp = getattr(exc, "resp", None)
    status = getattr(resp, "status", None)
    if status is None:
        status = getattr(exc, "status", None)
    try:
        return int(status) if status is not None else None
    except (TypeError, ValueError):
        return None


def _reasons_of(exc: BaseException) -> list[str]:
    content = getattr(exc, "content", None)
    if not content:
        return []
    try:
        data: Any = json.loads(content.decode("utf-8", "replace") if isinstance(content, bytes) else content)
        errs = data.get("error", {}).get("errors", [])
        return [str(e.get("reason", "")) for e in errs]
    except Exception:
        return []


_QUOTA_REASONS = {"quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded",
                  "userRateLimitExceeded", "sharingRateLimitExceeded"}


def classify(exc: BaseException) -> str:
    """Return 'quota' | 'transient' | 'fatal' for an API/transport error."""
    if isinstance(exc, QuotaExceeded):
        return "quota"
    status = _status_of(exc)
    reasons = set(_reasons_of(exc))
    if status in (403, 429) and reasons & _QUOTA_REASONS:
        return "quota"
    if status == 429:
        return "quota"
    if status in (408, 429, 500, 502, 503, 504):
        return "transient"
    if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
        return "transient"
    if status is not None and 400 <= status < 500:
        return "fatal"
    # Unknown non-HTTP error: fail fast rather than mask a bug with retries.
    return "fatal"
