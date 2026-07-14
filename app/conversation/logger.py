"""Console logger helper utilizing Rich to output formatted conversation events."""

from rich.console import Console
from rich.panel import Panel

console = Console()


def log_loaded(chat_id: int, duration_ms: float) -> None:
    """Log loaded conversation status.

    Args:
        chat_id: Chat identifier.
        duration_ms: Load duration.
    """
    console.print(
        f"[bold green][Load][/bold green] Conversation Loaded | "
        f"Chat ID: [cyan]{chat_id}[/cyan] | "
        f"Time: [yellow]{duration_ms:.2f}ms[/yellow]"
    )


def log_created(chat_id: int) -> None:
    """Log created conversation status.

    Args:
        chat_id: Chat identifier.
    """
    console.print(
        f"[bold blue][New][/bold blue] Conversation Created | "
        f"Chat ID: [cyan]{chat_id}[/cyan]"
    )


def log_appended(chat_id: int) -> None:
    """Log user message appended status.

    Args:
        chat_id: Chat identifier.
    """
    console.print(
        f"[bold magenta][Msg][/bold magenta] User Message Appended | "
        f"Chat ID: [cyan]{chat_id}[/cyan]"
    )


def log_saved(chat_id: int, duration_ms: float) -> None:
    """Log saved state status.

    Args:
        chat_id: Chat identifier.
        duration_ms: Write duration.
    """
    console.print(
        f"[bold green][Save][/bold green] Conversation Saved | "
        f"Chat ID: [cyan]{chat_id}[/cyan] | "
        f"Time: [yellow]{duration_ms:.2f}ms[/yellow]"
    )


def log_archived(chat_id: int, title: str, duration_ms: float) -> None:
    """Log archived conversation status.

    Args:
        chat_id: Chat identifier.
        title: Generated title.
        duration_ms: Archive duration.
    """
    console.print(
        f"[bold green][Archive][/bold green] Conversation Archived | "
        f"Chat ID: [cyan]{chat_id}[/cyan] | "
        f"Title: '[green]{title}[/green]' | "
        f"Time: [yellow]{duration_ms:.2f}ms[/yellow]"
    )


def log_deleted(chat_id: int) -> None:
    """Log active state deletion status.

    Args:
        chat_id: Chat identifier.
    """
    console.print(
        f"[bold red][Del][/bold red] Active Conversation Deleted | "
        f"Chat ID: [cyan]{chat_id}[/cyan]"
    )
