"""Video assembly: raw frames -> per-scene H.264 -> concat -> mux audio.

ffmpeg is required (doctor checks). Frames are piped as rawvideo rgb24.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path

from .scene import render_frame

log = logging.getLogger("render")


def ffmpeg_bin() -> str:
    exe = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if not exe:
        raise RuntimeError("ffmpeg not found on PATH (run: python -m app doctor)")
    return exe


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
    for i, (scene, entry) in enumerate(zip(scenes, entries)):
        if consumed >= budget:
            break
        dur = float(entry["duration"])
        allow = min(dur, budget - consumed)
        n_frames = max(1, int(round(allow * fps)))
        part = out_dir / f"part_{i:02d}.mp4"
        log.info("render: scene %d/%d %.1fs (%d frames)", i + 1, len(scenes), allow, n_frames)
        proc = _spawn(part, w, h, fps)
        try:
            for f in range(n_frames):
                t = f / fps
                img = render_frame(
                    scene, t, dur, cfg, frame_w=w, frame_h=h, frame_no=f,
                    lines=entry.get("lines", []), scene_index=i,
                    scene_count=len(scenes),
                    package_title=package.get("title", ""),
                    episode_label=_episode_label(package, timing),
                )
                proc.stdin.write(img.tobytes())
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
        if thumb_dir is not None and i == 0:
            render_frame(scene, min(6.0, dur / 2), dur, cfg, frame_w=w, frame_h=h,
                         lines=entry.get("lines", []), scene_index=1,
                         scene_count=len(scenes) + 1).save(thumb_dir / "auto_scene.png")

    # concat
    concat_list = out_dir / "concat.txt"
    concat_list.write_text(
        "".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8"
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

    scene = _short_as_scene(short)
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


def _short_as_scene(short: dict) -> dict:
    return {
        "scene_id": short.get("short_id", "short"),
        "location": short.get("location", "hollow_oak_village"),
        "time_of_day": short.get("time_of_day", "day"),
        "camera": short.get("camera", "static"),
        "transition_in": "fade",
        "music_mood": short.get("music_mood", "happy"),
        "characters": [
            {"id": cid, "position": pos, "enter": "onscreen", "state": "idle"}
            for cid, pos in zip(short.get("characters", ["juni"]),
                                ("left", "right", "center")[: max(1, len(short.get("characters", [])))])
        ],
        "dialogue": short.get("dialogue", []),
        "narration": [],
        "props": short.get("props", []),
        "fx": short.get("fx", []),
    }


def _episode_label(package: dict, timing: dict) -> str:
    return "Fernwood Friends"
