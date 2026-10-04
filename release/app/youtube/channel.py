"""Channel statistics snapshot for reporting/monitoring (§52).

Uses the same refresh token as publishing (youtube.readonly scope is
requested by `python -m app youtube-oauth`).
"""

from __future__ import annotations

from typing import Any

from ..logging_setup import get_logger
from ..state import now_iso
from .errors import YouTubeError
from .oauth import build_service

log = get_logger("youtube.channel")


def channel_stats(service: Any | None = None) -> dict:
    """Fetch public channel statistics via channels.list(mine=True)."""
    svc = service if service is not None else build_service()
    resp = svc.channels().list(part="snippet,statistics", mine=True).execute()
    items = resp.get("items") or []
    if not items:
        raise YouTubeError("channels.list(mine=True) returned no channel — check OAuth scopes")
    ch = items[0]
    st = ch.get("statistics", {})
    sn = ch.get("snippet", {})
    return {
        "channel_id": ch.get("id"),
        "title": sn.get("title"),
        "handle": sn.get("customUrl"),
        "subscribers": int(st.get("subscriberCount", 0) or 0),
        "videos": int(st.get("videoCount", 0) or 0),
        "views": int(st.get("viewCount", 0) or 0),
        "hidden_subscribers": bool(st.get("hiddenSubscriberCount", False)),
        "fetched_at": now_iso(),
    }


def format_snapshot(stats: dict) -> str:
    subs = "hidden" if stats.get("hidden_subscribers") else f"{stats['subscribers']:,}"
    return (
        f"Fernwood Friends channel snapshot ({stats.get('fetched_at')})\n"
        f"title: {stats.get('title')} ({stats.get('handle') or 'no handle'})\n"
        f"subscribers: {subs}\n"
        f"videos: {stats['videos']:,}   views: {stats['views']:,}"
    )
