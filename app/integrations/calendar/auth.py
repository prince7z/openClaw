"""Calendar OAuth authentication wrapper delegating to Google Core."""

from app.integrations.google import auth as google_auth


def is_connected() -> bool:
    """Check if Calendar credentials exist and are active."""
    return google_auth.is_connected("calendar")


def get_authorization_url() -> str:
    """Generate the user authorization URL."""
    return google_auth.get_authorization_url("calendar")


def complete_auth(callback_url: str) -> None:
    """Exchange authorization code from callback redirect URL."""
    google_auth.complete_auth("calendar", callback_url)


def revoke_token(token: str) -> None:
    """Revoke user access token."""
    google_auth.revoke_token(token)
