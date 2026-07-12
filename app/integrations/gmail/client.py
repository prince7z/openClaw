"""Gmail API client construction and credentials management."""

from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app.integrations.gmail.token_store import load_credentials, save_credentials


def get_client():
    """Load credentials, refreshing them if expired, and build the Gmail API service.

    Returns:
        The authenticated googleapiclient.discovery.Resource client for Gmail API.

    Raises:
        ValueError: If Gmail integration is not connected (no credentials exist)
            or if the credentials fail to refresh.
    """
    creds = load_credentials()
    if not creds:
        raise ValueError("Gmail credentials not found. Please run connection flow first.")

    if creds.expired:
        try:
            creds.refresh(Request())
            save_credentials(creds)
        except Exception as exc:
            raise ValueError(f"Failed to refresh expired Gmail OAuth token: {exc}")

    return build("gmail", "v1", credentials=creds)
