"""Benchmark orchestrator: golden reference → REAL stages → metrics → gates.

Isolation: everything runs under workspace/bench/ (own state root + registry);
production state/ is never read or written. Only existing dependencies are
used (numpy, Pillow, soundfile, ffmpeg, faster-whisper).

Exit codes: 0 pass (and a loud warning when no baseline exists yet),
1 regression vs baseline, 2 setup/stage failure.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from ..config import load_config
from ..logging_setup import get_logger
from . import REFERENCE_ID
from . import metrics_audio as ma
from . import metrics_video as mv
from .reference import PACKAGE, reference_texts, write_reference

log = get_logger("bench")

ROOT = Path(__file__).resolve().parent.parent.parent
BENCH_DIR = ROOT / "workspace" / "bench"
METRICS_PATH = BENCH_DIR / "metrics.json"
BASELINE_PATH = ROOT / "benchmarks" / "baseline.json"

STATE_REL = "workspace/bench/state"
WS_REL = "workspace/bench/workspace"

# Gate rules per metric:
#   rel_min/rel_max — multiplier applied to the baseline value (skipped when
#                     |baseline| is negligible, so near-zero metrics stay stable)
#   abs_min/abs_max — absolute bounds (standards like LUFS)
METRIC_SPECS: dict[str, dict[str, float]] = {
    "audio.lufs_integrated": {"abs_min": -19.0, "abs_max": -13.0},
    "audio.true_peak_db": {"abs_max": 0.0},
    "audio.speech_prominence_db": {"rel_min": 0.8, "abs_min": 3.0},
    "audio.duration_drift_sec": {"abs_max": 1.0},
    "audio.wer": {"rel_max": 1.5, "abs_max": 0.30},
    "audio.tts_rtf": {"rel_max": 1.5},
    "video.encode_psnr_db": {"rel_min": 0.97},
    "video.encode_ssim": {"rel_min": 0.99},
    "video.sharpness_laplacian": {"rel_min": 0.85},
    "video.colorfulness": {"rel_min": 0.90},
    "video.flicker_static_mae": {"rel_max": 2.0},
    "video.pan_frozen_pct": {"rel_max": 1.05},
    "video.pan_jitter_px": {"rel_max": 1.5},
    "video.thumbnail_sharpness": {"rel_min": 0.85},
    "perf.render_ms_per_frame": {"rel_max": 1.30},
    "perf.audio_wall_sec": {"rel_max": 1.35},
}

REL_EPS = 1e-6


def _ffmpeg() -> str:
    import shutil as _sh

    exe = _sh.which("ffmpeg") or _sh.which("ffmpeg.exe")
    if not exe:
        raise RuntimeError("ffmpeg not found on PATH")
    return exe


def _decode_frame(video: Path, ts: float, w: int, h: int) -> Any:
    """Decode the single frame covering timestamp ts as RGB ndarray."""
    import numpy as np

    out = subprocess.run(
        [_ffmpeg(), "-loglevel", "error", "-ss", f"{ts:.4f}", "-i", str(video),
         "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True, timeout=120,
    )
    if out.returncode != 0 or len(out.stdout) < w * h * 3:
        raise RuntimeError(f"frame decode failed at t={ts:.3f}: {out.stderr[-300:]!r}")
    return np.frombuffer(out.stdout[: w * h * 3], dtype=np.uint8).reshape(h, w, 3).copy()


def _decode_crop(video: Path, start: float, dur: float, crop: str, scale: str,
                 w: int, h: int) -> list[Any]:
    """Decode a time window cropped+scaled to raw frames."""
    import numpy as np

    proc = subprocess.run(
        [_ffmpeg(), "-loglevel", "error", "-ss", f"{start:.4f}", "-t", f"{dur:.4f}",
         "-i", str(video), "-vf", f"crop={crop},scale={scale}", "-f", "rawvideo",
         "-pix_fmt", "rgb24", "-"],
        capture_output=True, timeout=300,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"crop decode failed: {proc.stderr[-300:]!r}")
    sw, sh = (int(v) for v in scale.split(":"))
    frame_bytes = sw * sh * 3
    buf = proc.stdout
    n = len(buf) // frame_bytes
    frames = []
    for i in range(n):
        chunk = buf[i * frame_bytes:(i + 1) * frame_bytes]
        frames.append(np.frombuffer(chunk, dtype=np.uint8).reshape(sh, sw, 3).copy())
    return frames


def _scene_offsets(timing: dict[str, Any], fps: int) -> tuple[list[int], list[int]]:
    """(offset_frames, n_frames) per scene — mirrors video.py partitioning."""
    offsets: list[int] = []
    counts: list[int] = []
    off = 0
    for entry in timing.get("scenes", []):
        n = max(1, int(round(float(entry["duration"]) * fps)))
        offsets.append(off)
        counts.append(n)
        off += n
    return offsets, counts


def _run_stages(cfg: Any, reg: Any) -> tuple[dict[str, Any], Path, Path, float, float]:
    """Run the real audio + render stages; return timing/video/thumb/walls."""
    from ..audio.stages import build_audio
    from ..render.stages import render_long

    t0 = time.perf_counter()
    build_audio(cfg, reg, REFERENCE_ID, {})
    audio_wall = time.perf_counter() - t0

    t0 = time.perf_counter()
    render_long(cfg, reg, REFERENCE_ID, {})
    render_wall = time.perf_counter() - t0

    base = Path(STATE_REL) / "episodes" / REFERENCE_ID
    timing = json.loads((base / "audio" / "timing.json").read_text(encoding="utf-8"))
    entry = reg.get(REFERENCE_ID)
    video = Path(entry["video_path"])
    thumb = Path(entry["thumbnail_path"])
    return timing, video, thumb, audio_wall, render_wall


def _collect_audio_metrics(cfg: Any, timing: dict[str, Any], audio_wall: float,
                           skip_whisper: bool) -> dict[str, float]:
    import soundfile as sf

    base = Path(STATE_REL) / "episodes" / REFERENCE_ID
    master = base / "audio" / "master.wav"
    info = sf.info(str(master))
    wav_sec = info.frames / float(info.samplerate)

    m: dict[str, float] = {
        "perf.audio_wall_sec": round(audio_wall, 2),
        "audio.duration_drift_sec": round(abs(wav_sec - float(timing.get("total", 0))), 3),
    }
    loud = ma.loudness(master)
    if loud.get("lufs_integrated") is not None:
        m["audio.lufs_integrated"] = round(loud["lufs_integrated"], 2)
    if loud.get("true_peak_db") is not None:
        m["audio.true_peak_db"] = round(loud["true_peak_db"], 2)

    prom = ma.speech_prominence(master, timing)
    if prom is not None:
        m["audio.speech_prominence_db"] = round(prom, 2)

    texts = reference_texts()
    narrator = str(cfg.get("voices.narrator", "af_bella"))
    speed = float(cfg.get("tts.speed", 1.0))
    rtf = ma.tts_rtf(texts[:3], voice=narrator, speed=speed)
    m["audio.tts_rtf"] = rtf["rtf"]
    log.info("tts rtf: %s", rtf)

    if not skip_whisper:
        try:
            hyp = ma.transcribe(master, seconds=min(wav_sec, 180.0))
            ref_text = " ".join(texts)
            m["audio.wer"] = round(ma.wer(ref_text, hyp), 4)
            log.info("wer=%.3f hyp=%r", m["audio.wer"], hyp[:120])
        except Exception as exc:
            log.warning("whisper spot-check failed (metric omitted): %s", exc)
    return m


def _collect_video_metrics(cfg: Any, timing: dict[str, Any], video: Path, thumb: Path,
                           render_wall: float) -> dict[str, float]:
    import numpy as np

    from ..render.scene import render_frame
    from ..render.video import _episode_label

    r = cfg.get("render", {})
    w, h, fps = int(r.get("width", 1920)), int(r.get("height", 1080)), int(r.get("fps", 24))
    scenes = PACKAGE["scenes"]
    entries = timing["scenes"]
    offsets, counts = _scene_offsets(timing, fps)
    total_frames = offsets[-1] + counts[-1] if counts else 1

    m: dict[str, float] = {
        "perf.render_ms_per_frame": round(render_wall * 1000.0 / max(1, total_frames), 1),
    }
    label = _episode_label(cfg, PACKAGE, timing)

    # --- encode fidelity: regenerate source frames and compare to decoded
    psnrs: list[float] = []
    ssims: list[float] = []
    sharps: list[float] = []
    colorful: list[float] = []
    for idx, (off, n) in enumerate(zip(offsets, counts)):
        for frac in (0.3, 0.6, 0.9):
            f_local = max(1, min(n - 2, int(n * frac)))
            t_local = f_local / fps
            src = render_frame(
                scenes[idx], t_local, float(entries[idx]["duration"]), cfg,
                frame_w=w, frame_h=h, frame_no=f_local,
                lines=entries[idx].get("lines", []), scene_index=idx,
                scene_count=len(scenes), package_title=PACKAGE.get("title", ""),
                episode_label=label,
            )
            src_arr = np.asarray(src.convert("RGB"))
            t_global = (off + f_local) / fps + 0.5 / fps
            dec = _decode_frame(video, t_global, w, h)
            psnrs.append(mv.psnr(src_arr, dec))
            ssims.append(mv.ssim(src_arr, dec))
            gray = mv.to_gray(dec)
            sharps.append(mv.laplacian_var(gray))
            colorful.append(mv.colorfulness(dec))
    m["video.encode_psnr_db"] = round(float(np.mean(psnrs)), 2)
    m["video.encode_ssim"] = round(float(np.mean(ssims)), 4)
    m["video.sharpness_laplacian"] = round(float(np.mean(sharps)), 1)
    m["video.colorfulness"] = round(float(np.mean(colorful)), 2)

    # --- static-scene stability (top crop of sc_probe_static, excludes chars/fx)
    starts = [float(e.get("start", 0.0)) for e in entries]
    durs = [float(e.get("duration", 0.0)) for e in entries]
    flick_start = starts[0] + 1.5
    flick_dur = max(1.0, min(3.0, durs[0] - 2.0))
    static_frames = _decode_crop(video, flick_start, flick_dur,
                                 "1920:192:0:0", "480:48", w, h)
    m["video.flicker_static_mae"] = round(mv.flicker_mae(static_frames), 4)

    # --- pan motion continuity (top crop of sc_probe_pan)
    pan_idx = 1 if len(entries) > 1 else 0
    pan_start = starts[pan_idx] + 1.0
    pan_dur = max(1.0, min(6.0, durs[pan_idx] - 2.0))
    pan_frames = _decode_crop(video, pan_start, pan_dur,
                              "1920:320:0:0", "480:80", w, h)
    greys = [mv.to_gray(f) for f in pan_frames]
    pan = mv.pan_motion(greys, scale=w / 480.0)
    m["video.pan_frozen_pct"] = round(pan["frozen_pct"], 2)
    m["video.pan_jitter_px"] = round(pan["jitter_px"], 3)
    log.info("pan motion: %s", pan)

    # --- thumbnail quality
    if thumb.exists():
        arr = mv.load_png(thumb)
        m["video.thumbnail_sharpness"] = round(mv.laplacian_var(mv.to_gray(arr)), 1)
        m["video.thumbnail_colorfulness"] = round(mv.colorfulness(arr), 2)
    return m


def _gates(baseline: dict[str, Any], current: dict[str, float]) -> tuple[list[dict], int]:
    """Apply METRIC_SPECS against the baseline; returns (rows, fail_count)."""
    base_metrics: dict[str, float] = baseline.get("metrics", {})
    rows: list[dict] = []
    fails = 0
    for name in sorted(set(base_metrics) | set(current)):
        base = base_metrics.get(name)
        cur = current.get(name)
        spec = METRIC_SPECS.get(name, {})
        if cur is None:
            rows.append({"name": name, "base": base, "cur": None, "status": "FAIL",
                         "note": "metric missing from current run"})
            fails += 1
            continue
        if base is None:
            rows.append({"name": name, "base": None, "cur": cur, "status": "new",
                         "note": "not in baseline (re-baseline to gate)"})
            continue
        viol: list[str] = []
        if "rel_min" in spec and abs(base) > REL_EPS and cur < base * float(spec["rel_min"]):
            viol.append(f"< {spec['rel_min']}x baseline ({base * float(spec['rel_min']):.4g})")
        if "rel_max" in spec and abs(base) > REL_EPS and cur > base * float(spec["rel_max"]):
            viol.append(f"> {spec['rel_max']}x baseline ({base * float(spec['rel_max']):.4g})")
        if "abs_min" in spec and cur < float(spec["abs_min"]):
            viol.append(f"< abs_min {spec['abs_min']}")
        if "abs_max" in spec and cur > float(spec["abs_max"]):
            viol.append(f"> abs_max {spec['abs_max']}")
        rows.append({
            "name": name, "base": base, "cur": cur,
            "status": "FAIL" if viol else "pass", "note": "; ".join(viol),
        })
        if viol:
            fails += 1
    return rows, fails


def _print_report(rows: list[dict], fails: int) -> None:
    print("\n| metric | baseline | current | status | note |")
    print("|---|---:|---:|---|---|")
    for row in rows:
        base = "-" if row["base"] is None else f"{row['base']:.4g}"
        cur = "-" if row["cur"] is None else f"{row['cur']:.4g}"
        print(f"| {row['name']} | {base} | {cur} | {row['status']} | {row['note']} |")
    print(f"\n{len(rows)} metrics, {fails} failing gate(s)")


def run(*, update_baseline: bool, skip_whisper: bool, keep: bool) -> int:
    from ..state import load_registry

    if BENCH_DIR.exists() and not keep:
        shutil.rmtree(BENCH_DIR, ignore_errors=True)
    BENCH_DIR.mkdir(parents=True, exist_ok=True)

    cfg = load_config(allow_example=True)
    cfg.data.setdefault("paths", {})
    cfg.data["paths"]["state"] = STATE_REL
    cfg.data["paths"]["workspace"] = WS_REL

    write_reference(Path(STATE_REL))
    reg = load_registry(STATE_REL)
    reg.data["episodes"].setdefault(REFERENCE_ID, {
        "episode_id": REFERENCE_ID, "stage": "AUDIO_READY", "attempts": 0,
        "shorts": {}, "created_at": "bench", "updated_at": "bench",
    })
    reg.save()

    t_start = time.perf_counter()
    timing, video, thumb, audio_wall, render_wall = _run_stages(cfg, reg)
    log.info("stages done: audio %.1fs render %.1fs", audio_wall, render_wall)

    metrics: dict[str, float] = {}
    metrics.update(_collect_audio_metrics(cfg, timing, audio_wall, skip_whisper))
    metrics.update(_collect_video_metrics(cfg, timing, video, thumb, render_wall))

    payload = {
        "meta": {
            "git_sha": os.environ.get("GITHUB_SHA", "local"),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "wall_sec": round(time.perf_counter() - t_start, 1),
            "timing_total_sec": timing.get("total"),
        },
        "metrics": metrics,
    }
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"metrics written: {METRICS_PATH.relative_to(ROOT)}")

    if update_baseline:
        baseline = dict(payload)
        baseline["specs"] = METRIC_SPECS
        BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        BASELINE_PATH.write_text(json.dumps(baseline, indent=2, sort_keys=True),
                                 encoding="utf-8")
        print(f"baseline updated: {BASELINE_PATH.relative_to(ROOT)}")
        return 0

    if not BASELINE_PATH.exists():
        # First-ever run: warn loudly but don't fail the push; the workflow
        # dispatch with update_baseline=true establishes the gate immediately.
        print("NO BASELINE YET — dispatch `benchmark` with update_baseline=true "
              "to establish benchmarks/baseline.json (gates inactive until then)")
        return 0
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    rows, fails = _gates(baseline, metrics)
    _print_report(rows, fails)
    if fails:
        print("\nREGRESSION DETECTED — fix before proceeding (do not re-baseline failures)")
        return 1
    print("\nall gates passed")
    return 0
