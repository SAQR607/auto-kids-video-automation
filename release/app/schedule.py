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

# Shorts publish the day AFTER their long: Mon->Tue, Wed->Thu, Fri->Sat.
_LONG_TO_SHORTS_GAP_DAYS = 1
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


def _shorts_source_long(cfg: Config, shorts_slot: datetime) -> datetime | None:
    """The long episode slot that produced content for this shorts day
    (the long published the previous day)."""
    long_days = {w for w, _, _ in _slots(cfg, "long")}
    prev_day = shorts_slot - timedelta(days=_LONG_TO_SHORTS_GAP_DAYS)
    if prev_day.weekday() not in long_days:
        return None
    for weekday, hour, minute in _slots(cfg, "long"):
        if weekday == prev_day.weekday():
            return prev_day.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return None


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

        # shorts slot: find the long episode published the previous day
        shorts_dt = datetime.strptime(slot["slot_time"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        src = _shorts_source_long(cfg, shorts_dt)
        if src is None:
            continue
        src_key = _slot_key("long", src)
        src_id = None
        for ep_id, entry in reg.episodes().items():
            if entry.get("slot_key") == src_key:
                src_id = ep_id
                break
        if src_id is None:
            continue
        entry = reg.get(src_id)
        ep_stage = entry["stage"]
        if ep_stage == Stage.COMPLETE.value:
            continue  # every short uploaded — nothing left to claim
        shorts = entry.get("shorts", {})
        pending = [
            sid
            for sid, sh in shorts.items()
            if sh.get("status") in ("ready", "rendering_failed", "rendered", "upload_failed")
        ]
        if pending:
            slot["episode_id"] = src_id
            slot["pending_shorts"] = pending
            slot["stage"] = ep_stage
            jobs.append(slot)
    return jobs
