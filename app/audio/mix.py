"""Audio stage: TTS per line, music bed, SFX, scene tracks, master timeline.

Outputs under state/episodes/<id>/audio/:
  scene_XX.wav (44.1k stereo), master.wav, timing.json
Shorts: short_N.wav (+ entries in timing.json).
timing.json is the contract for the video renderer.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

import numpy as np
import soundfile as sf

from . import music, sfx, tts

log = logging.getLogger("audio")

# Music ducking under speech (sidechain-style, driven by line marks):
# how far the bed drops while a line is active and how fast it recovers.
DUCK_ATTACK_SEC = 0.12
DUCK_RELEASE_SEC = 0.40
DUCK_LEAD_SEC = 0.10   # start dipping just before the first sample
DUCK_TAIL_SEC = 0.30   # hold the dip past the last sample


def _g(db: float) -> float:
    return float(10 ** (db / 20.0))


def _fade(x: np.ndarray, fade_in: float, fade_out: float, sr: int) -> np.ndarray:
    n = x.shape[0]
    fi = min(int(fade_in * sr), n // 2)
    fo = min(int(fade_out * sr), n // 2)
    if fi > 0:
        ramp = np.linspace(0, 1, fi, dtype=np.float32)[:, None]
        x[:fi] *= ramp
    if fo > 0:
        ramp = np.linspace(1, 0, fo, dtype=np.float32)[:, None]
        x[n - fo:] *= ramp
    return x


def _add(track: np.ndarray, clip: np.ndarray, start_s: float, gain: float, sr: int) -> None:
    s = int(start_s * sr)
    if s < 0:
        clip = clip[-s:]
        s = 0
    e = min(s + clip.shape[0], track.shape[0])
    if e <= s:
        return
    track[s:e] += clip[: e - s] * gain


def _mono2stereo(y: np.ndarray) -> np.ndarray:
    if y.ndim == 2:
        return y
    return np.stack([y, y], axis=1).astype(np.float32)


def _voices(cfg: dict) -> tuple[dict[str, str], str]:
    v = {k.lower(): val for k, val in (cfg.get("voices") or {}).items()}
    narrator = v.get("narrator", "af_bella")
    return v, narrator


def _line_voice(voices: dict[str, str], narrator: str, speaker: str) -> str:
    return voices.get((speaker or "").lower(), narrator)


def _scene_speech(scene: dict, voices: dict[str, str], narrator: str,
                  cache_dir: Path, speed: float) -> tuple[np.ndarray, float, int, list[dict]]:
    """Synthesize all lines of a scene -> (track@24k mono, end_time, sr, line_marks)."""
    items: list[tuple[str, str, str]] = []
    for d in scene.get("dialogue", []):
        items.append((d.get("speaker", ""), d.get("text", ""), _line_voice(voices, narrator, d.get("speaker", ""))))
    for nline in scene.get("narration", []):
        items.append(("narrator", nline.get("text", ""), narrator))

    pieces: list[tuple[np.ndarray, float]] = []
    marks: list[dict] = []
    t = 0.5
    for i, (speaker, text, voice) in enumerate(items):
        if not text:
            continue
        samples, sr = tts.synth(text, voice=voice, speed=speed, cache_dir=cache_dir)
        dur = samples.shape[0] / sr
        pieces.append((samples, t))
        marks.append({"speaker": speaker, "start": round(t, 3),
                      "end": round(t + dur, 3), "emotion": _line_emotion(scene, i, speaker)})
        is_narration = speaker == "narrator"
        gap = 0.6 if is_narration else 0.42
        t += dur + gap
    end = t + 0.6
    track = np.zeros(int(end * 24000), dtype=np.float32)
    for samples, at in pieces:
        s = int(at * 24000)
        e = min(s + samples.shape[0], track.shape[0])
        track[s:e] += samples[: e - s]
    return track, end, 24000, marks


def _line_emotion(scene: dict, index: int, speaker: str) -> str:
    if speaker == "narrator":
        return "neutral"
    dialogue = scene.get("dialogue", [])
    if index < len(dialogue):
        return dialogue[index].get("emotion") or "neutral"
    return "neutral"


def _scene_sfx(scene: dict, sr: int) -> list[tuple[str, float, float]]:
    """(sfx name, at_seconds, gain_mult) events for a scene."""
    dur_est = 20.0
    events: list[tuple[str, float, float]] = []
    for fx in scene.get("fx", []) or []:
        if fx == "glimmer_sparkle":
            events.append(("chime", dur_est * 0.2, 0.7))
            events.append(("sparkle", dur_est * 0.55, 0.5))
        elif fx == "speech_pop":
            events.append(("pop", 0.4, 0.8))
        elif fx == "leaf_swirl":
            events.append(("whoosh", 0.3, 0.7))
        elif fx == "rain_streak":
            events.append(("rain", 0.0, 0.35))
        elif fx == "ripple_ring":
            events.append(("sparkle", 0.6, 0.6))
        elif fx == "endcard_wave":
            events.append(("bell", dur_est * 0.7, 0.6))
    return events


def _duck_envelope(n: int, marks: list[dict], sr: int, depth_db: float) -> np.ndarray:
    """Music-bed gain envelope that ducks to `depth_db` around each line.

    Built from the scene's line marks (exact TTS timings) rather than an
    audio sidechain detector: deterministic, no detector lag, and the dip
    always aligns with the words. Overlapping lines merge (elementwise
    min keeps the deepest dip).
    """
    env = np.ones(n, dtype=np.float32)
    if depth_db >= 0.0 or not marks:
        return env
    depth = _g(depth_db)
    for m in marks:
        a = int((float(m["start"]) - DUCK_LEAD_SEC) * sr)
        b = int((float(m["end"]) + DUCK_TAIL_SEC) * sr)
        a, b = max(0, a), min(n, b)
        if b <= a:
            continue
        seg = np.full(b - a, depth, dtype=np.float32)
        att = min(int(DUCK_ATTACK_SEC * sr), seg.shape[0])
        if att > 0:
            seg[:att] = np.linspace(1.0, depth, att, dtype=np.float32)
        rel = min(int(DUCK_RELEASE_SEC * sr), seg.shape[0] - att)
        if rel > 0:
            seg[-rel:] = np.linspace(depth, 1.0, rel, dtype=np.float32)
        env[a:b] = np.minimum(env[a:b], seg)
    return env


def _normalize_loudness(path: Path) -> None:
    """2-pass loudnorm a written wav in place (atomic); skip w/o ffmpeg."""
    if not (shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")):
        log.warning("audio: ffmpeg missing — %s left un-normalized", path.name)
        return
    from . import loudnorm

    m = loudnorm.normalize(path, path)
    log.info("audio: loudnorm %s measured %.1f LUFS (TP %.1f) -> target %.1f",
             path.name, m.get("lufs_integrated") or float("nan"),
             m.get("true_peak_db") or float("nan"), loudnorm.TARGET_I)


def _render_scene(scene: dict, idx: int, cfg: dict, voices: dict[str, str],
                  narrator: str, cache_dir: Path, speed: float) -> tuple[np.ndarray, int, float, list[dict]]:
    sr = int(cfg.get("render", {}).get("sample_rate", 44100))
    speech24, end24, _, marks = _scene_speech(scene, voices, narrator, cache_dir, speed)
    speech = tts.resample(speech24, 24000, sr)
    scene_len = max(end24, 4.0)
    n = int(scene_len * sr)
    track = np.zeros((n, 2), dtype=np.float32)

    # speech (centered; kokoro is already level-consistent scene to scene
    # — a measured RMS leveler here only fought the peak cap)
    sp = _mono2stereo(speech)
    m = min(sp.shape[0], n)
    track[:m] += sp[:m] * 0.95

    # music bed — ducked under speech (line marks give exact timings)
    mc = cfg.get("music", {})
    if mc.get("enabled", True):
        mood = scene.get("music_mood", "happy")
        bed = music.render_bed(mood, scene_len + 0.3, sr)
        bed = _fade(bed, 0.35, 0.45, sr)
        gain = _g(float(mc.get("bed_gain_db", -24.0)))
        mm = min(bed.shape[0], n)
        env = _duck_envelope(mm, marks, sr, float(mc.get("duck_db", -8.0)))
        track[:mm] += bed[:mm] * env[:, None] * gain

    # sfx
    sfx_gain = _g(float(mc.get("sfx_gain_db", -10.0)))
    for name, at, mult in _scene_sfx(scene, sr):
        if name == "rain" and at == 0.0:
            clip = sfx.render("rain", sr=sr)
            clip = _fade(_mono2stereo(clip), 0.5, 0.5, sr)
            _add(track, clip, 0.0, sfx_gain * 0.5 * mult, sr)
        else:
            clip = _mono2stereo(sfx.render(name, seed=idx + 3, sr=sr))
            _add(track, clip, at, sfx_gain * mult, sr)

    # transition whoosh at scene start (skip very first)
    if idx > 0:
        clip = _mono2stereo(sfx.render("whoosh", sr=sr))
        _add(track, clip, -0.12, sfx_gain * 0.55, sr)

    return track, sr, scene_len, marks


def build_long_audio(cfg: dict, episode_id: str, package: dict,
                     state_root: str | Path, limit_scenes: int | None = None) -> dict:
    out_dir = Path(state_root) / "episodes" / episode_id / "audio"
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = Path(state_root) / "cache" / "tts"
    voices, narrator = _voices(cfg)
    speed = float(cfg.get("tts", {}).get("speed", 1.0))

    scenes = package.get("scenes", [])
    if limit_scenes:
        scenes = scenes[:limit_scenes]

    master_parts: list[np.ndarray] = []
    entries = []
    cursor = 0.0
    sr_out = int(cfg.get("render", {}).get("sample_rate", 44100))

    for i, scene in enumerate(scenes):
        log.info("audio: scene %d/%d (%s)", i + 1, len(scenes), scene.get("scene_id"))
        track, sr, scene_len, marks = _render_scene(scene, i, cfg, voices, narrator, cache_dir, speed)
        assert sr == sr_out
        fname = f"scene_{i + 1:02d}.wav"
        sf.write(out_dir / fname, np.clip(track, -1.0, 1.0), sr, subtype="PCM_16")
        entries.append({"scene_id": scene.get("scene_id"), "file": fname,
                        "start": round(cursor, 3), "duration": round(scene_len, 3),
                        "end": round(cursor + scene_len, 3), "lines": marks})
        master_parts.append(track)
        cursor += scene_len

    if master_parts:
        master = np.concatenate(master_parts, axis=0)
        master_path = out_dir / "master.wav"
        sf.write(master_path, np.clip(master, -1.0, 1.0), sr_out, subtype="PCM_16")
        _normalize_loudness(master_path)
    timing = {"kind": "long", "episode_id": episode_id, "sample_rate": sr_out,
              "fps": int(cfg.get("render", {}).get("fps", 24)),
              "total": round(cursor, 3), "scenes": entries}
    (out_dir / "timing.json").write_text(json.dumps(timing, indent=2), encoding="utf-8")
    log.info("audio: long master %.1fs -> %s", cursor, out_dir)
    return timing


_SHORT_MOOD_FALLBACK = "happy"


def build_short_audio(cfg: dict, episode_id: str, short: dict, index: int,
                      state_root: str | Path) -> dict:
    out_dir = Path(state_root) / "episodes" / episode_id / "audio"
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = Path(state_root) / "cache" / "tts"
    voices, narrator = _voices(cfg)
    speed = float(cfg.get("tts", {}).get("speed", 1.0))
    sr = int(cfg.get("render", {}).get("sample_rate", 44100))

    scene = dict(short)
    scene.setdefault("fx", ["sparkle"] if short.get("kind") in ("wonder", "funny") else [])
    scene["music_mood"] = {"funny": "playful", "wonder": "wonder"}.get(short.get("kind", ""), _SHORT_MOOD_FALLBACK)
    track, _, scene_len, marks = _render_scene(scene, 0, cfg, voices, narrator, cache_dir, speed)

    # hold: shorts must land in 25-45s — extend with music tail + end sfx if short
    target_min = float(cfg.get("duration", {}).get("short_min_sec", 25)) + 0.8
    if scene_len < target_min:
        extra = target_min - scene_len
        n_extra = int(extra * sr)
        tail = np.zeros((n_extra, 2), dtype=np.float32)
        mc = cfg.get("music", {})
        if mc.get("enabled", True):
            bed = _fade(music.render_bed(scene["music_mood"], extra + 0.3, sr), 0.3, 0.5, sr)
            mm = min(bed.shape[0], n_extra)
            tail[:mm] += bed[:mm] * _g(float(mc.get("bed_gain_db", -24.0)))
        track = np.concatenate([track, tail], axis=0)
        scene_len = track.shape[0] / sr

    # short: upbeat start whoosh + end pop/bell
    sfx_gain = _g(float(cfg.get("music", {}).get("sfx_gain_db", -10.0)))
    _add(track, _mono2stereo(sfx.render("whoosh", sr=sr)), -0.05, sfx_gain * 0.5, sr)
    _add(track, _mono2stereo(sfx.render("bell", sr=sr)), scene_len - 1.1, sfx_gain * 0.5, sr)
    _add(track, _mono2stereo(sfx.render("pop", sr=sr)), scene_len - 0.4, sfx_gain * 0.6, sr)

    fname = f"short_{index}.wav"
    sf.write(out_dir / fname, np.clip(track, -1.0, 1.0), sr, subtype="PCM_16")
    _normalize_loudness(out_dir / fname)
    return {"short_id": short.get("short_id"), "file": fname,
            "start": 0.0, "duration": round(scene_len, 3), "end": round(scene_len, 3),
            "kind": short.get("kind"), "lines": marks}
