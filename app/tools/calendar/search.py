"""Google Calendar search events tool implementation."""

from typing import Any
from langchain.tools import tool

from app.tools.calendar.executor import execute_calendar_request
from app.tools.calendar.schemas import SearchResponse, parse_google_event


def _api_search(
    service: Any,
    query: str,
    limit: int,
    calendar_id: str
) -> dict[str, Any]:
    """Execute raw search API query.

    Args:
        service: Authenticated Google Calendar client.
        query: Full-text search string.
        limit: Limit of results.
        calendar_id: Calendar ID.

    Returns:
        A SearchResponse dictionary.
    """
    res = service.events().list(
        calendarId=calendar_id,
        q=query,
        maxResults=limit,
        singleEvents=True
    ).execute()

    items = res.get("items") or []
    events = [parse_google_event(evt) for evt in items]

    response = SearchResponse(
        success=True,
        events=events
    )
    return response.model_dump()


@tool("calendar.search")
def calendar_search(
    query: str,
    limit: int = 10,
    calendar_id: str = "primary"
) -> dict[str, Any]:
    """Search for calendar events using a text query.

    Args:
        query: Free-text search terms (matches subject, description, locations, attendee emails).
        limit: Max results count. Defaults to 10.
        calendar_id: Calendar ID to query. Defaults to 'primary'.

    Returns:
        A dict containing success state and a list of parsed CalendarEvents.
    """
    details = {
        "Calendar ID": calendar_id,
        "Limit": limit,
        "Query": query
    }
    return execute_calendar_request(
        "Search",
        details,
        "calendar",
        _api_search,
        query,
        limit,
        calendar_id
    )
