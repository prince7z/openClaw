"""Google Calendar event creation tools."""

import time
from typing import Any
from langchain.tools import tool

from app.tools.calendar.executor import execute_calendar_request
from app.tools.calendar.schemas import CreateResponse


def _api_create_event(
    service: Any,
    summary: str,
    start: str,
    end: str,
    description: str | None,
    location: str | None,
    attendees: list[str],
    reminders: list[dict],
    recurrence_rule: dict | None,
    create_meet: bool,
    calendar_id: str
) -> dict[str, Any]:
    """Execute raw Google Calendar insert API request.

    Args:
        service: Authenticated Google Calendar client.
        summary: Event title.
        start: ISO-8601 start time.
        end: ISO-8601 end time.
        description: Event description.
        location: Event location.
        attendees: Attendee emails list.
        reminders: Reminders overrides list of dicts.
        recurrence_rule: Optional dictionary of RRULE parameters.
        create_meet: Whether to request Google Meet creation.
        calendar_id: Calendar ID.

    Returns:
        A serialized CreateResponse dictionary.
    """
    body: dict[str, Any] = {
        "summary": summary,
        "description": description,
        "location": location,
        "start": {"dateTime": start} if "T" in start else {"date": start},
        "end": {"dateTime": end} if "T" in end else {"date": end}
    }

    if attendees:
        body["attendees"] = [{"email": email} for email in attendees]

    if reminders:
        body["reminders"] = {
            "useDefault": False,
            "overrides": reminders
        }

    # Handle Google Meet video integration request
    if create_meet:
        body["conferenceData"] = {
            "createRequest": {
                "requestId": f"meet_{int(time.time())}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"}
            }
        }

    # Handle Recurrence Rules (RRULE)
    if recurrence_rule:
        freq = recurrence_rule.get("frequency", "DAILY").upper()
        rrule = f"FREQ={freq}"

        interval = recurrence_rule.get("interval")
        if interval:
            rrule += f";INTERVAL={interval}"

        count = recurrence_rule.get("count")
        if count:
            rrule += f";COUNT={count}"

        until = recurrence_rule.get("until")
        if until:
            rrule += f";UNTIL={until}"

        body["recurrence"] = [f"RRULE:{rrule}"]

    # Dispatch insert request
    kwargs = {"calendarId": calendar_id, "body": body}
    if create_meet:
        kwargs["conferenceDataVersion"] = 1

    created = service.events().insert(**kwargs).execute()

    # Search for the created meet link in conference details
    meet_link = None
    conf = created.get("conferenceData") or {}
    for entry in conf.get("entryPoints") or []:
        if entry.get("entryPointType") == "video":
            meet_link = entry.get("uri")
            break

    response = CreateResponse(
        success=True,
        event_id=created.get("id", ""),
        meet_link=meet_link,
        calendar_link=created.get("htmlLink")
    )
    return response.model_dump()


@tool("calendar.create_event")
def calendar_create_event(
    summary: str,
    start: str,
    end: str,
    description: str | None = None,
    location: str | None = None,
    attendees: list[str] = [],
    reminders: list[dict] = [],
    calendar_id: str = "primary"
) -> dict[str, Any]:
    """Create a new standard calendar event.

    Args:
        summary: The title/summary of the calendar event.
        start: ISO-8601 date-time string (e.g. '2026-07-13T15:00:00Z') or date (e.g. '2026-07-13').
        end: ISO-8601 date-time string (e.g. '2026-07-13T16:00:00Z') or date (e.g. '2026-07-13').
        description: Optional details or description text of the event.
        location: Optional location description string.
        attendees: Optional list of email addresses of attendees. Defaults to [].
        reminders: Optional list of reminder overrides, e.g. [{'method': 'popup', 'minutes': 30}]. Defaults to [].
        calendar_id: Calendar ID. Defaults to 'primary'.

    Returns:
        A dict containing success state, event_id, and calendar_link.
    """
    details = {
        "Title": summary,
        "Start": start,
        "End": end,
        "Attendees": len(attendees),
        "Reminders": len(reminders)
    }
    return execute_calendar_request(
        "Create",
        details,
        "calendar",
        _api_create_event,
        summary,
        start,
        end,
        description,
        location,
        attendees,
        reminders,
        None,  # No recurrence
        False,  # No meet
        calendar_id
    )


@tool("calendar.create_recurring_event")
def calendar_create_recurring_event(
    summary: str,
    start: str,
    end: str,
    recurrence_rule: dict,
    description: str | None = None,
    location: str | None = None,
    attendees: list[str] = [],
    reminders: list[dict] = [],
    calendar_id: str = "primary"
) -> dict[str, Any]:
    """Create a new recurring calendar event using a recurrence rule (RRULE).

    Args:
        summary: The title of the calendar event.
        start: ISO-8601 start date-time or date string.
        end: ISO-8601 end date-time or date string.
        recurrence_rule: Dict specifying recurrence details. Keys:
          - frequency: 'DAILY', 'WEEKLY', 'MONTHLY', or 'YEARLY'. (Required)
          - interval: Optional integer multiplier (e.g., 2 for every 2 weeks).
          - count: Optional integer maximum number of recurrences.
          - until: Optional end date string (e.g. '20261231' or '2026-12-31T23:59:59Z').
        description: Optional details of the event.
        location: Optional location string.
        attendees: Optional list of email addresses. Defaults to [].
        reminders: Optional list of reminder override dicts. Defaults to [].
        calendar_id: Calendar ID. Defaults to 'primary'.

    Returns:
        A dict containing success state, event_id, and calendar_link.
    """
    details = {
        "Title": summary,
        "Start": start,
        "End": end,
        "Recurrence": str(recurrence_rule),
        "Attendees": len(attendees)
    }
    return execute_calendar_request(
        "Create",
        details,
        "calendar",
        _api_create_event,
        summary,
        start,
        end,
        description,
        location,
        attendees,
        reminders,
        recurrence_rule,
        False,  # No meet
        calendar_id
    )


@tool("calendar.create_meet_event")
def calendar_create_meet_event(
    summary: str,
    start: str,
    end: str,
    description: str | None = None,
    location: str | None = None,
    attendees: list[str] = [],
    reminders: list[dict] = [],
    calendar_id: str = "primary"
) -> dict[str, Any]:
    """Create a calendar event with a Google Meet conference link auto-generated.

    Args:
        summary: The title of the calendar event.
        start: ISO-8601 start date-time or date string.
        end: ISO-8601 end date-time or date string.
        description: Optional details of the event.
        location: Optional location string.
        attendees: Optional list of email addresses. Defaults to [].
        reminders: Optional list of reminder override dicts. Defaults to [].
        calendar_id: Calendar ID. Defaults to 'primary'.

    Returns:
        A dict containing success state, event_id, meet_link, and calendar_link.
    """
    details = {
        "Title": summary,
        "Start": start,
        "End": end,
        "Meet Enabled": "True",
        "Attendees": len(attendees)
    }
    return execute_calendar_request(
        "Create",
        details,
        "calendar",
        _api_create_event,
        summary,
        start,
        end,
        description,
        location,
        attendees,
        reminders,
        None,  # No recurrence
        True,  # Meet enabled
        calendar_id
    )
