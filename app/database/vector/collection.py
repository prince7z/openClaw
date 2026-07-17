"""Qdrant memory collections initialization."""

import logging
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

logger = logging.getLogger("openclaw-agent")

SEMANTIC_COLLECTION = "semantic_memory"
EPISODIC_COLLECTION = "episodic_memory"
VECTOR_DIMENSION = 384  # BAAI/bge-small-en-v1.5 vector dimension


def init_memory_collections(client: QdrantClient) -> None:
    """Check and create semantic_memory and episodic_memory collections in Qdrant if missing.

    Args:
        client: Active QdrantClient instance.
    """
    try:
        # Create semantic_memory collection
        if not client.collection_exists(SEMANTIC_COLLECTION):
            logger.info(f"Creating Qdrant collection: {SEMANTIC_COLLECTION}...")
            client.create_collection(
                collection_name=SEMANTIC_COLLECTION,
                vectors_config=VectorParams(
                    size=VECTOR_DIMENSION,
                    distance=Distance.COSINE
                )
            )
        else:
            logger.debug(f"Collection {SEMANTIC_COLLECTION} already exists.")

        # Create episodic_memory collection
        if not client.collection_exists(EPISODIC_COLLECTION):
            logger.info(f"Creating Qdrant collection: {EPISODIC_COLLECTION}...")
            client.create_collection(
                collection_name=EPISODIC_COLLECTION,
                vectors_config=VectorParams(
                    size=VECTOR_DIMENSION,
                    distance=Distance.COSINE
                )
            )
        else:
            logger.debug(f"Collection {EPISODIC_COLLECTION} already exists.")

    except Exception as exc:
        logger.error(f"Failed to initialize Qdrant memory collections: {exc}")
