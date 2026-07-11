"""LangGraph Agent for OpenClaw."""

import logging
from rich.logging import RichHandler

from app.agent.graph import graph

# Configure standard logging to route through RichHandler with markup styling enabled
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)]
)

logger = logging.getLogger("openclaw-agent")
logger.info("Initializing OpenClaw agent module...")

__all__ = ["graph"]
