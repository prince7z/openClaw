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



