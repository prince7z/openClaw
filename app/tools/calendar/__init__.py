"""Google Calendar and Tasks tools package for the OpenClaw agent."""

from app.tools.calendar.create import (
    calendar_create_event,
    calendar_create_meet_event,
    calendar_create_recurring_event,
)
from app.tools.calendar.delete import calendar_delete_event
from app.tools.calendar.freebusy import calendar_free_busy
from app.tools.calendar.list import calendar_list_events
from app.tools.calendar.search import calendar_search
from app.tools.calendar.shared import calendar_list_shared_calendars
from app.tools.calendar.tasks import (
    calendar_create_task,
    calendar_delete_task,
    calendar_list_tasks,
    calendar_update_task,
)
from app.tools.calendar.update import (
    calendar_update_event,
    calendar_add_attendees,
    calendar_remove_attendees,
)

# Standardized tools list for agent binding
tools = [
    calendar_list_events,
    calendar_search,
    calendar_free_busy,
    calendar_create_event,
    calendar_create_recurring_event,
    calendar_create_meet_event,
    calendar_update_event,
    calendar_add_attendees,
    calendar_remove_attendees,
    calendar_list_shared_calendars,
    calendar_list_tasks,
    calendar_create_task,
    calendar_update_task,
    calendar_delete_task
]

__all__ = [
    "calendar_list_events",
    "calendar_search",
    "calendar_free_busy",
    "calendar_create_event",
    "calendar_create_recurring_event",
    "calendar_create_meet_event",
    "calendar_update_event",
    "calendar_add_attendees",
    "calendar_remove_attendees",
    "calendar_list_shared_calendars",
    "calendar_list_tasks",
    "calendar_create_task",
    "calendar_update_task",
    "calendar_delete_task",
    "tools"
]
