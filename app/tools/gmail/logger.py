"""Logging utility for formatting Gmail tool executions with Rich."""

from typing import Any
from rich.console import Console
from rich.theme import Theme

console = Console(theme=Theme({
    "border": "bold blue",
    "header": "bold cyan",
    "label": "bold green",
    "value": "white",
    "success": "bold green",
    "warning": "bold yellow",
    "error": "bold red"
}))

# Action icons for beautiful stage headers
ICONS = {
    "Search": "📧",
    "Read": "📖",
    "Send": "📤",
    "Reply": "↩",
    "Download Attachment": "💾"
}


def log_gmail_stage(action: str, details: dict[str, Any] | None = None) -> None:
    """Log a styled header and metadata block for a Gmail tool action.

    Args:
        action: The action name (e.g. 'Search', 'Read', 'Send', 'Reply').
        details: Optional dictionary of metadata key-values to display.
    """
    icon = ICONS.get(action, "📧")
    console.print("[border]══════════════════════════════════[/]")
    console.print(f"[header]{icon} Gmail {action}[/]")
    console.print("[border]══════════════════════════════════[/]")
    
    if details:
        for key, val in details.items():
            console.print(f"[label]{key:<12}[/] [value]{val}[/]")
