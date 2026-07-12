"""Pydantic validation models for Google Calendar and Tasks tools."""

from pydantic import BaseModel, Field


class Attendee(BaseModel):
    """Event attendee representation."""
    email: str = Field(description="Email address of the attendee")
    response_status: str | None = Field(default=None, alias="responseStatus", description="Response status (e.g., accepted, declined)")

    class Config:
        populate_by_name = True


class Reminder(BaseModel):
    """Event reminder representation."""
    method: str = Field(description="Reminder method (e.g., email, popup)")
    minutes: int = Field(description="Minutes before start time to trigger")


class CalendarEvent(BaseModel):
    """A Google Calendar event."""
    id: str = Field(description="Unique identifier of the event")
    summary: str = Field(description="Title of the event")
    description: str | None = Field(default=None, description="Detailed description of the event")
    start: str = Field(description="Start time (ISO-8601 string or date)")
    end: str = Field(description="End time (ISO-8601 string or date)")
    location: str | None = Field(default=None, description="Location of the event")
    meet_link: str | None = Field(default=None, alias="meetLink", description="Google Meet video call link")
    calendar_link: str | None = Field(default=None, alias="calendarLink", description="Google Calendar event detail page link")
    attendees: list[Attendee] = Field(default_factory=list, description="List of event attendees")
    reminders: list[Reminder] = Field(default_factory=list, description="Event reminders override list")

    class Config:
        populate_by_name = True


class Task(BaseModel):
    """A Google Tasks task."""
    id: str = Field(description="Unique identifier of the task")
    title: str = Field(description="Title/Subject of the task")
    notes: str | None = Field(default=None, description="Notes/Description of the task")
    status: str = Field(description="Status of the task ('needsAction' or 'completed')")
    due: str | None = Field(default=None, description="Due date (ISO-8601 string or date)")
    completed: str | None = Field(default=None, description="Completion timestamp, if completed")


class RecurringRule(BaseModel):
    """Recurrence rule settings (RRULE) for creating recurring events."""
    frequency: str = Field(description="Recurrence frequency ('DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY')")
    interval: int = Field(default=1, description="Interval between recurrences (e.g. every 2 weeks)")
    count: int | None = Field(default=None, description="Number of times to repeat")
    until: str | None = Field(default=None, description="End date of recurrence (YYYYMMDD or ISO-8601)")


class SearchResponse(BaseModel):
    """Response payload for event search operations."""
    success: bool = Field(description="Whether the query succeeded")
    events: list[CalendarEvent] = Field(default_factory=list, description="Matching calendar events list")


class TodayResponse(BaseModel):
    """Response payload for today's events listing."""
    success: bool = Field(description="Whether the query succeeded")
    events: list[CalendarEvent] = Field(default_factory=list, description="Events scheduled for today")


class NextEventResponse(BaseModel):
    """Response payload for fetching the next upcoming event."""
    success: bool = Field(description="Whether the query succeeded")
    event: CalendarEvent | None = Field(default=None, description="The next upcoming calendar event")


class FreeBusyResponse(BaseModel):
    """Response payload for freebusy queries."""
    success: bool = Field(description="Whether the query succeeded")
    busy_intervals: list[dict] = Field(default_factory=list, description="List of start/end time dicts indicating busy ranges")


class CreateResponse(BaseModel):
    """Response payload for event creation."""
    success: bool = Field(description="Whether the event creation succeeded")
    event_id: str = Field(alias="event_id", description="Unique identifier of the created event")
    meet_link: str | None = Field(default=None, alias="meet_link", description="Google Meet link")
    calendar_link: str | None = Field(default=None, alias="calendar_link", description="Google Calendar detail link")

    class Config:
        populate_by_name = True


class UpdateResponse(BaseModel):
    """Response payload for event updates."""
    success: bool = Field(description="Whether the event update succeeded")
    event_id: str = Field(alias="event_id", description="Unique identifier of the updated event")

    class Config:
        populate_by_name = True


class DeleteResponse(BaseModel):
    """Response payload for event deletions."""
    success: bool = Field(description="Whether the deletion succeeded")


class NotificationResponse(BaseModel):
    """Placeholder response for webhook notifications registration (not implemented)."""
    success: bool = Field(default=False, description="Webhook watch is not supported in V1")


class TaskResponse(BaseModel):
    """Response payload for task list/manipulation operations."""
    success: bool = Field(description="Whether the task operation succeeded")
    task: Task | None = Field(default=None, description="Task details, if applicable")
    tasks: list[Task] = Field(default_factory=list, description="List of tasks, if applicable")


class SharedCalendarResponse(BaseModel):
    """Response payload listing calendars user has access to."""
    success: bool = Field(description="Whether the query succeeded")
    calendars: list[dict] = Field(default_factory=list, description="List of shared/available calendar properties")


def parse_google_event(evt: dict) -> CalendarEvent:
    """Parse raw Google Calendar Event resource dictionary into CalendarEvent model.

    Args:
        evt: Google Calendar API event resource dictionary.

    Returns:
        A CalendarEvent model instance.
    """
    start_data = evt.get("start") or {}
    end_data = evt.get("end") or {}

    start = start_data.get("dateTime") or start_data.get("date") or ""
    end = end_data.get("dateTime") or end_data.get("date") or ""

    # Search for video conference link
    meet_link = None
    conf = evt.get("conferenceData") or {}
    for entry in conf.get("entryPoints") or []:
        if entry.get("entryPointType") == "video":
            meet_link = entry.get("uri")
            break

    attendees = [
        Attendee(
            email=att.get("email", ""),
            response_status=att.get("responseStatus")
        ) for att in evt.get("attendees") or []
    ]

    reminders_list = []
    reminders_data = evt.get("reminders") or {}
    if not reminders_data.get("useDefault", False):
        reminders_list = [
            Reminder(
                method=rem.get("method", "popup"),
                minutes=rem.get("minutes", 0)
            ) for rem in reminders_data.get("overrides") or []
        ]

    return CalendarEvent(
        id=evt.get("id", ""),
        summary=evt.get("summary") or "(No Subject)",
        description=evt.get("description"),
        start=start,
        end=end,
        location=evt.get("location"),
        meet_link=meet_link,
        calendar_link=evt.get("htmlLink"),
        attendees=attendees,
        reminders=reminders_list
    )
