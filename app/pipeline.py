"""Pipeline orchestration: drives an episode through the state machine (§31-§33).

Stage modules are imported lazily so `doctor`/`init`/`schedule` work before the
full build exists, and a failure in any stage is checkpointed to the registry
(attempt-bounded, resumable) and alerted via Telegram.
"""

from __future__ import annotations

import importlib
import traceback
from pathlib import Path
from typing import Any, Callable

from .config import Config, env_bool, load_config
from .logging_setup import get_logger, redact
from .state import Registry, Stage, advance_path, load_registry

log = get_logger("pipeline")

# Long-day job: (transition target, module, function) in run order.
_LONG_ORDER: list[tuple[Stage, str, str]] = [
    (Stage.SCRIPTED, "app.content.engine", "run_generation"),
    (Stage.SCRIPT_QC, "app.qc.script_qc", "check_script"),
    (Stage.AUDIO_READY, "app.audio.stages", "build_audio"),
    (Stage.RENDERING, "app.render.stages", "render_long"),
    (Stage.RENDER_QC, "app.qc.video_qc", "check_video"),
    (Stage.UPLOADING, "app.youtube.publish", "publish_long"),
    (Stage.SHORTS_READY, "app.content.shorts", "build_short_packages"),
]


class StageUnavailable(Exception):
    pass


def _call(stage_module: str, func_name: str, *args: Any, **kwargs: Any) -> Any:
    try:
        module = importlib.import_module(stage_module)
    except ModuleNotFoundError as exc:
        raise StageUnavailable(f"{stage_module} not available yet ({exc.name})") from exc
    func: Callable[..., Any] | None = getattr(module, func_name, None)
    if func is None:
        raise StageUnavailable(f"{stage_module}.{func_name} missing")
    return func(*args, **kwargs)


def _load(episode_id: str) -> tuple[Config, Registry, dict[str, Any]]:
    cfg = load_config()
    reg = load_registry(cfg.get("paths.state", "state"))
    entry = reg.get(episode_id)
    return cfg, reg, entry


def _alert_failure(cfg: Config, reg: Registry, episode_id: str, stage: Stage, error: str) -> None:
    if not cfg.get("telegram.notify_failure", True):
        return
    try:
        from . import telegram_client

        attempts = int(reg.get(episode_id).get("attempts", 0))
        msg = (
            f"RED ALERT production\n"
            f"episode: {episode_id}\n"
            f"stage: {stage.value}\n"
            f"error: {redact(error)[:400]}\n"
            f"attempts: {attempts}"
        )
        telegram_client.send_message(msg)
    except Exception as exc:  # notification must never break the run
        log.warning("failure alert could not be sent: %s", redact(str(exc)))


def _execute_stage(
    cfg: Config,
    reg: Registry,
    episode_id: str,
    stage: Stage,
    module: str,
    func: str,
    ctx: dict[str, Any],
) -> None:
    """Run one stage, checkpoint on success, capture failure (§33)."""
    log.info("=== %s :: %s ===", episode_id, stage.value)
    if reg.stage_of(episode_id) == Stage.FAILED:
        reg.unfail(episode_id)
    try:
        _call(module, func, cfg, reg, episode_id, ctx)
    except StageUnavailable as exc:
        log.error("stage %s unavailable: %s", stage.value, exc)
        reg.mark_failed(episode_id, f"stage unavailable: {exc}", failed_stage=stage.value)
        _alert_failure(cfg, reg, episode_id, stage, str(exc))
        raise SystemExit(2) from exc
    except Exception as exc:
        tb = traceback.format_exc(limit=6)
        log.error("stage %s failed: %s\n%s", stage.value, exc, tb)
        reg.mark_failed(episode_id, f"{type(exc).__name__}: {exc}", failed_stage=stage.value)
        _alert_failure(cfg, reg, episode_id, stage, f"{type(exc).__name__}: {exc}")
        max_retries = int(cfg.get("qc.max_stage_retries", 3))
        attempts = int(reg.get(episode_id).get("attempts", 0))
        if attempts >= max_retries:
            log.error("%s exhausted %d attempts — giving up", episode_id, max_retries)
        raise SystemExit(1) from exc
    if reg.stage_of(episode_id) != stage:
        # Advance, bridging one bookkeeping hop when needed
        # (RENDERING -> RENDERED -> RENDER_QC, UPLOADING -> PUBLISHED -> SHORTS_READY).
        try:
            for hop in advance_path(reg.stage_of(episode_id), stage):
                if reg.stage_of(episode_id) != hop:
                    reg.transition(episode_id, hop)
        except Exception as exc:
            msg = f"state wiring error: {type(exc).__name__}: {exc}"
            log.error("%s: %s", episode_id, msg)
            reg.mark_failed(episode_id, msg, failed_stage=stage.value)
            _alert_failure(cfg, reg, episode_id, stage, msg)
            raise SystemExit(1) from exc


def _next_index(reg: Registry, episode_id: str, order: list[tuple[Stage, str, str]]) -> int:
    current = reg.stage_of(episode_id)
    if current == Stage.FAILED:
        current = reg.resume_stage(episode_id)
    if current == Stage.COMPLETE:
        return -1
    names = [s for s, _, _ in order]
    if current == Stage.PLANNED:
        return 0
    if current in names:
        # A stage value in the registry means the PREVIOUS step finished.
        # Resume AT `current` only if the run died inside that step.
        entry = reg.get(episode_id)
        if entry.get("stage") == Stage.FAILED.value or entry.get("failed_stage") == current.value:
            return names.index(current)
        nxt = names.index(current) + 1
        return nxt if nxt <= len(names) else -1
    # Stage beyond this job's scope (e.g. SHORTS_SCHEDULED) — nothing to do.
    return -1


def _missing_media(cfg: Config, episode_id: str, entry: dict[str, Any],
                   *, need_video: bool) -> str | None:
    """Git carries state, never bytes — media built on a previous runner is
    gone on a fresh checkout. Returns why the resume point cannot be served."""
    base = Path(cfg.get("paths.state", "state")) / "episodes" / episode_id
    if not (base / "audio" / "timing.json").exists():
        return "audio/timing.json"
    if need_video:
        video = str(entry.get("video_path") or "")
        if not video or not Path(video).exists():
            return "rendered video"
        thumb = str(entry.get("thumbnail_path") or "")
        if thumb and not Path(thumb).exists():
            return "thumbnail"
    return None


def _exhausted(cfg: Config, reg: Registry, episode_id: str) -> bool:
    """True when a FAILED episode already burned its attempt budget (§33):
    retries are bounded across runs, not just within one."""
    if reg.stage_of(episode_id) != Stage.FAILED:
        return False
    entry = reg.get(episode_id)
    max_retries = int(cfg.get("qc.max_stage_retries", 3))
    attempts = int(entry.get("attempts", 0))
    if attempts < max_retries:
        return False
    log.error("%s TERMINAL: %d attempts used at %s — manual intervention required "
              "(reset 'attempts' in state/registry.json to retry)",
              episode_id, attempts, entry.get("failed_stage"))
    try:
        _alert_failure(cfg, reg, episode_id,
                       Stage(entry.get("failed_stage") or Stage.PLANNED.value),
                       f"terminal: {attempts}/{max_retries} attempts exhausted")
    except Exception:
        pass
    return True


def run_long(
    episode_id: str,
    *,
    dry_run: bool | None = None,
    sample_sec: float | None = None,
    private_test: bool = False,
    stop_after: Stage | None = None,
) -> Stage:
    """Run/resume the long-day pipeline. Returns the stage reached."""
    cfg, reg, _ = _load(episode_id)
    if _exhausted(cfg, reg, episode_id):
        raise SystemExit(f"{episode_id}: attempt budget exhausted (see log)")
    dry = env_bool("DRY_RUN", False) if dry_run is None else dry_run
    ctx: dict[str, Any] = {"dry_run": dry, "sample_sec": sample_sec, "private_test": private_test,
                           "kind": "long", "allow_regen": True}
    if dry and stop_after is None:
        # Dry-run builds + QCs everything but never publishes; state is left
        # at RENDER_QC so the next real run resumes AT publish_long (§41).
        stop_after = Stage.RENDER_QC

    start = _next_index(reg, episode_id, _LONG_ORDER)
    if start < 0:
        log.info("%s already complete — nothing to do", episode_id)
        return Stage.COMPLETE
    if start > 0:
        log.info("%s resuming (stage %s)", episode_id, reg.stage_of(episode_id).value)

    # Media guard: a resume that would SKIP the audio/render steps still needs
    # their files. If they are absent (fresh checkout), fall back to
    # AUDIO_READY so they rebuild instead of failing at publish time.
    render_i = _order_index(Stage.RENDERING, _LONG_ORDER)
    if start >= render_i:
        missing = _missing_media(cfg, episode_id, reg.get(episode_id),
                                 need_video=start > render_i)
        if missing:
            log.warning("%s missing %s (media does not cross runs) — rebuilding from audio",
                        episode_id, missing)
            entry = reg.get(episode_id)
            entry["stage"] = Stage.AUDIO_READY.value
            entry["failed_stage"] = Stage.AUDIO_READY.value
            reg.save()
            start = _order_index(Stage.AUDIO_READY, _LONG_ORDER)

    for stage, module, func in _LONG_ORDER[start:]:
        if stop_after is not None and _order_index(stop_after, _LONG_ORDER) < _order_index(stage, _LONG_ORDER):
            return reg.stage_of(episode_id)
        _execute_stage(cfg, reg, episode_id, stage, module, func, ctx)
    return reg.stage_of(episode_id)


def run_shorts(episode_id: str, *, dry_run: bool | None = None, private_test: bool = False) -> Stage:
    """Shorts-day job: render + publish pending shorts of a published long.

    Per-short status drives idempotency: ready->rendered->uploaded, so a killed
    runner resumes exactly where it stopped (§32).
    """
    cfg, reg, entry = _load(episode_id)
    if _exhausted(cfg, reg, episode_id):
        raise SystemExit(f"{episode_id}: attempt budget exhausted (see log)")
    dry = env_bool("DRY_RUN", False) if dry_run is None else dry_run
    ctx: dict[str, Any] = {"dry_run": dry, "private_test": private_test, "kind": "shorts"}

    if reg.stage_of(episode_id) == Stage.FAILED:
        reg.unfail(episode_id)
    st = reg.stage_of(episode_id)
    if st == Stage.COMPLETE:
        log.info("%s already complete", episode_id)
        return st
    if st not in (Stage.SHORTS_READY, Stage.SHORTS_SCHEDULED):
        raise SystemExit(f"{episode_id} is at {st.value}; shorts day requires SHORTS_READY")

    shorts: dict[str, Any] = dict(reg.get(episode_id).get("shorts", {}))
    # Media guard: a short marked 'rendered' whose file is gone (fresh
    # checkout) must re-render before it can upload.
    for sid, sh in shorts.items():
        if sh.get("status") in ("rendered", "upload_failed"):
            vp = str(sh.get("video_path") or "")
            if not vp or not Path(vp).exists():
                log.warning("%s %s rendered file missing (media does not cross runs) — re-rendering",
                            episode_id, sid)
                sh["status"] = "ready"
                sh.pop("video_path", None)
                reg.save()
    render_ids = [sid for sid, sh in shorts.items() if sh.get("status") in ("ready", "rendering_failed")]
    upload_ids = [sid for sid, sh in shorts.items() if sh.get("status") in ("rendered", "upload_failed")]

    if render_ids:
        ctx["short_ids"] = render_ids
        _execute_stage(cfg, reg, episode_id, Stage.SHORTS_SCHEDULED, "app.render.stages", "render_shorts", ctx)
    elif reg.stage_of(episode_id) == Stage.SHORTS_READY:
        reg.transition(episode_id, Stage.SHORTS_SCHEDULED)

    if dry:
        log.warning("%s DRY RUN — shorts publishing skipped (shorts stay 'rendered'; "
                    "next real run-shorts uploads them)", episode_id)
        return reg.stage_of(episode_id)

    if reg.stage_of(episode_id) == Stage.SHORTS_SCHEDULED:
        ctx["short_ids"] = upload_ids or list(shorts.keys())
        _execute_stage(cfg, reg, episode_id, Stage.COMPLETE, "app.youtube.publish", "publish_shorts", ctx)
    return reg.stage_of(episode_id)


def _order_index(stage: Stage, order: list[tuple[Stage, str, str]]) -> int:
    for i, (s, _, _) in enumerate(order):
        if s == stage:
            return i
    return len(order)
