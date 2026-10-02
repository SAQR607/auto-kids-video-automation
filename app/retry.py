"""Bounded retry helpers with exponential backoff (§25, §42)."""

from __future__ import annotations

import random
import time
from typing import Callable, Iterable, Type, TypeVar

from .logging_setup import get_logger

T = TypeVar("T")
log = get_logger("retry")


class RetryExhausted(Exception):
    def __init__(self, message: str, last_error: BaseException | None = None):
        super().__init__(message)
        self.last_error = last_error


def backoff_delay(attempt: int, base: float = 2.0, cap: float = 60.0, jitter: bool = True) -> float:
    """attempt is 0-based; bounded exponential with full jitter."""
    delay = min(cap, base * (2 ** attempt))
    if jitter:
        delay = random.uniform(delay * 0.5, delay)
    return delay


def call_with_backoff(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    base: float = 2.0,
    cap: float = 60.0,
    retry_on: Iterable[Type[BaseException]] = (Exception,),
    sleep: Callable[[float], None] = time.sleep,
    label: str = "call",
) -> T:
    """Retry fn up to `attempts` times with bounded exponential backoff.

    Never retries forever (§25).
    """
    retry_on_tuple = tuple(retry_on)
    last_error: BaseException | None = None
    for attempt in range(attempts):
        try:
            return fn()
        except retry_on_tuple as exc:  # noqa: PERF203
            last_error = exc
            if attempt == attempts - 1:
                break
            delay = backoff_delay(attempt, base, cap)
            log.warning("%s failed (attempt %d/%d): %s — retrying in %.1fs", label, attempt + 1, attempts, exc, delay)
            sleep(delay)
    raise RetryExhausted(f"{label} failed after {attempts} attempts", last_error)
