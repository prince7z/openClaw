"""Google Calendar list events tool implementation."""

import datetime
from typing import Any
from langchain.tools import tool

from app.tools.calendar.executor import execute_calendar_request
from app.tools.calendar.schemas import SearchResponse, parse_google_event


def _api_list_events(
    service: Any,
    start: str | None,
    end: str | None,
    limit: int,
    calendar_id: str
) -> dict[str, Any]:
    """Execute raw list events API query.

    Args:
        service: Authenticated Google Calendar client.
        start: ISO-8601 start time.
        end: ISO-8601 end time.
        limit: Limit of results.
        calendar_id: Calendar ID.

    Returns:
        A SearchResponse dictionary.
    """
    kwargs: dict[str, Any] = {
        "calendarId": calendar_id,
        "maxResults": limit,
        "singleEvents": True,
        "orderBy": "startTime"
    }

    if start:
        kwargs["timeMin"] = start
    else:
        # Default starting point to current time to list upcoming events
        kwargs["timeMin"] = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

    if end:
        kwargs["timeMax"] = end

    res = service.events().list(**kwargs).execute()
    items = res.get("items") or []
    events = [parse_google_event(evt) for evt in items]

    response = SearchResponse(
        success=True,
        events=events
    )
    return response.model_dump()


@tool("calendar.list_events")
def calendar_list_events(
    start: str | None = None,
    end: str | None = None,
    limit: int = 10,
    calendar_id: str = "primary"
) -> dict[str, Any]:
    """List calendar events within an optional time range.

    If start is not specified, it defaults to the current time (listing upcoming events).
    Useful for:
    - Checking today's events (by setting start and end to the bounds of today).
    - Querying the next upcoming meeting (by setting limit=1).

    Args:
        start: Optional start date-time string in ISO-8601 format (e.g. '2026-07-12T15:00:00Z').
        end: Optional end date-time string in ISO-8601 format (e.g. '2026-07-12T23:59:59Z').
        limit: Max results count. Defaults to 10.
        calendar_id: Calendar ID to query. Defaults to 'primary'.

    Returns:
        A dict containing success state and a list of parsed CalendarEvents.
    """
    details = {
        "Calendar ID": calendar_id,
        "Limit": limit,
        "Start Time": start or "Now",
        "End Time": end or "Unbounded"
    }
    return execute_calendar_request(
        "List",
        details,
        "calendar",
        _api_list_events,
        start,
        end,
        limit,
        calendar_id
    )
