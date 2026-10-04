"""YouTube OAuth2 credentials + API service factory (§47).

Credentials come from env/GitHub Secrets (YOUTUBE_CLIENT_ID/SECRET/
REFRESH_TOKEN); the one-time installed-app flow is `python -m app youtube-oauth`.
Scope includes readonly so the channel snapshot command works with the same
refresh token.
"""

from __future__ import annotations

from ..config import env_str
from ..logging_setup import get_logger

log = get_logger("youtube.oauth")

SCOPE = (
    "https://www.googleapis.com/auth/youtube.upload "
    "https://www.googleapis.com/auth/youtube.readonly"
)
TOKEN_URI = "https://oauth2.googleapis.com/token"
AUTH_URI = "https://accounts.google.com/o/oauth2/auth"

ENV_KEYS = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")


class YouTubeCredentialsError(RuntimeError):
    """Missing/placeholder YouTube credentials — user action required."""


def _placeholder(val: str | None) -> bool:
    return val is None or not val.strip() or val.strip().upper().startswith("REPLACE")


def require_env() -> tuple[str, str, str]:
    vals = {k: env_str(k) for k in ENV_KEYS}
    missing = [k for k, v in vals.items() if _placeholder(v)]
    if missing:
        raise YouTubeCredentialsError(
            f"missing {', '.join(missing)} — run `python -m app youtube-oauth` "
            "(see SETUP.md) or set them in GitHub Secrets"
        )
    return vals["YOUTUBE_CLIENT_ID"], vals["YOUTUBE_CLIENT_SECRET"], vals["YOUTUBE_REFRESH_TOKEN"]


def credentials():
    """Build google Credentials that refresh on demand (no network here)."""
    from google.oauth2.credentials import Credentials

    client_id, client_secret, refresh_token = require_env()
    return Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=TOKEN_URI,
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPE.split(),
    )


def build_service():
    """YouTube Data API v3 service (discovery cached off — CI has no cache dir)."""
    from googleapiclient.discovery import build

    require_env()
    return build("youtube", "v3", credentials=credentials(), cache_discovery=False)


def run_oauth_flow() -> str:
    """One-time installed-app consent flow; prints the refresh token.

    Requires YOUTUBE_CLIENT_ID/SECRET (OAuth Desktop client, YouTube Data API
    enabled — SETUP.md §4).
    """
    from google_auth_oauthlib.flow import InstalledAppFlow

    client_id, client_secret, _ = require_env()
    flow = InstalledAppFlow.from_client_config(
        {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": AUTH_URI,
                "token_uri": TOKEN_URI,
                "redirect_uris": ["http://localhost"],
            }
        },
        scopes=SCOPE.split(),
    )
    creds = flow.run_local_server(port=0, open_browser=True,
                                  access_type="offline", prompt="consent")
    if not creds.refresh_token:
        raise YouTubeCredentialsError(
            "Google returned no refresh_token — revoke prior grants at "
            "https://myaccount.google.com/permissions and run again with prompt=consent"
        )
    return creds.refresh_token
