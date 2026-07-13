"""Rich terminal formatting for Browser Automation actions and performance metrics."""

from typing import Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def log_browser_action(action: str, details: dict[str, Any]) -> None:
    """Print a visually rich panel describing the action details.

    Args:
        action: The browser command name (e.g. Open, Click).
        details: Mapped parameters of the call.
    """
    table = Table(show_header=False, box=None, padding=(0, 2))
    for key, val in details.items():
        table.add_row(f"[bold cyan]{key}[/bold cyan]", str(val))
    console.print(
        Panel(
            table,
            title=f"[bold green]Browser Action: {action}[/bold green]",
            border_style="green",
            expand=False
        )
    )


def log_stabilization(duration_ms: float, strategy: str) -> None:
    """Print stabilization execution timing details.

    Args:
        duration_ms: Time taken to reach DOM settlement.
        strategy: Wait strategy description.
    """
    console.print(
        f"[dim white]Page stabilized in[/dim white] "
        f"[bold yellow]{duration_ms:.2f}ms[/bold yellow] "
        f"[dim white](strategy: {strategy})[/dim white]"
    )


def log_extraction(counts: dict[str, int]) -> None:
    """Print element count summaries compiled from A11y & DOM analysis.

    Args:
        counts: Counts of buttons, inputs, links, and products.
    """
    summary = ", ".join(f"{k}: [bold green]{v}[/bold green]" for k, v in counts.items())
    console.print(f"[bold blue]Extracted Elements[/bold blue] -> {summary}")


def log_browser_error(action: str, error: str) -> None:
    """Print high-visibility action failure panels.

    Args:
        action: Failed browser command.
        error: The associated error description string.
    """
    console.print(
        Panel(
            f"[bold red]Error:[/bold red] {error}",
            title=f"[bold red]Browser {action} Failed[/bold red]",
            border_style="red",
            expand=False
        )
    )
