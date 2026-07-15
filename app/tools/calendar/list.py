"""Google Calendar list events tool implementation."""

import datetime
from typing import Any, Literal
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


# Internal helper function, not exposed as tool
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


@tool("calendar.list_calendar")
def list_calendar(
    resource: Literal["events", "tasks", "calendars"] = "events",
    query: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> dict[str, Any]:
    """List calendars, events, or tasks."""
    try:
        if resource == "events":
            if query:
                from app.tools.calendar.search import calendar_search
                return calendar_search(query=query, limit=25)
            else:
                return calendar_list_events(start=start, end=end, limit=25)
        elif resource == "tasks":
            from app.tools.calendar.tasks import calendar_list_tasks
            res = calendar_list_tasks(limit=25)
            if query and res.get("success"):
                tasks = res.get("tasks") or []
                filtered = [
                    t for t in tasks
                    if query.lower() in t.get("title", "").lower() or query.lower() in (t.get("notes") or "").lower()
                ]
                res["tasks"] = filtered
            return res
        elif resource == "calendars":
            from app.tools.calendar.shared import calendar_list_shared_calendars
            res = calendar_list_shared_calendars()
            if query and res.get("success"):
                calendars = res.get("calendars") or []
                filtered = [
                    c for c in calendars
                    if query.lower() in c.get("summary", "").lower() or query.lower() in (c.get("description") or "").lower()
                ]
                res["calendars"] = filtered
            return res
        else:
            return {"success": False, "error": f"Unsupported resource: {resource}"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
