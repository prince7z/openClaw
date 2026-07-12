"""Logging utility for formatting Calendar tool executions with Rich."""

from typing import Any
from rich.console import Console
from rich.theme import Theme

console = Console(theme=Theme({
    "border": "bold magenta",
    "header": "bold cyan",
    "label": "bold green",
    "value": "white",
    "success": "bold green",
    "warning": "bold yellow",
    "error": "bold red"
}))

ICONS = {
    "Search": "🔍",
    "List": "📋",
    "FreeBusy": "⏰",
    "Create": "📅",
    "Update": "✏️",
    "Delete": "🗑️",
    "Shared": "👥",
    "Task": "✅"
}


def log_calendar_stage(action: str, details: dict[str, Any] | None = None) -> None:
    """Log a styled header and metadata block for a Google Calendar or Tasks tool action.

    Args:
        action: The action name (e.g. 'Search', 'List', 'Create', 'Task').
        details: Optional dictionary of metadata key-values to display.
    """
    icon = ICONS.get(action, "📅")
    console.print("[border]══════════════════════════════════[/]")
    console.print(f"[header]{icon} Google Calendar {action}[/]")
    console.print("[border]══════════════════════════════════[/]")

    if details:
        for key, val in details.items():
            console.print(f"[label]{key:<15}[/] [value]{val}[/]")
