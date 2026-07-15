"""Google Calendar event deletion tool."""

from typing import Any
from langchain.tools import tool

from app.tools.calendar.executor import execute_calendar_request
from app.tools.calendar.schemas import DeleteResponse


def _api_delete_event(
    service: Any,
    event_id: str,
    calendar_id: str
) -> dict[str, Any]:
    """Execute raw Calendar delete API request.

    Args:
        service: Authenticated Google Calendar client.
        event_id: Event ID to delete.
        calendar_id: Calendar ID.

    Returns:
        A DeleteResponse dictionary.
    """
    service.events().delete(
        calendarId=calendar_id,
        eventId=event_id
    ).execute()

    response = DeleteResponse(success=True)
    return response.model_dump()

