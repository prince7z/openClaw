"""Google Calendar list shared calendars tool."""

from typing import Any
from langchain.tools import tool

from app.tools.calendar.executor import execute_calendar_request
from app.tools.calendar.schemas import SharedCalendarResponse


def _api_list_calendars(service: Any) -> dict[str, Any]:
    """Execute raw CalendarList query.

    Args:
        service: Authenticated Google Calendar client.

    Returns:
        A SharedCalendarResponse dictionary.
    """
    res = service.calendarList().list().execute()
    items = res.get("items") or []

    calendars = []
    for item in items:
        calendars.append({
            "id": item.get("id"),
            "summary": item.get("summary") or "(No Subject)",
            "description": item.get("description"),
            "primary": item.get("primary", False),
            "access_role": item.get("accessRole")
        })

    response = SharedCalendarResponse(
        success=True,
        calendars=calendars
    )
    return response.model_dump()


# Internal helper function, not exposed as tool
def calendar_list_shared_calendars() -> dict[str, Any]:
    """Retrieve lists of calendars that the user has access to (including secondary/shared calendars).

    Returns:
        A dict containing success state and details of accessible calendars (id, summary, role).
    """
    return execute_calendar_request(
        "Shared",
        {},
        "calendar",
        _api_list_calendars
    )
