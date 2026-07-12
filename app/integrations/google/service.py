"""Google API service client generator."""

import logging
from typing import Any
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app.integrations.google.token_store import load_credentials, save_credentials

logger = logging.getLogger("openclaw-agent")


def get_google_service(service_name: str, version: str, provider: str) -> Any:
    """Load authorized credentials, auto-refresh them if expired, and build a client.

    Args:
        service_name: Name of the Google API service (e.g. 'gmail', 'calendar', 'tasks').
        version: Version of the Google API service (e.g. 'v1', 'v3').
        provider: Provider identifier ('gmail', 'calendar').

    Returns:
        Google API client resource object.
    """
    creds = load_credentials(provider)
    if not creds:
        raise ConnectionError(f"No credentials found for provider '{provider}'. Please authorize integration first.")

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            save_credentials(provider, creds)
            logger.info(f"Refreshed expired Google credentials for provider '{provider}'.")
        except Exception as exc:
            raise ConnectionError(f"Credentials for provider '{provider}' are expired and refresh failed: {exc}")

    if not creds.valid:
        raise ConnectionError(f"Google credentials for provider '{provider}' are invalid or expired.")

    return build(service_name, version, credentials=creds)
