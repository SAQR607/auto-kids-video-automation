"""Video assembly: raw frames -> per-scene H.264 -> concat -> mux audio.

ffmpeg is required (doctor checks). Frames are piped as rawvideo rgb24.

Frame rendering is parallelized across fork worker processes
(`_frame_pool`, RENDER_WORKERS): frames are pure functions of their
arguments, so workers produce byte-identical output while the main
process keeps the ordered ffmpeg pipe.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path

from .scene import render_frame

log = logging.getLogger("render")


def ffmpeg_bin() -> str:
    exe = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if not exe:
        raise RuntimeError("ffmpeg not found on PATH (run: python -m app doctor)")
    return exe


# --- parallel frame rendering ---------------------------------------------

def _render_workers() -> int:
    """Worker processes for frame rendering (RENDER_WORKERS overrides).

    Default cpu_count-1: the main process still drives the ffmpeg pipe and
    the encoder needs a core, so one stays free.
    """
    env = os.environ.get("RENDER_WORKERS")
    if env is not None and env.strip():
        try:
            return max(1, int(env))
        except ValueError:
            pass
    return max(1, (os.cpu_count() or 2) - 1)


def _warmup() -> int:
    """Touch task: forces the executor to fork a worker immediately."""
    return os.getpid()


# Per-process render diagnostics (each forked worker owns its own copy).
_WORKER_STATE: dict[str, int] = {"pid": 0, "frames": 0, "t0": 0}


def _affinity() -> str:
    try:
        return ",".join(str(c) for c in sorted(os.sched_getaffinity(0)))
    except (AttributeError, OSError):
        return "?"


def _render_frame_bytes(task: tuple) -> bytes:
    """Render one frame to raw rgb24 bytes (worker entry point).

    Must stay module-level with a plain-data argument tuple: workers
    receive it by pickle. Output is identical to the sequential loop.
    """
    st = _WORKER_STATE
    if st["pid"] == 0:  # first frame in this process
        st["pid"] = os.getpid()
        st["t0"] = time.perf_counter()
        log.info("render: frame worker active pid=%d affinity=%s",
                 st["pid"], _affinity())
    st["frames"] += 1
    if st["frames"] % 200 == 0:
        # cpu/wall ~= 1.0 => worker gets a full core; ~= 1/N => CPU-starved
        # (affinity/quota), i.e. workers time-share instead of running in parallel.
        log.info("render: frame worker pid=%d rendered %d frames "
                 "cpu=%.1fs wall=%.1fs",
                 st["pid"], st["frames"],
                 time.process_time(), time.perf_counter() - st["t0"])
    (scene, t, dur, cfg, w, h, frame_no, lines, scene_index,
     scene_count, title, label) = task
    img = render_frame(
        scene, t, dur, cfg, frame_w=w, frame_h=h, frame_no=frame_no,
        lines=lines, scene_index=scene_index, scene_count=scene_count,
        package_title=title, episode_label=label,
    )
    return img.tobytes()


def _ordered_parallel(fn, tasks, pool, window: int):
    """Ordered parallel map bounded to `window` in-flight futures.

    Executor.map() queues every task up front; raw frames are ~6 MB each,
    so an unbounded result buffer could reach GBs if the encoder lags.
    Yields results strictly in task order (the pipe needs frame order).
    """
    from collections import deque

    pending: deque = deque()
    for task in tasks:
        pending.append(pool.submit(fn, task))
        if len(pending) >= window:
            yield pending.popleft().result()
    while pending:
        yield pending.popleft().result()


def _frame_pool():
    """(pool, workers) for frame rendering; pool None => sequential.

    fork-only on purpose:
      * spawn platforms re-import __main__, and app/__main__.py raises
        SystemExit at import time (children would run main());
      * fork inherits test monkeypatches (fake render_frame) and is cheap.
    The pool must be created BEFORE any ffmpeg _spawn: workers forked
    afterwards inherit the encode pipe's stdin, hold it open, and ffmpeg
    never sees EOF -> proc.wait() deadlocks.
    """
    import multiprocessing as mp

    workers = _render_workers()
    if workers <= 1:
        return None, workers
    try:
        ctx = mp.get_context("fork")
    except ValueError:
        return None, workers  # no fork (Windows): sequential fallback
    from concurrent.futures import ProcessPoolExecutor

    return ProcessPoolExecutor(max_workers=workers, mp_context=ctx), workers


def _spawn(video_path: Path, w: int, h: int, fps: int) -> subprocess.Popen:
    cmd = [ffmpeg_bin(), "-y", "-loglevel", "error"]
    threads = os.environ.get("FFMPEG_THREADS")
    if threads:
        cmd += ["-threads", str(threads)]
    cmd += [
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps),
        "-i", "-",
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video_path),
    ]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)


def render_long_video(cfg: dict, episode_id: str, package: dict, timing: dict,
                      state_root: str | Path, sample_sec: float | None = None,
                      thumb_dir: Path | None = None) -> Path:
    r = cfg.get("render", {})
    w, h, fps = int(r.get("width", 1920)), int(r.get("height", 1080)), int(r.get("fps", 24))
    base = Path(state_root) / "episodes" / episode_id
    out_dir = base / "render"
    out_dir.mkdir(parents=True, exist_ok=True)
    scenes = package.get("scenes", [])
    entries = timing.get("scenes", [])
    total = float(timing.get("total", 0))
    budget = sample_sec if sample_sec else total

    parts: list[Path] = []
    consumed = 0.0
    label = _episode_label(cfg, package, timing)
    title = package.get("title", "")

    pool, workers = _frame_pool()
    if pool is not None:
        # Fork every worker NOW — before the first _spawn (see _frame_pool).
        for _ in range(workers):
            pool.submit(_warmup).result()
        log.info("render: frame pool up: workers=%d pids=%s cpus=%s affinity=%s "
                 "loadavg=%s", workers,
                 sorted(getattr(pool, "_processes", {}) or {}),
                 os.cpu_count(), _affinity(),
                 os.getloadavg() if hasattr(os, "getloadavg") else "?")
    else:
        log.info("render: frame pool off (workers=%d): sequential", workers)
    try:
        for i, (scene, entry) in enumerate(zip(scenes, entries)):
            if consumed >= budget:
                break
            dur = float(entry["duration"])
            allow = min(dur, budget - consumed)
            n_frames = max(1, int(round(allow * fps)))
            part = out_dir / f"part_{i:02d}.mp4"
            log.info("render: scene %d/%d %.1fs (%d frames)", i + 1, len(scenes), allow, n_frames)
            t_scene = time.perf_counter()
            proc = _spawn(part, w, h, fps)
            try:
                tasks = (
                    (scene, f / fps, dur, cfg, w, h, f, entry.get("lines", []),
                     i, len(scenes), title, label)
                    for f in range(n_frames)
                )
                if pool is not None:
                    frames = _ordered_parallel(_render_frame_bytes, tasks,
                                               pool, workers * 2)
                else:
                    frames = map(_render_frame_bytes, tasks)
                for data in frames:
                    proc.stdin.write(data)
                proc.stdin.close()
                ret = proc.wait()
                if ret != 0:
                    err = proc.stderr.read().decode(errors="replace")[-800:]
                    raise RuntimeError(f"ffmpeg scene encode failed: {err}")
            finally:
                if proc.poll() is None:
                    proc.kill()
            parts.append(part)
            consumed += allow
            wall = time.perf_counter() - t_scene
            log.info("render: scene %d done in %.1fs (%d frames, %.1f ms/f, "
                     "parent cpu %.1fs)",
                     i + 1, wall, n_frames, wall * 1000.0 / n_frames,
                     time.process_time())
            if thumb_dir is not None and i == 0:
                render_frame(scene, min(6.0, dur / 2), dur, cfg, frame_w=w, frame_h=h,
                             lines=entry.get("lines", []), scene_index=1,
                             scene_count=len(scenes) + 1).save(thumb_dir / "auto_scene.png")
    finally:
        if pool is not None:
            pool.shutdown(wait=True, cancel_futures=True)

    # concat — absolute paths: the concat demuxer resolves each file entry
    # relative to the LIST FILE's directory, so CWD-relative paths get doubled
    # (state/.../render/state/.../part_00.mp4) and the mux fails.
    concat_list = out_dir / "concat.txt"
    concat_list.write_text(
        "".join(f"file '{p.resolve().as_posix()}'\n" for p in parts), encoding="utf-8"
    )
    noaudio = out_dir / "video_noaudio.mp4"
    subprocess.run(
        [ffmpeg_bin(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(concat_list), "-c", "copy", str(noaudio)],
        check=True,
    )

    final = out_dir / "long.mp4"
    master = base / "audio" / "master.wav"
    cmd = [ffmpeg_bin(), "-y", "-loglevel", "error", "-i", str(noaudio)]
    if master.exists():
        cmd += ["-i", str(master), "-c:v", "copy", "-c:a", "aac", "-b:a",
                str(r.get("audio_bitrate", "192k")), "-shortest"]
    else:
        cmd += ["-c", "copy"]
    cmd += ["-movflags", "+faststart", str(final)]
    subprocess.run(cmd, check=True)
    log.info("render: long video -> %s", final)
    return final


def render_short_video(cfg: dict, episode_id: str, short: dict, short_timing: dict,
                       index: int, state_root: str | Path,
                       sample_sec: float | None = None) -> Path:
    r = cfg.get("render", {})
    w, h, fps = int(r.get("short_width", 1080)), int(r.get("short_height", 1920)), int(r.get("fps", 24))
    base = Path(state_root) / "episodes" / episode_id
    out_dir = base / "render"
    out_dir.mkdir(parents=True, exist_ok=True)
    dur = float(short_timing.get("duration", 30))
    if sample_sec:
        dur = min(dur, sample_sec)
    n_frames = max(1, int(round(dur * fps)))

    scene = _short_as_scene(short, cfg)
    part = out_dir / f"short_{index}_raw.mp4"
    log.info("render: short %d %.1fs (%d frames)", index, dur, n_frames)
    proc = _spawn(part, w, h, fps)
    try:
        for f in range(n_frames):
            img = render_frame(scene, f / fps, dur, cfg, frame_w=w, frame_h=h,
                               frame_no=f, lines=short_timing.get("lines", []),
                               scene_index=1, scene_count=99)
            proc.stdin.write(img.tobytes())
        proc.stdin.close()
        ret = proc.wait()
        if ret != 0:
            err = proc.stderr.read().decode(errors="replace")[-800:]
            raise RuntimeError(f"ffmpeg short encode failed: {err}")
    finally:
        if proc.poll() is None:
            proc.kill()

    final = out_dir / f"short_{index}.mp4"
    wav = base / "audio" / short_timing.get("file", f"short_{index}.wav")
    cmd = [ffmpeg_bin(), "-y", "-loglevel", "error", "-i", str(part)]
    if wav.exists():
        cmd += ["-i", str(wav), "-c:v", "copy", "-c:a", "aac", "-b:a",
                str(r.get("audio_bitrate", "192k")), "-shortest"]
    else:
        cmd += ["-c", "copy"]
    cmd += ["-movflags", "+faststart", str(final)]
    subprocess.run(cmd, check=True)
    part.unlink(missing_ok=True)
    return final


def _short_as_scene(short: dict, cfg: dict | None = None) -> dict:
    def _cget(key: str, default: str) -> str:
        try:
            return str(cfg.get(key, default)) if cfg is not None else default
        except Exception:
            return default

    return {
        "scene_id": short.get("short_id", "short"),
        "location": short.get("location") or _cget("channel.default_location", "hollow_oak_village"),
        "time_of_day": short.get("time_of_day", "day"),
        "camera": short.get("camera", "static"),
        "transition_in": "fade",
        "music_mood": short.get("music_mood", "happy"),
        "characters": [
            {"id": cid, "position": pos, "enter": "onscreen", "state": "idle"}
            for cid, pos in zip(short.get("characters") or [_cget("channel.default_character", "juni")],
                                ("left", "right", "center")[: max(1, len(short.get("characters", [])))] or ["center"])
        ],
        "dialogue": short.get("dialogue", []),
        "narration": [],
        "props": short.get("props", []),
        "fx": short.get("fx", []),
    }


def _episode_label(cfg: dict | None, package: dict, timing: dict) -> str:
    try:
        return str(cfg.get("channel.name", "Fernwood Friends")) if cfg is not None else "Fernwood Friends"
    except Exception:
        return "Fernwood Friends"
