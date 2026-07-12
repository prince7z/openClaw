"""Calendar token and metadata store wrapper delegating to Google Core."""

from google.oauth2.credentials import Credentials
from app.integrations.google import token_store as google_store


def load_credentials() -> Credentials | None:
    """Load user credentials from local store."""
    return google_store.load_credentials("calendar")


def save_credentials(credentials: Credentials) -> None:
    """Save user credentials to local store."""
    google_store.save_credentials("calendar", credentials)


def clear_credentials() -> None:
    """Remove local credentials from store."""
    google_store.clear_credentials("calendar")
    clear_metadata()


def save_metadata(data: dict) -> None:
    """Save connection metadata cache."""
    google_store.save_metadata("calendar", data)


def load_metadata() -> dict:
    """Load cached connection metadata."""
    return google_store.load_metadata("calendar")


def clear_metadata() -> None:
    """Remove local metadata cache."""
    google_store.clear_metadata("calendar")
