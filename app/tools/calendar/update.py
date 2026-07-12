"""Google Calendar event update tools."""

from typing import Any
from langchain.tools import tool

from app.tools.calendar.executor import execute_calendar_request
from app.tools.calendar.schemas import UpdateResponse


def _api_update_event(
    service: Any,
    event_id: str,
    summary: str | None,
    start: str | None,
    end: str | None,
    description: str | None,
    location: str | None,
    attendees: list[str] | None,
    reminders: list[dict] | None,
    calendar_id: str
) -> dict[str, Any]:
    """Execute raw Calendar patch API query.

    Args:
        service: Authenticated Google Calendar client.
        event_id: Event ID.
        summary: Optional updated event summary.
        start: Optional updated ISO-8601 start time.
        end: Optional updated ISO-8601 end time.
        description: Optional updated event description.
        location: Optional updated location.
        attendees: Optional updated attendee email list.
        reminders: Optional updated reminders overrides.
        calendar_id: Calendar ID.

    Returns:
        An UpdateResponse dictionary.
    """
    body: dict[str, Any] = {}

    if summary is not None:
        body["summary"] = summary
    if description is not None:
        body["description"] = description
    if location is not None:
        body["location"] = location

    if start:
        body["start"] = {"dateTime": start} if "T" in start else {"date": start}
    if end:
        body["end"] = {"dateTime": end} if "T" in end else {"date": end}

    if attendees is not None:
        body["attendees"] = [{"email": email} for email in attendees]

    if reminders is not None:
        body["reminders"] = {
            "useDefault": False,
            "overrides": reminders
        }

    patched = service.events().patch(
        calendarId=calendar_id,
        eventId=event_id,
        body=body
    ).execute()

    response = UpdateResponse(
        success=True,
        event_id=patched.get("id", event_id)
    )
    return response.model_dump()


def _api_add_attendees(
    service: Any,
    event_id: str,
    emails: list[str],
    calendar_id: str
) -> dict[str, Any]:
    """Fetch existing event, merge new attendees, and patch event.

    Args:
        service: Authenticated Google Calendar client.
        event_id: Event ID.
        emails: Emails to add.
        calendar_id: Calendar ID.

    Returns:
        An UpdateResponse dictionary.
    """
    evt = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
    current = evt.get("attendees") or []

    # Get emails already in list
    existing = {a.get("email") for a in current if a.get("email")}

    updated = list(current)
    for email in emails:
        if email not in existing:
            updated.append({"email": email})

    patched = service.events().patch(
        calendarId=calendar_id,
        eventId=event_id,
        body={"attendees": updated}
    ).execute()

    response = UpdateResponse(
        success=True,
        event_id=patched.get("id", event_id)
    )
    return response.model_dump()


def _api_remove_attendees(
    service: Any,
    event_id: str,
    emails: list[str],
    calendar_id: str
) -> dict[str, Any]:
    """Fetch existing event, filter out specified emails, and patch event.

    Args:
        service: Authenticated Google Calendar client.
        event_id: Event ID.
        emails: Emails to remove.
        calendar_id: Calendar ID.

    Returns:
        An UpdateResponse dictionary.
    """
    evt = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
    current = evt.get("attendees") or []

    remove_set = set(emails)
    updated = [a for a in current if a.get("email") not in remove_set]

    patched = service.events().patch(
        calendarId=calendar_id,
        eventId=event_id,
        body={"attendees": updated}
    ).execute()

    response = UpdateResponse(
        success=True,
        event_id=patched.get("id", event_id)
    )
    return response.model_dump()


@tool("calendar.update_event")
def calendar_update_event(
    event_id: str,
    summary: str | None = None,
    start: str | None = None,
    end: str | None = None,
    description: str | None = None,
    location: str | None = None,
    attendees: list[str] | None = None,
    reminders: list[dict] | None = None,
    calendar_id: str = "primary"
) -> dict[str, Any]:
    """Update properties of an existing calendar event (patch updates).

    Only fields that are explicitly provided will be updated; other fields are left untouched.

    Args:
        event_id: The unique hex ID of the target calendar event.
        summary: Optional updated title/summary.
        start: Optional updated ISO-8601 start date-time or date.
        end: Optional updated ISO-8601 end date-time or date.
        description: Optional updated detailed description.
        location: Optional updated location string.
        attendees: Optional list of email addresses of attendees to overwrite the list.
        reminders: Optional list of reminder override dicts to overwrite (e.g. [{'method': 'popup', 'minutes': 15}]).
        calendar_id: Calendar ID to query. Defaults to 'primary'.

    Returns:
        A dict containing success state and event_id.
    """
    details = {
        "Event ID": event_id,
        "Calendar ID": calendar_id,
        "Update Title": summary or "No Change",
        "Update Time": f"{start or 'No Change'} -> {end or 'No Change'}"
    }
    return execute_calendar_request(
        "Update",
        details,
        "calendar",
        _api_update_event,
        event_id,
        summary,
        start,
        end,
        description,
        location,
        attendees,
        reminders,
        calendar_id
    )


@tool("calendar.add_attendees")
def calendar_add_attendees(
    event_id: str,
    emails: list[str],
    calendar_id: str = "primary"
) -> dict[str, Any]:
    """Add one or more email addresses to the attendee list of an existing event.

    Args:
        event_id: The unique hex ID of the target event.
        emails: A list of email address strings to add as attendees.
        calendar_id: Calendar ID to query. Defaults to 'primary'.

    Returns:
        A dict containing success state and event_id.
    """
    details = {
        "Event ID": event_id,
        "Calendar ID": calendar_id,
        "Add Emails": ", ".join(emails)
    }
    return execute_calendar_request(
        "Update",
        details,
        "calendar",
        _api_add_attendees,
        event_id,
        emails,
        calendar_id
    )


@tool("calendar.remove_attendees")
def calendar_remove_attendees(
    event_id: str,
    emails: list[str],
    calendar_id: str = "primary"
) -> dict[str, Any]:
    """Remove one or more email addresses from the attendee list of an existing event.

    Args:
        event_id: The unique hex ID of the target event.
        emails: A list of email address strings to remove from attendees.
        calendar_id: Calendar ID to query. Defaults to 'primary'.

    Returns:
        A dict containing success state and event_id.
    """
    details = {
        "Event ID": event_id,
        "Calendar ID": calendar_id,
        "Remove Emails": ", ".join(emails)
    }
    return execute_calendar_request(
        "Update",
        details,
        "calendar",
        _api_remove_attendees,
        event_id,
        emails,
        calendar_id
    )
