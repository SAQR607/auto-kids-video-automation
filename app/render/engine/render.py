"""Drive the engine-js page through the pinned Lemo render tools (node).

Contract (vendor/lemo-opuscar/core/render): the page must expose window.READY,
window.DUR and window.render(t); stills come back as JPEG, video is JPEG frames
piped to ffmpeg. engine-js/ lives outside the render server root, so the page is
mounted at /@film/ — nothing here depends on that, only on the <demo> folder path.

The scene plan travels percent-encoded in the ?plan= query (stateless, safe for
video.mjs's parallel workers); a plan-less run falls back to DEFAULT_PLAN.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEMO = ROOT / "engine-js"
_RENDER = ROOT / "vendor" / "lemo-opuscar" / "core" / "render"


def _query(plan: dict) -> str:
    return "plan=" + urllib.parse.quote(json.dumps(plan, separators=(",", ":")), safe="")


def _run(args: list[str]) -> None:
    node = shutil.which("node")
    if not node:
        raise RuntimeError("node is not on PATH (engine render needs Node >= 20)")
    proc = subprocess.run([node, *args], cwd=ROOT, capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError(
            f"engine render failed (exit {proc.returncode}):\n{proc.stdout}\n{proc.stderr}"
        )


def render_stills(
    plan: dict,
    times: list[float],
    out_dir: str | Path,
    size: tuple[int, int] = (1920, 1080),
) -> list[Path]:
    """Render one JPEG per time point: returns [<out_dir>/t_<t>.jpg, ...]."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamps = [str(t) for t in times]
    _run([
        str(_RENDER / "still.mjs"), str(DEMO), *stamps,
        "--q", _query(plan), "--out", str(out), "--size", f"{size[0]}x{size[1]}",
    ])
    return [out / f"t_{s}.jpg" for s in stamps]


def render_video(
    plan: dict,
    out_path: str | Path,
    fps: int = 24,
    workers: int = 3,
    size: tuple[int, int] = (1920, 1080),
) -> Path:
    """Render plan.duration seconds of video to out_path (ffmpeg required on PATH)."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    _run([
        str(_RENDER / "video.mjs"), str(DEMO),
        "--fps", str(fps), "--workers", str(workers),
        "--q", _query(plan), "--out", str(out), "--size", f"{size[0]}x{size[1]}",
    ])
    return out
