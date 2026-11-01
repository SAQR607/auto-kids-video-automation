"""TikTok OAuth v2: consent flow + access-token refresh (docs/TIKTOK.md).

Tokens: access_token 24h, refresh_token 365d and ROTATED on every refresh —
the new refresh_token must be persisted or the next refresh fails with
invalid_grant. We always write the latest bundle to
state/secrets/tiktok_tokens.json (gitignored); in CI the workflow copies
rotated values back into repo secrets via TIKTOK_ROTATE_PAT when set.
Env bootstrap: TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET /
TIKTOK_ACCESS_TOKEN (optional) / TIKTOK_REFRESH_TOKEN.
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any

from ..config import ROOT, env_str
from ..logging_setup import get_logger, redact

log = get_logger("tiktok.oauth")

SCOPE = "video.upload"
AUTH_URI = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URI = "https://open.tiktokapis.com/v2/oauth/token/"
# Fixed loopback port: register http://localhost:8766/ as the app redirect URI.
LOCAL_PORT = 8766


class TikTokCredentialsError(RuntimeError):
    """Missing/invalid TikTok credentials — user action required."""


def _placeholder(val: str | None) -> bool:
    return val is None or not val.strip() or val.strip().upper().startswith("REPLACE")


def client_env() -> tuple[str, str]:
    key, secret = env_str("TIKTOK_CLIENT_KEY"), env_str("TIKTOK_CLIENT_SECRET")
    if _placeholder(key) or _placeholder(secret):
        raise TikTokCredentialsError(
            "TIKTOK_CLIENT_KEY/SECRET not set — create an app at "
            "developers.tiktok.com (Content Posting API) and fill .env (docs/TIKTOK.md)"
        )
    return str(key), str(secret)


def available() -> bool:
    """True when the app credentials exist (tokens are refreshed on demand)."""
    try:
        client_env()
        return True
    except TikTokCredentialsError:
        return False


def tokens_path(state_dir: str | Path | None = None) -> Path:
    return Path(state_dir or ROOT / "state") / "secrets" / "tiktok_tokens.json"


def _post_form(url: str, fields: dict[str, str], *, timeout: int = 30) -> dict[str, Any]:
    data = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "Cache-Control": "no-cache"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        snippet = ""
        try:
            snippet = exc.read().decode("utf-8", "replace")[:300]
        except Exception:
            pass
        raise TikTokCredentialsError(f"tiktok token HTTP {exc.code}: {redact(snippet)}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise TikTokCredentialsError(f"tiktok token network error: {redact(str(exc))}") from exc
    if body.get("error"):
        desc = body.get("error_description") or ""
        raise TikTokCredentialsError(f"tiktok token error {body['error']}: {redact(desc)[:200]}")
    return body


def _load_bundle(state_dir: str | Path | None = None) -> dict[str, str]:
    """Latest known tokens: local rotation file wins over env bootstrap."""
    bundle = {
        "access_token": env_str("TIKTOK_ACCESS_TOKEN") or "",
        "refresh_token": env_str("TIKTOK_REFRESH_TOKEN") or "",
    }
    path = tokens_path(state_dir)
    if path.exists():
        try:
            disk = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            log.warning("bad token file %s: %s", path, redact(str(exc)))
            disk = {}
        for k in ("access_token", "refresh_token"):
            if disk.get(k):
                bundle[k] = str(disk[k])
    return bundle


def save_local_tokens(bundle: dict[str, Any], state_dir: str | Path | None = None) -> Path:
    path = tokens_path(state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    slim = {k: bundle.get(k, "") for k in ("access_token", "refresh_token", "open_id", "scope")}
    slim["obtained_at"] = int(time.time())
    path.write_text(json.dumps(slim, indent=2), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    log.info("tiktok tokens persisted to %s (gitignored)", path)
    return path


def refresh_access(state_dir: str | Path | None = None) -> dict[str, str]:
    """Refresh with the stored refresh_token; persists the rotated bundle."""
    key, secret = client_env()
    bundle = _load_bundle(state_dir)
    if not bundle["refresh_token"] or _placeholder(bundle["refresh_token"]):
        raise TikTokCredentialsError(
            "TIKTOK_REFRESH_TOKEN not set — run `python -m app tiktok-auth` (docs/TIKTOK.md)"
        )
    body = _post_form(TOKEN_URI, {
        "client_key": key,
        "client_secret": secret,
        "grant_type": "refresh_token",
        "refresh_token": bundle["refresh_token"],
    })
    if not body.get("access_token"):
        raise TikTokCredentialsError(f"tiktok refresh returned no access_token: {redact(str(body))[:200]}")
    new_bundle = {
        "access_token": str(body["access_token"]),
        "refresh_token": str(body.get("refresh_token") or bundle["refresh_token"]),
        "open_id": str(body.get("open_id") or ""),
        "scope": str(body.get("scope") or ""),
    }
    save_local_tokens(new_bundle, state_dir)
    return new_bundle


def ensure_access_token(state_dir: str | Path | None = None) -> str:
    """Fresh-enough access token for API calls (always refreshes — 24h TTL)."""
    return refresh_access(state_dir)["access_token"]


def _pkce_pair() -> tuple[str, str]:
    """PKCE (RFC 7636, S256) — TikTok rejects authorize URLs without a challenge."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def exchange_code(code: str, state_dir: str | Path | None = None,
                  *, code_verifier: str | None = None) -> dict[str, str]:
    key, secret = client_env()
    fields = {
        "client_key": key,
        "client_secret": secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": f"http://localhost:{LOCAL_PORT}/",
    }
    if code_verifier:
        fields["code_verifier"] = code_verifier
    body = _post_form(TOKEN_URI, fields)
    if not body.get("access_token"):
        raise TikTokCredentialsError(f"tiktok code exchange failed: {redact(str(body))[:200]}")
    bundle = {
        "access_token": str(body["access_token"]),
        "refresh_token": str(body.get("refresh_token") or ""),
        "open_id": str(body.get("open_id") or ""),
        "scope": str(body.get("scope") or ""),
    }
    save_local_tokens(bundle, state_dir)
    return bundle


def run_oauth_flow(state_dir: str | Path | None = None) -> dict[str, str]:
    """One-time consent flow; waits for the localhost redirect, exchanges the code."""
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from urllib.parse import parse_qs, urlparse

    key, _secret = client_env()
    verifier, challenge = _pkce_pair()
    authorize = (
        f"{AUTH_URI}?client_key={urllib.parse.quote(key)}"
        f"&scope={urllib.parse.quote(SCOPE)}"
        "&response_type=code"
        f"&code_challenge={urllib.parse.quote(challenge)}"
        "&code_challenge_method=S256"
        f"&redirect_uri={urllib.parse.quote(f'http://localhost:{LOCAL_PORT}/')}"
    )
    captured: dict[str, str] = {}

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 (stdlib signature)
            qs = parse_qs(urlparse(self.path).query)
            if "code" in qs:
                captured["code"] = qs["code"][0]
                msg = b"TikTok connected. You can close this tab."
                self.send_response(200)
            elif "error" in qs:
                captured["error"] = qs.get("error", ["unknown"])[0]
                msg = f"TikTok authorization failed: {captured['error']}".encode()
                self.send_response(400)
            else:
                msg = b"unexpected callback"
                self.send_response(400)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

        def log_message(self, *_args):  # silence request logging
            pass

    server = HTTPServer(("127.0.0.1", LOCAL_PORT), _Handler)
    server.timeout = 300
    log.info("tiktok consent: listening on http://localhost:%d/ for up to 5 min", LOCAL_PORT)
    webbrowser.open(authorize)
    print(f"Open this URL if the browser did not:\n{authorize}\n")
    deadline = time.time() + 300
    while time.time() < deadline and "code" not in captured and "error" not in captured:
        server.handle_request()
    server.server_close()
    if "error" in captured:
        raise TikTokCredentialsError(f"authorization denied: {captured['error']}")
    if "code" not in captured:
        raise TikTokCredentialsError("timed out waiting for the TikTok consent redirect")
    return exchange_code(captured["code"], state_dir, code_verifier=verifier)
