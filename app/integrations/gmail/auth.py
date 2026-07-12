"""Gmail OAuth authentication wrapper delegating to Google Core."""

from app.integrations.google import auth as google_auth


def is_connected() -> bool:
    """Check if Gmail credentials exist and are active."""
    return google_auth.is_connected("gmail")


def get_authorization_url() -> str:
    """Generate the user authorization URL."""
    return google_auth.get_authorization_url("gmail")


def complete_auth(callback_url: str) -> None:
    """Exchange authorization code from callback redirect URL."""
    google_auth.complete_auth("gmail", callback_url)


def revoke_token(token: str) -> None:
    """Revoke user access token."""
    google_auth.revoke_token(token)


def get_user_email(service) -> str | None:
    """Fetch profile email address from Gmail API service.

    Args:
        service: The authenticated googleapiclient Gmail service.

    Returns:
        The email address string, or None if query fails.
    """
    try:
        profile = service.users().getProfile(userId="me").execute()
        return profile.get("emailAddress")
    except Exception:
        return None
