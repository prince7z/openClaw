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


def log_memories_stored(semantic_count: int, episodic_count: int) -> None:
    """Log the storage of semantic and episodic memories to Qdrant."""
    console.print(
        f"[bold blue][Memory Store][/bold blue] Stored memories in Qdrant | "
        f"Semantic: [green]{semantic_count}[/green] | "
        f"Episodic: [green]{episodic_count}[/green]"
    )


def log_retrieval_started(query: str, sources: list[str]) -> None:
    """Log the beginning of memory retrieval."""
    sources_str = ", ".join(sources)
    console.print(
        f"[bold cyan][Memory Query][/bold cyan] Querying Long-Term Memory | "
        f"Query: '[yellow]{query}[/yellow]' | "
        f"Sources: [magenta]{sources_str}[/magenta]"
    )


def log_retrieval_completed(total_candidates: int, final_top_k: int) -> None:
    """Log completion of memory retrieval and filtering results."""
    console.print(
        f"[bold green][Memory Match][/bold green] Retrieval Finished | "
        f"Found: [yellow]{total_candidates} candidates[/yellow] | "
        f"Delivered: [green]{final_top_k} matched[/green]"
    )

