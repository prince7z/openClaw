"""Google Calendar and Tasks tools package for the OpenClaw agent."""

from app.tools.calendar.list import list_calendar
from app.tools.calendar.create import manage_event
from app.tools.calendar.tasks import manage_task
from app.tools.calendar.freebusy import calendar_free_busy

# Standardized tools list for agent binding
tools = [
    list_calendar,
    manage_event,
    manage_task,
    calendar_free_busy,
]

__all__ = [
    "list_calendar",
    "manage_event",
    "manage_task",
    "calendar_free_busy",
    "tools",
]
