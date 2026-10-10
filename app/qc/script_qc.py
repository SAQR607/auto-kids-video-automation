"""Stage SCRIPT_QC: editorial/policy gate on the generated package (§15).

Structural validation is re-run as a floor (defense in depth), then the checks
the structural validator does not cover: scene line-count recipe, narration
length, line repetition, English-only ASCII text, speaker coverage, hook
presence, and title reuse against the registry.

Writes qc/script_qc.json + a registry marker; raises ScriptQCError on FAIL so
the pipeline checkpoints FAILED (§33). Warnings never fail the stage.

When the pipeline allows it (ctx['allow_regen']), a failing package is
regenerated once with the QC errors as feedback — otherwise a resume would
deterministically re-run this same check against the same file forever.
The editorial checks are also reused by the generator's repair loop
(collect_script_errors), so most QC failures are prevented at generation time.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..config import Config
from ..content.universe import Universe
from ..content.validate import estimate_long_seconds, validate_package
from ..logging_setup import get_logger
from ..state import Registry, now_iso

log = get_logger("script_qc")

# Bounds calibrated against the real generator output (5 lines/scene,
# narration 34-40 words, dialogue 6-11 words) with light headroom.
NARRATION_WORDS = (30, 50)
DIALOGUE_LINES_PER_SCENE = (3, 6)
DIALOGUE_WORDS = (5, 14)
REPEAT_LIMIT = 3

_NON_ASCII = re.compile(
    r"[^\x09\x0a\x0d\x20-\x7e\u00a0-\u00ff\u00ad\u2010\u2011\u2012"
    r"\u2018\u2019\u201c\u201d\u2013\u2014\u2026\u00b7]"
)


class ScriptQCError(RuntimeError):
    """Script QC FAIL — pipeline marks the episode FAILED."""


def _words(text: str) -> int:
    return len(re.findall(r"\w+", text or ""))


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _iter_text_fields(pkg: dict[str, Any]):
    """Yield (where, text) for every human-readable string in the package."""
    for key in ("title", "premise", "hook", "learning_spine", "arc_crumb"):
        if isinstance(pkg.get(key), str):
            yield key, pkg[key]
    for i, scene in enumerate(pkg.get("scenes", []), 1):
        where = f"scene {i}"
        for d in scene.get("dialogue", []):
            yield f"{where} dialogue", str(d.get("text", ""))
            yield f"{where} action", str(d.get("action", ""))
        for n in scene.get("narration", []):
            yield f"{where} narration", str(n.get("text", ""))
    for j, sh in enumerate(pkg.get("shorts", []), 1):
        where = f"short {j}"
        yield f"{where} title", str(sh.get("title", ""))
        for d in sh.get("dialogue", []):
            yield f"{where} dialogue", str(d.get("text", ""))
    meta = pkg.get("metadata", {})
    for key in ("title", "description"):
        if isinstance(meta.get(key), str):
            yield f"metadata.{key}", meta[key]


def _check_recipe(pkg: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for i, scene in enumerate(pkg.get("scenes", []), 1):
        dialogue = scene.get("dialogue", [])
        n = len(dialogue)
        lo, hi = DIALOGUE_LINES_PER_SCENE
        if not (lo <= n <= hi):
            errors.append(f"scene {i}: {n} dialogue lines outside {lo}-{hi} (recipe: 5)")
        for d in dialogue:
            w = _words(str(d.get("text", "")))
            lo_w, hi_w = DIALOGUE_WORDS
            if not (lo_w <= w <= hi_w):
                errors.append(f"scene {i}: dialogue line {w} words outside {lo_w}-{hi_w}: {str(d.get('text',''))[:50]!r}")
        for nline in scene.get("narration", []):
            w = _words(str(nline.get("text", "")))
            lo_n, hi_n = NARRATION_WORDS
            if not (lo_n <= w <= hi_n):
                errors.append(f"scene {i}: narration {w} words outside {lo_n}-{hi_n}")
    return errors


def _check_repetition(pkg: dict[str, Any]) -> list[str]:
    # Repetition targets SPOKEN content (dialogue, narration, titles). Physical
    # stage directions (actions) repeat naturally in a puppet show — "nods" or
    # "leans forward" across scenes is expected, not an editorial fault — so
    # actions are excluded here (english-only still checks them for charset).
    counts: dict[str, int] = {}
    for where, text in _iter_text_fields(pkg):
        if where.endswith("action"):
            continue
        key = _norm(text)
        if len(key) < 12:  # short strings repeat legitimately
            continue
        counts[key] = counts.get(key, 0) + 1
    return [
        f"line repeated {c}x: {key[:60]!r}"
        for key, c in sorted(counts.items(), key=lambda kv: -kv[1])
        if c >= REPEAT_LIMIT
    ]


def _check_english_only(pkg: dict[str, Any]) -> list[str]:
    # Latin-1 + English typography allowed; anything else (Arabic, CJK,
    # Cyrillic, emoji, ...) violates the English-only rule (§7).
    return [
        f"non-English text in {where}: {text[:40]!r}"
        for where, text in _iter_text_fields(pkg)
        if _NON_ASCII.search(text)
    ]


def _check_speakers(pkg: dict[str, Any]) -> list[str]:
    speakers = {
        str(d.get("speaker", ""))
        for scene in pkg.get("scenes", [])
        for d in scene.get("dialogue", [])
        if str(d.get("speaker", ""))
    }
    if len(speakers) < 2:
        return [f"only {len(speakers)} distinct speaker(s) in long script: {sorted(speakers)}"]
    return []


def _check_hook(pkg: dict[str, Any]) -> list[str]:
    """Hook should surface early — warning only (editorial nudge)."""
    hook = str(pkg.get("hook", ""))
    keys = [w.lower() for w in re.findall(r"\w+", hook) if len(w) > 3][:6]
    if not keys:
        return []
    parts: list[str] = []
    for scene in pkg.get("scenes", [])[:2]:
        parts.extend(str(d.get("text", "")) for d in scene.get("dialogue", []))
        parts.extend(str(n.get("text", "")) for n in scene.get("narration", []))
    early = " ".join(parts).lower()
    if not any(k in early for k in keys):
        return ["hook wording not found in scenes 1-2"]
    return []


def _check_title_reuse(pkg: dict[str, Any], reg: Registry, episode_id: str) -> list[str]:
    title = str(pkg.get("title", "")).strip().lower()
    if not title:
        return []
    for other_id, entry in reg.episodes().items():
        if other_id == episode_id:
            continue
        if str(entry.get("title") or "").strip().lower() == title:
            return [f"title duplicates {other_id}: {pkg.get('title')!r}"]
    return []


def collect_script_errors(pkg: dict[str, Any], cfg: Config, reg: Registry,
                          episode_id: str) -> tuple[list[str], list[str]]:
    """Full (errors, warnings) set for a package: structural floor + editorial.

    Single source of truth shared by this gate and the generator's repair loop.
    """
    errors: list[str] = []
    errors.extend(validate_package(pkg, Universe(), cfg))
    errors.extend(_check_recipe(pkg))
    errors.extend(_check_repetition(pkg))
    errors.extend(_check_english_only(pkg))
    errors.extend(_check_speakers(pkg))
    errors.extend(_check_title_reuse(pkg, reg, episode_id))
    warnings = _check_hook(pkg)
    return errors, warnings


def _regenerate_and_recheck(cfg: Config, reg: Registry, episode_id: str,
                            ctx: dict[str, Any], pkg_file: Path,
                            errors: list[str], warnings: list[str],
                            ) -> tuple[list[str], list[str]]:
    """Repair path: regenerate the script once with the QC errors as feedback.

    On regeneration failure keep the original errors — QC must still report
    what was actually wrong with the package on disk.
    """
    ctx["script_regen"] = True
    log.warning("%s script QC found %d error(s) — regenerating with QC feedback: %s",
                episode_id, len(errors), errors[:5])
    try:
        from ..content.engine import run_generation

        ctx["force_regen"] = True
        run_generation(cfg, reg, episode_id, ctx)
    except Exception as exc:
        log.error("%s QC regeneration failed (%s) — keeping original QC errors",
                  episode_id, type(exc).__name__)
        return errors, warnings
    try:
        pkg = json.loads(pkg_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ["regenerated package.json unreadable"], warnings
    errors, warnings = collect_script_errors(pkg, cfg, reg, episode_id)
    if errors:
        log.warning("%s regenerated script still fails QC (%d error(s)): %s",
                    episode_id, len(errors), errors[:5])
    return errors, warnings


def check_script(cfg: Config, reg: Registry, episode_id: str, ctx: dict[str, Any]) -> None:
    """Stage SCRIPT_QC: PASS/FAIL gate; raises ScriptQCError on FAIL."""
    base = Path(cfg.get("paths.state", "state")) / "episodes" / episode_id
    pkg_file = base / "package.json"
    if not pkg_file.exists():
        raise ScriptQCError(f"package.json missing for {episode_id}")
    pkg = json.loads(pkg_file.read_text(encoding="utf-8"))
    errors, warnings = collect_script_errors(pkg, cfg, reg, episode_id)

    if errors and ctx.get("allow_regen") and not ctx.get("script_regen"):
        errors, warnings = _regenerate_and_recheck(
            cfg, reg, episode_id, ctx, pkg_file, errors, warnings)

    report = {
        "episode_id": episode_id,
        "checked_at": now_iso(),
        "status": "FAIL" if errors else "PASS",
        "estimate_sec": estimate_long_seconds(pkg),
        "errors": errors,
        "warnings": warnings,
    }
    qc_dir = base / "qc"
    qc_dir.mkdir(parents=True, exist_ok=True)
    (qc_dir / "script_qc.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    entry = reg.get(episode_id)
    entry["script_qc"] = {"status": report["status"], "at": report["checked_at"],
                          "warnings": len(warnings)}
    reg.save()

    if errors:
        shown = "; ".join(errors[:12])
        more = f" (+{len(errors) - 12} more)" if len(errors) > 12 else ""
        raise ScriptQCError(f"script QC failed with {len(errors)} error(s): {shown}{more}")
    log.info("%s script QC PASS (estimate %.0fs, %d warning(s))",
             episode_id, report["estimate_sec"], len(warnings))
    for w in warnings:
        log.warning("%s script QC warning: %s", episode_id, w)
