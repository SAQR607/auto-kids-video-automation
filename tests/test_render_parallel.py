"""Parallel frame-render helpers (render/video.py).

Covers the worker-count contract, the fork-only pool policy, and the
bounded ordered map that keeps the ffmpeg pipe fed without unbounded
result buffering. The full loop (pool + fake render_frame via fork) is
exercised end-to-end by test_sample_flag.test_render_long_video_budget.
"""

from __future__ import annotations

import multiprocessing as mp

from app.render import video


def test_render_workers_env_override(monkeypatch):
    monkeypatch.setenv("RENDER_WORKERS", "2")
    assert video._render_workers() == 2
    monkeypatch.setenv("RENDER_WORKERS", "1")
    assert video._render_workers() == 1
    monkeypatch.setenv("RENDER_WORKERS", "0")  # clamped to sequential
    assert video._render_workers() == 1
    monkeypatch.setenv("RENDER_WORKERS", "junk")  # bad value -> default
    assert video._render_workers() >= 1
    monkeypatch.delenv("RENDER_WORKERS")
    assert video._render_workers() >= 1


def test_frame_pool_sequential_when_one_worker(monkeypatch):
    monkeypatch.setenv("RENDER_WORKERS", "1")
    pool, workers = video._frame_pool()
    assert pool is None
    assert workers == 1


def test_frame_pool_fork_policy():
    """Pool only where fork exists; sequential fallback elsewhere."""
    pool, workers = video._frame_pool()
    try:
        try:
            mp.get_context("fork")
            fork_ok = True
        except ValueError:
            fork_ok = False
        if fork_ok and video._render_workers() > 1:
            assert pool is not None
            assert workers >= 2
        else:
            assert pool is None
    finally:
        if pool is not None:
            pool.shutdown(wait=True)


def test_ordered_parallel_ordered_and_bounded():
    """Results in task order; at most `window` futures in flight."""
    state = {"inflight": 0, "max": 0}

    class _Fut:
        def __init__(self, value):
            self.value = value

        def result(self):
            state["inflight"] -= 1
            return self.value

    class _Pool:
        def submit(self, fn, task):
            state["inflight"] += 1
            state["max"] = max(state["max"], state["inflight"])
            return _Fut(fn(task))

    out = list(video._ordered_parallel(lambda x: x * 2, range(10), _Pool(),
                                       window=3))
    assert out == [x * 2 for x in range(10)]
    assert state["max"] <= 3


def test_ordered_parallel_propagates_task_errors():
    class _Fut:
        def __init__(self, value):
            self.value = value

        def result(self):
            if isinstance(self.value, Exception):
                raise self.value
            return self.value

    class _Pool:
        def submit(self, fn, task):
            return _Fut(fn(task))

    def boom(x):
        if x == 3:
            return ValueError("render failed")
        return x

    got = []
    try:
        for v in video._ordered_parallel(boom, range(6), _Pool(), window=2):
            got.append(v)
    except ValueError:
        pass
    else:
        raise AssertionError("task error must propagate")
    assert got == [0, 1, 2]


def test_warmup_returns_pid():
    assert video._warmup() == __import__("os").getpid()


def test_render_frame_bytes_roundtrip(monkeypatch):
    """_render_frame_bytes unpacks the task tuple and returns raw bytes."""
    seen = {}

    class _Img:
        def tobytes(self):
            return b"FRAME"

    def fake_render_frame(scene, t, dur, cfg, **kw):
        seen.update(scene=scene, t=t, dur=dur, cfg=cfg, **kw)
        return _Img()

    monkeypatch.setattr(video, "render_frame", fake_render_frame)
    task = ({"scene_id": "s"}, 1.5, 10.0, {"x": 1}, 64, 48, 36,
            ["line"], 2, 5, "Title", "Label")
    assert video._render_frame_bytes(task) == b"FRAME"
    assert seen["scene"] == {"scene_id": "s"}
    assert seen["t"] == 1.5
    assert seen["frame_no"] == 36
    assert seen["frame_w"] == 64 and seen["frame_h"] == 48
    assert seen["lines"] == ["line"]
    assert seen["scene_index"] == 2 and seen["scene_count"] == 5
    assert seen["package_title"] == "Title"
    assert seen["episode_label"] == "Label"
