"""Logging and timing utility helpers for the Search tool."""

import uuid
from rich.console import Console
from rich.theme import Theme

# Theme specifically styled for our Search pipeline stages
console = Console(theme=Theme({
    "border": "bold blue",
    "stage": "bold cyan",
    "query": "bold green",
    "success": "bold green",
    "info": "white",
    "warning": "bold yellow",
    "error": "bold red",
    "time": "bold magenta"
}))


def generate_request_id() -> str:
    """Generate a short unique request ID for session correlation."""
    return uuid.uuid4().hex[:6]


def safe_print(text: str, style: str) -> None:
    """Print to console safely, handling encoding errors on legacy terminals."""
    encoding = getattr(console.file, "encoding", "ascii") or "ascii"
    try:
        # Check if the text is fully encodable in the console's encoding
        text.encode(encoding)
        console.print(text, style=style)
    except UnicodeEncodeError:
        try:
            safe_text = text.encode(encoding, errors="replace").decode(encoding)
            console.print(safe_text, style=style)
        except Exception:
            # Absolute fallback to plain ASCII
            safe_text = text.encode("ascii", errors="replace").decode("ascii")
            console.print(safe_text, style=style)


def log_stage(request_id: str, message: str, style: str = "stage") -> None:
    """Log a structured stage message with Request ID prefix."""
    safe_print(f"[{request_id}] {message}", style=style)


def log_border(request_id: str, char: str = "═", count: int = 35) -> None:
    """Log a formatted stage boundary line."""
    safe_print(f"[{request_id}] {char * count}", style="border")
