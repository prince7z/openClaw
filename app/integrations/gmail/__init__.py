"""Gmail integration layer package."""

from app.integrations.gmail.auth import (
    is_connected,
    get_authorization_url,
    complete_auth,
)
from app.integrations.gmail.service import get_gmail_service

__all__ = ["is_connected", "get_authorization_url", "complete_auth", "get_gmail_service"]
