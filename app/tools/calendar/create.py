"""Google Calendar event creation tools."""

import time
from typing import Any, Literal
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




@tool("calendar_manage_event")
def manage_event(
    action: Literal["create", "update", "delete"],
    event_id: str | None = None,
    event: dict | None = None,
    attendee_action: Literal["add", "remove"] | None = None,
) -> dict[str, Any]:
    """Create, update, or delete calendar events."""
    try:
        if action == "create":
            if not event:
                return {"success": False, "error": "event dictionary is required for create action", "data": None}
            summary = event.get("summary")
            start = event.get("start")
            end = event.get("end")
            if not summary or not start or not end:
                return {"success": False, "error": "summary, start, and end are required in event dictionary for create action", "data": None}
            
            description = event.get("description")
            location = event.get("location")
            attendees = event.get("attendees") or []
            reminders = event.get("reminders") or []
            recurrence_rule = event.get("recurrence_rule")
            conference = event.get("conference", False)
            
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
                recurrence_rule,
                conference,
                "primary"
            )

        elif action == "update":
            if not event_id:
                return {"success": False, "error": "event_id is required for update action", "data": None}

            if attendee_action:
                if not event or "attendees" not in event:
                    return {"success": False, "error": "event dictionary with 'attendees' list is required for attendee_action", "data": None}
                emails = event.get("attendees") or []
                
                if attendee_action == "add":
                    from app.tools.calendar.update import _api_add_attendees
                    details = {
                        "Event ID": event_id,
                        "Calendar ID": "primary",
                        "Add Emails": ", ".join(emails)
                    }
                    return execute_calendar_request(
                        "Update",
                        details,
                        "calendar",
                        _api_add_attendees,
                        event_id,
                        emails,
                        "primary"
                    )
                elif attendee_action == "remove":
                    from app.tools.calendar.update import _api_remove_attendees
                    details = {
                        "Event ID": event_id,
                        "Calendar ID": "primary",
                        "Remove Emails": ", ".join(emails)
                    }
                    return execute_calendar_request(
                        "Update",
                        details,
                        "calendar",
                        _api_remove_attendees,
                        event_id,
                        emails,
                        "primary"
                    )
                else:
                    return {"success": False, "error": f"Unsupported attendee_action: {attendee_action}", "data": None}
            else:
                if not event:
                    return {"success": False, "error": "event dictionary is required for update action", "data": None}
                summary = event.get("summary")
                start = event.get("start")
                end = event.get("end")
                description = event.get("description")
                location = event.get("location")
                attendees = event.get("attendees")
                reminders = event.get("reminders")

                from app.tools.calendar.update import _api_update_event
                details = {
                    "Event ID": event_id,
                    "Calendar ID": "primary",
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
                    "primary"
                )

        elif action == "delete":
            if not event_id:
                return {"success": False, "error": "event_id is required for delete action", "data": None}
            from app.tools.calendar.delete import _api_delete_event
            details = {
                "Event ID": event_id,
                "Calendar ID": "primary"
            }
            return execute_calendar_request(
                "Delete",
                details,
                "calendar",
                _api_delete_event,
                event_id,
                "primary"
            )

        else:
            return {"success": False, "error": f"Unsupported action: {action}", "data": None}
    except Exception as exc:
        return {"success": False, "error": str(exc), "data": None}
