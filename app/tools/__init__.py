"""Package exposing all available tools for the agent."""

from app.tools.filesystem import (
    append_file,
    copy,
    create_directory,
    create_file,
    current_directory,
    delete,
    exists,
    find,
    glob,
    list_directory,
    metadata,
    move,
    read_file,
    read_multiple,
    rename,
    search as filesystem_search,
    tree,
    write_file,
)
from app.tools.search import web_search
from app.tools.gmail import (
    gmail_search,
    gmail_read,
    gmail_send,
    gmail_reply,
    gmail_download_attachment,
)
from app.tools.calendar import (
    calendar_list_events,
    calendar_search,
    calendar_free_busy,
    calendar_create_event,
    calendar_create_recurring_event,
    calendar_create_meet_event,
    calendar_update_event,
    calendar_list_shared_calendars,
    calendar_list_tasks,
    calendar_create_task,
    calendar_update_task,
    calendar_delete_task,
)

tools = [
    web_search,
    gmail_search,
    gmail_read,
    gmail_send,
    gmail_reply,
    gmail_download_attachment,
    calendar_list_events,
    calendar_search,
    calendar_free_busy,
    calendar_create_event,
    calendar_create_recurring_event,
    calendar_create_meet_event,
    calendar_update_event,
    calendar_list_shared_calendars,
    calendar_list_tasks,
    calendar_create_task,
    calendar_update_task,
    calendar_delete_task,
    append_file,
    copy,
    create_directory,
    create_file,
    current_directory,
    delete,
    exists,
    find,
    glob,
    list_directory,
    metadata,
    move,
    read_file,
    read_multiple,
    rename,
    filesystem_search,
    tree,
    write_file,
]


def get_tools():
    """Return the list of all available tools."""
    return tools


__all__ = [
    "tools",
    "get_tools",
]
