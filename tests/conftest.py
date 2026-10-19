"""Shared test isolation.

Any test that touches cli/doctor may call load_env(), which copies .env
(including real TikTok credentials) into os.environ for the WHOLE session.
Autouse fixtures run before every test, so TikTok presence is decided by
each test's own monkeypatch.setenv — never by leftover real secrets.
"""

from __future__ import annotations

import pytest

_TIKTOK_KEYS = (
    "TIKTOK_CLIENT_KEY",
    "TIKTOK_CLIENT_SECRET",
    "TIKTOK_ACCESS_TOKEN",
    "TIKTOK_REFRESH_TOKEN",
)


@pytest.fixture(autouse=True)
def _isolate_tiktok_env(monkeypatch):
    for key in _TIKTOK_KEYS:
        monkeypatch.delenv(key, raising=False)
