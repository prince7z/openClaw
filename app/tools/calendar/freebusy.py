"""Google Calendar freebusy checking tool implementation."""

from typing import Any
from langchain.tools import tool

from app.tools.calendar.executor import execute_calendar_request
from app.tools.calendar.schemas import FreeBusyResponse


def _api_freebusy(
    service: Any,
    start: str,
    end: str,
    calendar_ids: list[str]
) -> dict[str, Any]:
    """Execute raw FreeBusy query.

    Args:
        service: Authenticated Google Calendar client.
        start: ISO-8601 query range start.
        end: ISO-8601 query range end.
        calendar_ids: List of calendar IDs to inspect.

    Returns:
        A FreeBusyResponse dictionary.
    """
    body = {
        "timeMin": start,
        "timeMax": end,
        "items": [{"id": cid} for cid in calendar_ids]
    }

    res = service.freebusy().query(body=body).execute()
    calendars = res.get("calendars") or {}

    busy_intervals = []
    for cid, data in calendars.items():
        busy_list = data.get("busy") or []
        for interval in busy_list:
            busy_intervals.append({
                "calendar_id": cid,
                "start": interval.get("start"),
                "end": interval.get("end")
            })

    response = FreeBusyResponse(
        success=True,
        busy_intervals=busy_intervals
    )
    return response.model_dump()


@tool("calendar.free_busy")
def calendar_free_busy(
    start: str,
    end: str,
    calendar_ids: list[str] = ["primary"]
) -> dict[str, Any]:
    """Check availability (busy times) for one or more calendars.

    Args:
        start: ISO-8601 query range start (e.g. '2026-07-12T00:00:00Z').
        end: ISO-8601 query range end (e.g. '2026-07-12T23:59:59Z').
        calendar_ids: List of calendar email/ID strings to check. Defaults to ['primary'].

    Returns:
        A dict containing success state and a list of busy interval start/end ranges.
    """
    details = {
        "Start Time": start,
        "End Time": end,
        "Calendars": ", ".join(calendar_ids)
    }
    return execute_calendar_request(
        "FreeBusy",
        details,
        "calendar",
        _api_freebusy,
        start,
        end,
        calendar_ids
    )
