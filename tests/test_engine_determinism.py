"""Phase 1 exit gate: the same mini-plan rendered twice → identical frame hashes.

Skips when the Node engine stack is not installed (node, playwright-core, headless
shell), so the Fernwood-only suites stay green on machines without it.
"""

from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path

import pytest

from app.render.engine import render_stills, render_video

ROOT = Path(__file__).resolve().parents[1]


def _browser_installed() -> bool:
    base = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if base:
        root = Path(base)
    elif os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright"
    else:
        root = Path.home() / ".cache" / "ms-playwright"
    return root.is_dir() and any(root.glob("chromium_headless_shell-*"))


RENDERABLE = (
    bool(shutil.which("node"))
    and (ROOT / "node_modules" / "playwright-core").is_dir()
    and _browser_installed()
)
HAS_FFMPEG = bool(shutil.which("ffmpeg"))

skip_no_engine = pytest.mark.skipif(
    not RENDERABLE,
    reason="engine stack (node + playwright-core + chromium headless shell) not installed",
)

# Mini-plan fixture: two actors, walk → wave, x-move, seeded phases.
PLAN = {
    "seed": 11,
    "duration": 2.4,
    "stage": {"bg": "#F3F0EA", "ground": True, "ground_y": 0.82},
    "actors": [
        {"id": "a", "x": 0.3, "scale": 420,
         "beats": [{"t": 0, "pose": "walk"}, {"t": 1.0, "pose": "wave", "x": 0.42}]},
        {"id": "b", "x": 0.68, "scale": 380, "phase": 2.4,
         "beats": [{"t": 0, "pose": "idle"}]},
    ],
}
TIMES = [0, 0.7, 1.5, 2.4]


def _hashes(plan: dict, out: Path) -> dict[str, str]:
    files = render_stills(plan, TIMES, out)
    return {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


@skip_no_engine
def test_same_plan_twice_identical_frames(tmp_path: Path):
    first = _hashes(PLAN, tmp_path / "run1")
    second = _hashes(PLAN, tmp_path / "run2")
    assert first == second, "same mini-plan rendered twice must hash identically"
    # a static/blank canvas would pass the equality above — frames must also differ over time
    assert len(set(first.values())) == len(first), "frames at different times must differ"


@skip_no_engine
@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_video_render_smoke(tmp_path: Path):
    out = render_video(PLAN, tmp_path / "sample.mp4", fps=24, workers=2, size=(640, 360))
    assert out.is_file() and out.stat().st_size > 0
