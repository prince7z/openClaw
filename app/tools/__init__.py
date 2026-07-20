"""Package exposing all available tools for the agent."""

from app.tools.filesystem import (
    read_file,
    write_file,
    manage_file,
    list_files,
    search_files,
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
    list_calendar,
    manage_event,
    manage_task,
    calendar_free_busy,
)
from app.tools.browser import (
    browser_open,
    browser_interact,
    browser_navigate,
    browser_scroll,
    browser_file,
    browser_close,
)

from app.tools.memory import retrieve_memory
from app.tools.sandbox.commands import (
    execute_python_code,
    execute_node_code,
    start_sandbox_server,
    stop_sandbox_server,
    get_sandbox_preview,
    execute_bash_command,

)

tools = [
    retrieve_memory,
    web_search,
    gmail_search,
    gmail_read,
    gmail_send,
    gmail_reply,
    gmail_download_attachment,
    list_calendar,
    manage_event,
    manage_task,
    calendar_free_busy,
    browser_open,
    browser_interact,
    browser_navigate,
    browser_scroll,
    browser_file,
    browser_close,
    read_file,
    write_file,
    manage_file,
    list_files,
    search_files,
    execute_bash_command,
    execute_python_code,
    execute_node_code,
    start_sandbox_server,
    stop_sandbox_server,
    get_sandbox_preview,
]


def get_tools():
    """Return the list of all available tools."""
    return tools


__all__ = [
    "tools",
    "get_tools",
]
