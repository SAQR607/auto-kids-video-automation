"""`python -m app doctor` — environment/configuration gate (§40).

PASS/FAIL/WARN table; exit code 1 on any FAIL. Network checks are opt-in via
--online so CI and offline dev can run the static subset.
"""

from __future__ import annotations

import importlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .config import ROOT, Config, ConfigError, env_str, groq_keys, load_config
from .logging_setup import get_logger

log = get_logger("doctor")

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"


@dataclass
class Check:
    name: str
    status: str
    detail: str

    @property
    def ok(self) -> bool:
        return self.status != FAIL


def _check_python() -> Check:
    v = sys.version_info
    ok = (v.major, v.minor) >= (3, 11)
    return Check("python", PASS if ok else FAIL, f"{v.major}.{v.minor}.{v.micro}" + ("" if ok else " (need >= 3.11)"))


def _check_ffmpeg() -> Check:
    exe = shutil.which("ffmpeg")
    if not exe:
        return Check("ffmpeg", FAIL, "not found on PATH (Windows: winget install Gyan.FFmpeg)")
    try:
        out = subprocess.run([exe, "-version"], capture_output=True, text=True, timeout=15)
        first = (out.stdout or "").splitlines()[0][:60]
        return Check("ffmpeg", PASS if out.returncode == 0 else FAIL, first or exe)
    except Exception as exc:
        return Check("ffmpeg", FAIL, str(exc))


def _check_ffprobe() -> Check:
    exe = shutil.which("ffprobe") or shutil.which("ffprobe.exe")
    if not exe:
        return Check("ffprobe", FAIL, "not found on PATH (ships with ffmpeg — video QC needs it)")
    return Check("ffprobe", PASS, exe)


def _check_module(mod: str, label: str, required: bool = True) -> Check:
    try:
        t0 = time.time()
        importlib.import_module(mod)
        return Check(label, PASS, f"import ok ({time.time() - t0:.1f}s)")
    except Exception as exc:
        status = FAIL if required else WARN
        return Check(label, status, f"import failed: {type(exc).__name__}: {exc}")


def _check_config() -> tuple[Check, Config | None]:
    try:
        cfg = load_config(allow_example=True)
    except ConfigError as exc:
        return Check("config", FAIL, str(exc).splitlines()[0]), None
    if cfg.path.name == "config.example.json":
        return Check("config", WARN, "using config.example.json — run `python -m app init` to create config/config.json"), cfg
    return Check("config", PASS, str(cfg.path.relative_to(ROOT))), cfg


def _check_state_dirs() -> Check:
    try:
        from .state import load_registry

        reg = load_registry(ROOT / "state")
        probe = ROOT / "state" / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        n = len(reg.episodes())
        return Check("state", PASS, f"state/ writable, {n} episode(s) registered")
    except Exception as exc:
        return Check("state", FAIL, str(exc))


def _placeholder(val: str | None) -> bool:
    return val is None or val.strip().upper().startswith("REPLACE")


def _check_groq(cfg: Config | None) -> Check:
    keys = [k for k in groq_keys() if not _placeholder(k)]
    if not keys:
        return Check("groq_keys", FAIL, "GROQ_API_KEYS empty or placeholder (set real key(s) in .env / GitHub Secrets)")
    detail = f"{len(keys)} key slot(s)"
    if len(keys) == 1:
        return Check("groq_keys", WARN, detail + " — failover needs 2+ keys")
    return Check("groq_keys", PASS, detail)


def _check_groq_online(cfg: Config | None) -> Check:
    keys = [k for k in groq_keys() if not _placeholder(k)]
    if not keys:
        return Check("groq_api", FAIL, "no real keys to test")
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/models",
        headers={"Authorization": f"Bearer {keys[0]}", "User-Agent": "python-requests/2.32.3"},
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
        n = len(data.get("data", []))
        model = (cfg.get("groq.model", "") if cfg else "")
        ids = {m.get("id") for m in data.get("data", [])}
        if model and model not in ids:
            return Check("groq_api", WARN, f"reachable ({n} models) but configured model '{model}' not listed")
        return Check("groq_api", PASS, f"reachable, slot0 valid, {n} models ({time.time() - t0:.1f}s)")
    except urllib.error.HTTPError as exc:
        return Check("groq_api", FAIL, f"HTTP {exc.code} from slot0")
    except Exception as exc:
        return Check("groq_api", FAIL, str(exc))


def _check_telegram(cfg: Config | None) -> Check:
    tok = env_str("TELEGRAM_BOT_TOKEN")
    chat = env_str("TELEGRAM_CHAT_ID")
    if _placeholder(tok) or _placeholder(chat):
        return Check("telegram", WARN, "not configured (TELEGRAM_BOT_TOKEN/CHAT_ID)")
    try:
        from . import telegram_client

        me = telegram_client.get_me()
        name = me.get("result", {}).get("username", "?")
        return Check("telegram", PASS, f"bot @{name} ok")
    except Exception as exc:
        return Check("telegram", FAIL, str(exc))


def _check_youtube(cfg: Config | None, online: bool) -> Check:
    need = ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"]
    missing = [k for k in need if _placeholder(env_str(k))]
    if missing:
        return Check("youtube", WARN, f"missing {', '.join(missing)} — run `python -m app youtube-oauth` (SETUP.md §4)")
    if not online:
        return Check("youtube", PASS, "credentials present (refresh not tested; use --online)")
    import urllib.parse

    body = urllib.parse.urlencode(
        {
            "client_id": env_str("YOUTUBE_CLIENT_ID"),
            "client_secret": env_str("YOUTUBE_CLIENT_SECRET"),
            "refresh_token": env_str("YOUTUBE_REFRESH_TOKEN"),
            "grant_type": "refresh_token",
        }
    ).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", data=body), timeout=20) as resp:
            data = json.loads(resp.read().decode())
        if data.get("access_token"):
            return Check("youtube", PASS, "token refresh ok")
        return Check("youtube", FAIL, "no access_token in refresh response")
    except urllib.error.HTTPError as exc:
        return Check("youtube", FAIL, f"refresh HTTP {exc.code}")
    except Exception as exc:
        return Check("youtube", FAIL, str(exc))


def _check_universe() -> Check:
    manifest = ROOT / "universe" / "manifest.json"
    if not manifest.exists():
        return Check("universe", WARN, "universe/manifest.json missing (created in Phase 3)")
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        return Check("universe", PASS, f"manifest ok: {len(data.get('characters', []))} characters, {len(data.get('locations', []))} locations")
    except Exception as exc:
        return Check("universe", FAIL, f"manifest unreadable: {exc}")


def run_doctor(online: bool = False) -> tuple[list[Check], Config | None]:
    checks: list[Check] = [_check_python(), _check_ffmpeg(), _check_ffprobe()]
    checks.append(_check_module("PIL", "pillow"))
    checks.append(_check_module("numpy", "numpy"))
    checks.append(_check_module("soundfile", "soundfile"))
    checks.append(_check_module("faster_whisper", "faster-whisper"))
    checks.append(_check_module("kokoro_onnx", "kokoro-onnx", required=False))
    checks.append(_check_module("onnxruntime", "onnxruntime", required=False))
    checks.append(_check_module("googleapiclient", "google-api"))

    cfg_check, cfg = _check_config()
    checks.append(cfg_check)
    checks.append(_check_state_dirs())
    checks.append(_check_groq(cfg))
    checks.append(_check_universe())
    if online:
        checks.append(_check_groq_online(cfg))
        checks.append(_check_telegram(cfg))
        checks.append(_check_youtube(cfg, online=True))
    else:
        checks.append(_check_youtube(cfg, online=False))
    return checks, cfg


def format_report(checks: list[Check]) -> str:
    width = max(len(c.name) for c in checks)
    lines = ["", "=== FERNWOOD DOCTOR ==="]
    for c in checks:
        mark = {PASS: "✓", WARN: "!", FAIL: "✗"}[c.status]
        lines.append(f" {mark} {c.status:<4} {c.name:<{width}}  {c.detail}")
    failed = [c for c in checks if c.status == FAIL]
    warned = [c for c in checks if c.status == WARN]
    lines.append("")
    if failed:
        lines.append(f"RESULT: FAIL — {len(failed)} failed, {len(warned)} warning(s)")
    elif warned:
        lines.append(f"RESULT: PASS with {len(warned)} warning(s)")
    else:
        lines.append("RESULT: PASS — all systems ready")
    return "\n".join(lines)


def main(online: bool = False) -> int:
    checks, _ = run_doctor(online=online)
    print(format_report(checks))
    return 1 if any(not c.ok for c in checks) else 0
