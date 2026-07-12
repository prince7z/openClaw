"""Calendar and Tasks service clients builders."""

from typing import Any
from app.integrations.google.service import get_google_service


def get_calendar_service() -> Any:
    """Retrieve and build an authorized Google Calendar API service client.

    Returns:
        The Calendar API resource client.
    """
    return get_google_service("calendar", "v3", "calendar")


def get_tasks_service() -> Any:
    """Retrieve and build an authorized Google Tasks API service client.

    Returns:
        The Tasks API resource client.
    """
    return get_google_service("tasks", "v1", "calendar")
