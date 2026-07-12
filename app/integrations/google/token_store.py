"""Shared credentials and metadata manager for Google APIs."""

import json
import logging
from pathlib import Path
from google.oauth2.credentials import Credentials

from app.integrations.google.config import GOOGLE_CREDENTIALS_DIR, GMAIL_LEGACY_DIR

logger = logging.getLogger("openclaw-agent")


def _get_token_path(provider: str) -> Path:
    return GOOGLE_CREDENTIALS_DIR / f"{provider.lower()}_token.json"


def _get_metadata_path(provider: str) -> Path:
    return GOOGLE_CREDENTIALS_DIR / f"{provider.lower()}_metadata.json"


def load_credentials(provider: str) -> Credentials | None:
    """Load OAuth2 credentials from file, performing migrations for legacy Gmail paths.

    Args:
        provider: The provider name (e.g. 'gmail', 'calendar').

    Returns:
        Google Credentials object if available and parsed, else None.
    """
    path = _get_token_path(provider)

    # Legacy Gmail credentials migration check
    if provider.lower() == "gmail" and not path.exists():
        legacy = GMAIL_LEGACY_DIR / "token.json"
        if legacy.exists():
            try:
                GOOGLE_CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
                path.write_bytes(legacy.read_bytes())
                logger.info("Successfully migrated legacy Gmail token to Google core token path.")
            except Exception as exc:
                logger.warning(f"Failed to migrate legacy Gmail token: {exc}")

    if not path.exists():
        return None

    try:
        return Credentials.from_authorized_user_file(str(path))
    except Exception as exc:
        logger.warning(f"Failed to load credentials for {provider}: {exc}")
        return None


def save_credentials(provider: str, credentials: Credentials) -> None:
    """Save OAuth2 credentials to the shared credentials file.

    Args:
        provider: The provider name.
        credentials: The credentials object to save.
    """
    path = _get_token_path(provider)
    try:
        GOOGLE_CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
        # credentials.to_json() returns serialized credentials string
        path.write_text(credentials.to_json(), encoding="utf-8")
    except OSError as exc:
        logger.warning(f"Failed to save credentials for {provider}: {exc}")


def clear_credentials(provider: str) -> None:
    """Delete local OAuth2 token file.

    Args:
        provider: The provider name.
    """
    path = _get_token_path(provider)
    try:
        if path.exists():
            path.unlink()
    except OSError as exc:
        logger.warning(f"Failed to clear credentials for {provider}: {exc}")


def load_metadata(provider: str) -> dict:
    """Load JSON metadata cached properties.

    Args:
        provider: The provider name.

    Returns:
        Dictionary of connection metadata.
    """
    path = _get_metadata_path(provider)

    # Legacy Gmail metadata migration check
    if provider.lower() == "gmail" and not path.exists():
        legacy = GMAIL_LEGACY_DIR / "metadata.json"
        if legacy.exists():
            try:
                GOOGLE_CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
                path.write_bytes(legacy.read_bytes())
                logger.info("Successfully migrated legacy Gmail metadata to Google core metadata path.")
            except Exception as exc:
                logger.warning(f"Failed to migrate legacy Gmail metadata: {exc}")

    if not path.exists():
        return {}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_metadata(provider: str, data: dict) -> None:
    """Save JSON metadata cache properties.

    Args:
        provider: The provider name.
        data: Key-value dict to update.
    """
    path = _get_metadata_path(provider)
    try:
        GOOGLE_CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
        existing = load_metadata(provider)
        existing.update(data)
        path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.warning(f"Failed to save metadata cache for {provider}: {exc}")


def clear_metadata(provider: str) -> None:
    """Delete JSON metadata cache file.

    Args:
        provider: The provider name.
    """
    path = _get_metadata_path(provider)
    try:
        if path.exists():
            path.unlink()
    except OSError as exc:
        logger.warning(f"Failed to clear metadata cache for {provider}: {exc}")
