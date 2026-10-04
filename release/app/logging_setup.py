"""Logging with secret redaction — no credential ever reaches a log line."""

from __future__ import annotations

import logging
import re
from pathlib import Path

_SECRET_PATTERNS = [
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]+", re.I),
    re.compile(r"bot\d{6,}:[A-Za-z0-9_\-]{20,}"),
    re.compile(r"gsk_[A-Za-z0-9]{10,}"),
    re.compile(r"KGAT_[A-Za-z0-9]{10,}"),
    re.compile(r"ya29\.[A-Za-z0-9_\-]+"),
    re.compile(r"AIza[A-Za-z0-9_\-]{20,}"),
]

REDACTED = "[REDACTED]"


def redact(text: str) -> str:
    out = text
    for pat in _SECRET_PATTERNS:
        out = pat.sub(REDACTED, out)
    return out


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        clean = redact(msg)
        if clean != msg:
            record.msg = clean
            record.args = ()
        return True


def setup_logging(level: str = "INFO", log_dir: str | Path | None = None) -> logging.Logger:
    root = logging.getLogger()
    if getattr(root, "_app_configured", False):
        return root
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s", "%H:%M:%S")
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    console.addFilter(RedactingFilter())
    root.addHandler(console)

    if log_dir:
        path = Path(log_dir)
        path.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(path / "app.log", encoding="utf-8")
        fh.setFormatter(fmt)
        fh.addFilter(RedactingFilter())
        root.addHandler(fh)

    root._app_configured = True  # type: ignore[attr-defined]
    return root


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
