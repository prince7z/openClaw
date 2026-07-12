"""Token and metadata serialization store."""

import json
import logging
from pathlib import Path
from google.oauth2.credentials import Credentials

from app.integrations.gmail.config import TOKEN_PATH, METADATA_PATH

logger = logging.getLogger("openclaw-agent")


def load_credentials() -> Credentials | None:
    """Load user credentials from local token.json file."""
    if not TOKEN_PATH.exists():
        return None
    try:
        return Credentials.from_authorized_user_file(str(TOKEN_PATH))
    except Exception as exc:
        logger.warning(f"Failed to parse credentials file: {exc}")
        return None


def save_credentials(credentials: Credentials) -> None:
    """Save user credentials to local token.json file."""
    try:
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(credentials.to_json(), encoding="utf-8")
    except OSError as exc:
        logger.error(f"Failed to write credentials file: {exc}")


def clear_credentials() -> None:
    """Remove local token.json credentials file."""
    if TOKEN_PATH.exists():
        try:
            TOKEN_PATH.unlink()
        except OSError as exc:
            logger.warning(f"Failed to delete credentials file: {exc}")
    clear_metadata()


def save_metadata(data: dict) -> None:
    """Save connection metadata cache (e.g. authorized email address, OAuth verifier)."""
    try:
        METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        existing = load_metadata()
        existing.update(data)
        METADATA_PATH.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.warning(f"Failed to save metadata cache: {exc}")


def load_metadata() -> dict:
    """Load cached connection metadata (e.g. email address)."""
    if not METADATA_PATH.exists():
        return {}
    try:
        return json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def clear_metadata() -> None:
    """Remove local metadata.json cache file."""
    if METADATA_PATH.exists():
        try:
            METADATA_PATH.unlink()
        except OSError as exc:
            logger.warning(f"Failed to delete metadata cache file: {exc}")
