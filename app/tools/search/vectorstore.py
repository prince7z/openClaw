"""Qdrant client wrapper to cache search chunk embeddings in Qdrant collection web_search_cache."""

import logging
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from app.config import Qdrant_url, Qdrant_api_key
from app.tools.search.schemas import Chunk
from app.tools.search.utils import log_stage

logger = logging.getLogger("openclaw-agent")

COLLECTION_NAME = "web_search_cache"
VECTOR_DIMENSION = 1024  # Standard dimension for BAAI/bge-m3


def _get_qdrant_client() -> QdrantClient | None:
    """Initialize and return the Qdrant client."""
    if not Qdrant_url:
        return None
    try:
        return QdrantClient(url=Qdrant_url, api_key=Qdrant_api_key, timeout=5.0)
    except Exception as exc:
        logger.warning(f"Failed to instantiate QdrantClient: {exc}")
        return None


def _ensure_collection(client: QdrantClient, request_id: str) -> bool:
    """Ensure the web_search_cache Qdrant collection exists."""
    try:
        if not client.collection_exists(COLLECTION_NAME):
            log_stage(request_id, f"📚 Creating Qdrant collection: {COLLECTION_NAME}...")
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=VECTOR_DIMENSION,
                    distance=Distance.COSINE
                )
            )
        return True
    except Exception as exc:
        log_stage(request_id, f"Error: Qdrant collection check/creation failed: {exc}", "error")
        return False


def save_chunks_to_qdrant(request_id: str, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
    """Insert chunk texts and their vector embeddings into Qdrant.

    Args:
        request_id: Unique request session identifier.
        chunks: A list of Chunk models.
        embeddings: A list of float vector lists corresponding to the chunks.
    """
    log_stage(request_id, "📚 Storing Chunks in Qdrant Cache...")

    if not chunks or not embeddings:
        return

    client = _get_qdrant_client()
    if not client:
        log_stage(request_id, "Warning: Qdrant is not configured. Skipping cache storage.", "warning")
        return

    if not _ensure_collection(client, request_id):
        return

    try:
        points = []
        for chunk, vector in zip(chunks, embeddings):
            if not vector:
                continue
                
            # Create a UUID based on chunk ID to prevent duplicate insertions
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"chunk_{chunk.id}"))
            
            payload = {
                "content": chunk.content,
                "metadata": chunk.metadata,
                "score": chunk.score
            }
            
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                )
            )

        if points:
            client.upsert(collection_name=COLLECTION_NAME, points=points)
            log_stage(request_id, f"📚 Successfully cached {len(points)} chunks in Qdrant.")
    except Exception as exc:
        log_stage(request_id, f"Error: Failed to save points to Qdrant: {exc}", "error")
