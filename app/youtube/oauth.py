"""YouTube OAuth2 credentials + API service factory (§47).

Credentials come from env/GitHub Secrets (YOUTUBE_CLIENT_ID/SECRET/
REFRESH_TOKEN); the one-time installed-app flow is `python -m app youtube-oauth`.
One full `youtube` scope covers every call we make: videos.insert (upload),
videos.list (verify), videos.update (metadata refresh), channels.list
(snapshot), thumbnails.set. The upload+readonly pair was too narrow:
videos.update 403'd with insufficientPermissions on an upload-only grant.
Note: credentials() deliberately refreshes WITHOUT a scope param (Google
rejects refreshes whose scope differs from the grant).
"""

from __future__ import annotations

from ..config import env_str
from ..logging_setup import get_logger

log = get_logger("youtube.oauth")

SCOPE = "https://www.googleapis.com/auth/youtube"
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


def _client_env() -> tuple[str, str]:
    """Client id/secret for the consent flow.

    The refresh token is deliberately NOT required here — acquiring one is
    exactly what `youtube-oauth` does, so a fresh .env (placeholder refresh
    token) must not block the flow.
    """
    vals = {k: env_str(k) for k in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET")}
    missing = [k for k, v in vals.items() if _placeholder(v)]
    if missing:
        raise YouTubeCredentialsError(
            f"missing {', '.join(missing)} — set the OAuth Desktop client in .env (SETUP.md §4)"
        )
    return vals["YOUTUBE_CLIENT_ID"], vals["YOUTUBE_CLIENT_SECRET"]


def credentials():
    """Build google Credentials that refresh on demand (no network here).

    `scopes` is deliberately OMITTED: google-auth appends our scope list to
    the refresh POST (`scope=` param) and Google rejects the whole refresh
    with invalid_scope when the stored grant's scopes differ from that list
    — while the very same refresh token works fine WITHOUT the param (that
    is exactly what the doctor's online check does). The resulting access
    token carries whatever the grant authorized.
    """
    from google.oauth2.credentials import Credentials

    client_id, client_secret, refresh_token = require_env()
    return Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=TOKEN_URI,
        client_id=client_id,
        client_secret=client_secret,
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

    client_id, client_secret = _client_env()
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
