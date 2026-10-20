"""Schedule computation (§29): which job is due now, config-driven, UTC.

The GitHub workflow runs hourly; this module answers "is a slot due and not
already done?" — making schedule changes config-only (no code/YAML edits beyond
the trigger cadence).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .config import Config, VALID_DAYS
from .state import Registry, Stage

# Window in which an hourly check may claim a slot (minutes): slot at 16:00,
# checks at 16:07 etc. must still claim; a later check same day also claims
# (catch-up), but only if the job hasn't run already.
CATCHUP_HOURS = 26


def _slots(cfg: Config, kind: str) -> list[tuple[int, int, int]]:
    """[(weekday, hour, minute)] from config for kind='long'|'shorts'."""
    out = []
    for slot in cfg.get(f"schedule.{kind}", []):
        day = str(slot["day"]).lower()
        hour, minute = (int(x) for x in str(slot["time_utc"]).split(":"))
        out.append((VALID_DAYS[day], hour, minute))
    return sorted(out)


def _slot_key(kind: str, when: datetime) -> str:
    return f"{kind}:{when.strftime('%Y-%m-%dT%H:%MZ')}"


def due_slots(cfg: Config, now: datetime | None = None) -> list[dict[str, Any]]:
    """All schedule slots whose time has arrived (within catch-up window) —
    includes shorts slots whose source long is already PUBLISHED."""
    now = now or datetime.now(timezone.utc)
    due: list[dict[str, Any]] = []

    for kind in ("long", "shorts"):
        for weekday, hour, minute in _slots(cfg, kind):
            # Most recent occurrence of this weekday/time at or before `now`.
            days_back = (now.weekday() - weekday) % 7
            candidate = (now - timedelta(days=days_back)).replace(
                hour=hour, minute=minute, second=0, microsecond=0, tzinfo=timezone.utc
            )
            if candidate > now:
                candidate -= timedelta(days=7)
            age = now - candidate
            if age < timedelta(0) or age > timedelta(hours=CATCHUP_HOURS):
                continue
            due.append(
                {
                    "kind": kind,
                    "slot_time": candidate.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "slot_key": _slot_key(kind, candidate),
                    "age_minutes": int(age.total_seconds() // 60),
                }
            )
    return due


def plan_due(cfg: Config, reg: Registry, now: datetime | None = None) -> list[dict[str, Any]]:
    """Join due slots with registry state; returns actionable jobs (skipping
    anything already done — idempotent hourly checks)."""
    jobs: list[dict[str, Any]] = []
    for slot in due_slots(cfg, now):
        if slot["kind"] == "long":
            ep_id = reg.episode_id_for_slot(slot["slot_key"])
            stage = reg.stage_of(ep_id)
            slot["episode_id"] = ep_id
            slot["stage"] = stage.value
            # Long-day job runs PLANNED -> ... -> SHORTS_READY (shorts are
            # generated the same day, uploaded later). FAILED stays actionable
            # for bounded retries (enforced by the pipeline runner).
            if stage not in (Stage.SHORTS_READY, Stage.SHORTS_SCHEDULED, Stage.COMPLETE):
                jobs.append(slot)
            continue

        # shorts slot: the most recent long episode (within the weekly window)
        # that still has pending shorts. Weekly cadence ships the freshest
        # long's shorts; older episodes stay shelved ("ready") by design.
        shorts_dt = datetime.strptime(slot["slot_time"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        best: tuple[datetime, str, list[str]] | None = None
        for ep_id, entry in reg.episodes().items():
            if entry.get("stage") == Stage.COMPLETE.value:
                continue
            key = str(entry.get("slot_key") or "")
            if not key.startswith("long:"):
                continue
            try:
                pub_dt = datetime.strptime(key[len("long:"):], "%Y-%m-%dT%H:%MZ").replace(
                    tzinfo=timezone.utc)
            except ValueError:
                continue
            pending = [
                sid
                for sid, sh in entry.get("shorts", {}).items()
                if sh.get("status") in ("ready", "rendering_failed", "rendered", "upload_failed")
            ]
            if not pending:
                continue
            age = shorts_dt - pub_dt
            if timedelta(0) <= age <= timedelta(days=8) and (best is None or pub_dt > best[0]):
                best = (pub_dt, ep_id, pending)
        if best is None:
            continue
        slot["episode_id"] = best[1]
        slot["pending_shorts"] = best[2]
        slot["stage"] = reg.get(best[1])["stage"]
        jobs.append(slot)
    return jobs


# Per-short statuses that still await an upload (mirrors plan_due).
_PENDING_SHORTS = ("ready", "rendering_failed", "rendered", "upload_failed")


def channel_totals(reg: Registry) -> dict[str, int]:
    """Published-video counts for the stats report: a long counts once it is
    verified on YouTube; each uploaded short counts as one video."""
    longs = sum(
        1 for e in reg.episodes().values()
        if e.get("youtube_video_id") and e.get("youtube_verified")
    )
    shorts = sum(
        1 for e in reg.episodes().values()
        for sh in e.get("shorts", {}).values()
        if sh.get("status") == "uploaded"
    )
    return {"longs": longs, "shorts": shorts, "total": longs + shorts}


def pending_shorts(reg: Registry) -> list[tuple[str, str]]:
    """(episode_id, short_id) pairs still awaiting upload, sorted."""
    out = [
        (ep_id, sid)
        for ep_id, e in reg.episodes().items()
        for sid, sh in e.get("shorts", {}).items()
        if sh.get("status") in _PENDING_SHORTS
    ]
    return sorted(out)


def _episode_for_long_slot(reg: Registry, slot_key: str) -> str | None:
    """Read-only lookup — never allocates (episode_id_for_slot would)."""
    for ep_id, entry in reg.episodes().items():
        if entry.get("slot_key") == slot_key:
            return ep_id
    return None


def next_posting(cfg: Config, reg: Registry, now: datetime | None = None) -> dict[str, Any] | None:
    """Next actionable posting event: the earliest upcoming long slot, or a
    shorts slot while uploads remain pending. Long slots always count (the
    runner creates a new episode); shorts count only while content is pending.
    Returns {kind, at, remaining_sec, count, episode_ids} or None."""
    now = now or datetime.now(timezone.utc)
    pending = pending_shorts(reg)
    candidates: list[dict[str, Any]] = []
    for kind in ("long", "shorts"):
        for weekday, hour, minute in _slots(cfg, kind):
            days_ahead = (weekday - now.weekday()) % 7
            at = (now + timedelta(days=days_ahead)).replace(
                hour=hour, minute=minute, second=0, microsecond=0, tzinfo=timezone.utc
            )
            if at <= now:
                at += timedelta(days=7)
            if kind == "shorts" and not pending:
                continue
            candidates.append({"kind": kind, "at": at})
    if not candidates:
        return None
    best = min(candidates, key=lambda c: c["at"])
    info: dict[str, Any] = {
        "kind": best["kind"],
        "at": best["at"],
        "remaining_sec": int((best["at"] - now).total_seconds()),
    }
    if best["kind"] == "shorts":
        info["count"] = len(pending)
        info["episode_ids"] = sorted({ep for ep, _ in pending})
    else:
        info["count"] = 1
        ep_id = _episode_for_long_slot(reg, _slot_key("long", best["at"]))
        info["episode_ids"] = [ep_id] if ep_id else []
    return info


def humanize_remaining(sec: int) -> str:
    """'9h 50m' / '2d 3h' / '45m' — compact remaining-time rendering."""
    sec = max(0, int(sec))
    if sec < 60:
        return "under a minute"
    days, rem = divmod(sec, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"
