import logging
from qdrant_client import QdrantClient
from app.config import Qdrant_url, Qdrant_api_key

logger = logging.getLogger("openclaw-agent")

def get_qdrant_client() -> QdrantClient | None:
    """Initialize and return the Qdrant client."""
    if not Qdrant_url:
        return None
    try:
        return QdrantClient(url=Qdrant_url, api_key=Qdrant_api_key, timeout=5.0)
    except Exception as exc:
        logger.warning(f"Failed to instantiate QdrantClient: {exc}")
        return None

