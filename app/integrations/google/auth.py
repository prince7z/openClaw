"""Core Google OAuth authentication workflows for Gmail and Calendar APIs."""

import logging
import shutil
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import httpx
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.integrations.google.config import (
    CALENDAR_SCOPES,
    CLIENT_SECRETS_PATH,
    GMAIL_LEGACY_CLIENT_SECRET,
    GMAIL_SCOPES,
    GOOGLE_CREDENTIALS_DIR,
    REDIRECT_URI,
)
from app.integrations.google.token_store import (
    load_credentials,
    load_metadata,
    save_credentials,
    save_metadata,
)

logger = logging.getLogger("openclaw-agent")


def resolve_client_secrets_path() -> Path:
    """Resolve and return the client_secret.json path, performing legacy migration if needed.

    Returns:
        The resolved Path object.
    """
    if CLIENT_SECRETS_PATH.exists():
        return CLIENT_SECRETS_PATH

    if GMAIL_LEGACY_CLIENT_SECRET.exists():
        try:
            GOOGLE_CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy(str(GMAIL_LEGACY_CLIENT_SECRET), str(CLIENT_SECRETS_PATH))
            logger.info("Successfully copied legacy Gmail client_secret.json to Google core credentials directory.")
            return CLIENT_SECRETS_PATH
        except Exception as exc:
            logger.warning(f"Failed to migrate legacy client_secret.json: {exc}")
            return GMAIL_LEGACY_CLIENT_SECRET

    return CLIENT_SECRETS_PATH


def is_connected(provider: str) -> bool:
    """Check if the target provider credentials are valid and active (auto-refreshing if expired).

    Args:
        provider: The provider name ('gmail', 'calendar').

    Returns:
        True if connected, else False.
    """
    creds = load_credentials(provider)
    if not creds:
        return False

    if creds.valid:
        return True

    if creds.expired and creds.refresh_token:
        try:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            save_credentials(provider, creds)
            return True
        except Exception as exc:
            logger.warning(f"Auto-refresh failed for provider '{provider}': {exc}")
            return False

    return False


def get_authorization_url(provider: str) -> str:
    """Generate consent screen authorization URL and cache the PKCE code_verifier.

    Args:
        provider: The provider name ('gmail', 'calendar').

    Returns:
        Consent screen authorization URL string.
    """
    secrets_path = resolve_client_secrets_path()
    if not secrets_path.exists():
        raise FileNotFoundError(f"Google OAuth client secrets file not found at: {secrets_path}")

    scopes = GMAIL_SCOPES if provider.lower() == "gmail" else CALENDAR_SCOPES

    flow = Flow.from_client_secrets_file(
        str(secrets_path),
        scopes=scopes
    )
    flow.redirect_uri = REDIRECT_URI

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent"
    )

    if hasattr(flow, "code_verifier") and flow.code_verifier:
        save_metadata(provider, {"code_verifier": flow.code_verifier})

    return auth_url


def complete_auth(provider: str, callback_url: str) -> None:
    """Exchange the authorization code for tokens, save them, and cache user email.

    Args:
        provider: The provider name ('gmail', 'calendar').
        callback_url: Redirect URL containing authorization parameters.
    """
    parsed = urlparse(callback_url)
    params = parse_qs(parsed.query)
    code = params.get("code", [None])[0]

    # Fallback if raw code string was supplied
    if not code:
        if not parsed.netloc and not parsed.path.startswith("http"):
            code = callback_url
        else:
            raise ValueError("No authorization code found in redirect callback URL query parameters.")

    secrets_path = resolve_client_secrets_path()
    scopes = GMAIL_SCOPES if provider.lower() == "gmail" else CALENDAR_SCOPES

    flow = Flow.from_client_secrets_file(
        str(secrets_path),
        scopes=scopes
    )
    flow.redirect_uri = REDIRECT_URI

    meta = load_metadata(provider)
    code_verifier = meta.get("code_verifier")
    if code_verifier:
        flow.code_verifier = code_verifier

    flow.fetch_token(code=code)

    creds = flow.credentials
    save_credentials(provider, creds)

    # Resolve and cache target email/profile
    try:
        if provider.lower() == "gmail":
            service = build("gmail", "v1", credentials=creds)
            profile = service.users().getProfile(userId="me").execute()
            email = profile.get("emailAddress")
        else:
            service = build("calendar", "v3", credentials=creds)
            cal = service.calendars().get(calendarId="primary").execute()
            email = cal.get("id")

        if email:
            save_metadata(provider, {"email": email})
    except Exception as exc:
        logger.warning(f"Failed to fetch profile email after OAuth token exchange: {exc}")


def revoke_token(token: str) -> None:
    """Revoke an active OAuth2 token with Google servers.

    Args:
        token: Access or refresh token to revoke.
    """
    try:
        res = httpx.post(
            "https://oauth2.googleapis.com/revoke",
            params={"token": token},
            headers={"content-type": "application/x-www-form-urlencoded"}
        )
        if res.status_code != 200:
            logger.warning(f"Failed to revoke Google OAuth token: {res.text}")
    except Exception as exc:
        logger.warning(f"Exception during Google OAuth token revocation: {exc}")
