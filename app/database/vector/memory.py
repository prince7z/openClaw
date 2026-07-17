"""Vector database lifecycle operations for Semantic and Episodic memories."""

import asyncio
import logging
from datetime import datetime
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchAny

from app.database.vector.client import get_qdrant_client
from app.database.vector.embedder import generate_embeddings
from app.database.vector.schemas import SemanticMemory, EpisodicMemory
from app.config import memory_duplicate_threshold

logger = logging.getLogger("openclaw-agent")

SEMANTIC_COLLECTION = "semantic_memory"
EPISODIC_COLLECTION = "episodic_memory"


def build_tag_filter(tags: list[str] | None) -> Filter | None:
    """Build Qdrant Filter to restrict search to records matching any of the specified tags.

    Args:
        tags: Optional list of keyword tags.

    Returns:
        Qdrant Filter object if tags are provided, else None.
    """
    if not tags:
        return None
    return Filter(
        must=[
            FieldCondition(
                key="tags",
                match=MatchAny(any=tags)
            )
        ]
    )


async def store_semantic_memories(memories: list[SemanticMemory]) -> None:
    """Embed and store semantic memories in Qdrant.

    Args:
        memories: A list of SemanticMemory objects.
    """
    client = get_qdrant_client()
    if not client or not memories:
        return

    texts = [m.text for m in memories]
    embeddings = await generate_embeddings("store_semantic_memory", texts)

    points = []
    for memory, embedding in zip(memories, embeddings):
        if not embedding:
            continue
        points.append(
            PointStruct(
                id=memory.id,
                vector=embedding,
                payload=memory.model_dump()
            )
        )

    if points:
        try:
            client.upsert(collection_name=SEMANTIC_COLLECTION, points=points)
            logger.info(f"Successfully stored {len(points)} semantic memories in Qdrant.")
        except Exception as exc:
            logger.error(f"Failed to upsert semantic memories to Qdrant: {exc}")


async def store_episodic_memories(memories: list[EpisodicMemory]) -> None:
    """Embed and store episodic memories in Qdrant.

    Args:
        memories: A list of EpisodicMemory objects.
    """
    client = get_qdrant_client()
    if not client or not memories:
        return

    texts = [m.summary for m in memories]
    embeddings = await generate_embeddings("store_episodic_memory", texts)

    points = []
    for memory, embedding in zip(memories, embeddings):
        if not embedding:
            continue
        points.append(
            PointStruct(
                id=memory.id,
                vector=embedding,
                payload=memory.model_dump()
            )
        )

    if points:
        try:
            client.upsert(collection_name=EPISODIC_COLLECTION, points=points)
            logger.info(f"Successfully stored {len(points)} episodic memories in Qdrant.")
        except Exception as exc:
            logger.error(f"Failed to upsert episodic memories to Qdrant: {exc}")


async def search_semantic_memories(
    query_vector: list[float],
    tags: list[str] | None = None,
    limit: int = 20
) -> list[dict]:
    """Search Qdrant semantic_memory collection.

    Args:
        query_vector: The query embedding.
        tags: Optional tags to filter search.
        limit: Max results to return.

    Returns:
        List of memory payload dicts with a similarity score key added.
    """
    client = get_qdrant_client()
    if not client:
        return []

    try:
        response = client.query_points(
            collection_name=SEMANTIC_COLLECTION,
            query=query_vector,
            query_filter=build_tag_filter(tags),
            limit=limit
        )
        memories = []
        for hit in response.points:
            payload = hit.payload or {}
            payload["id"] = str(hit.id)
            payload["similarity"] = hit.score
            memories.append(payload)
        return memories
    except Exception as exc:
        logger.error(f"Failed searching semantic memories in Qdrant: {exc}")
        return []


async def search_episodic_memories(
    query_vector: list[float],
    tags: list[str] | None = None,
    limit: int = 20
) -> list[dict]:
    """Search Qdrant episodic_memory collection.

    Args:
        query_vector: The query embedding.
        tags: Optional tags to filter search.
        limit: Max results to return.

    Returns:
        List of memory payload dicts with a similarity score key added.
    """
    client = get_qdrant_client()
    if not client:
        return []

    try:
        response = client.query_points(
            collection_name=EPISODIC_COLLECTION,
            query=query_vector,
            query_filter=build_tag_filter(tags),
            limit=limit
        )
        memories = []
        for hit in response.points:
            payload = hit.payload or {}
            payload["id"] = str(hit.id)
            payload["similarity"] = hit.score
            memories.append(payload)
        return memories
    except Exception as exc:
        logger.error(f"Failed searching episodic memories in Qdrant: {exc}")
        return []


async def update_retrieval_metadata(
    collection: str,
    point_id: str,
    current_access_count: int
) -> None:
    """Asynchronously update the last_accessed timestamp and increment access_count in Qdrant payload.

    Args:
        collection: Qdrant collection name.
        point_id: Unique UUID string or identifier of the point.
        current_access_count: The access_count prior to this retrieval.
    """
    client = get_qdrant_client()
    if not client:
        return

    new_count = current_access_count + 1
    now = datetime.utcnow().isoformat()

    try:
        client.set_payload(
            collection_name=collection,
            payload={
                "last_accessed": now,
                "access_count": new_count
            },
            points=[point_id]
        )
        logger.debug(f"Updated metadata for {point_id} in {collection}: access_count={new_count}, last_accessed={now}")
    except Exception as exc:
        logger.warning(f"Failed to update retrieval metadata for {point_id} in {collection}: {exc}")


async def update_memory(collection: str, point_id: str, payload: dict) -> None:
    """Update a specific memory's payload details (future-proof lifecycle method).

    Args:
        collection: Target collection name.
        point_id: Target point ID.
        payload: Dictionary of fields to update.
    """
    client = get_qdrant_client()
    if not client:
        return
    try:
        client.set_payload(collection_name=collection, payload=payload, points=[point_id])
        logger.info(f"Updated memory {point_id} in {collection}.")
    except Exception as exc:
        logger.error(f"Failed to update memory {point_id} in {collection}: {exc}")


async def delete_memory(collection: str, point_id: str) -> None:
    """Delete a memory from a collection (future-proof lifecycle method).

    Args:
        collection: Target collection name.
        point_id: Target point ID.
    """
    client = get_qdrant_client()
    if not client:
        return
    try:
        client.delete(collection_name=collection, points_selector=[point_id])
        logger.info(f"Deleted memory {point_id} from {collection}.")
    except Exception as exc:
        logger.error(f"Failed to delete memory {point_id} from {collection}: {exc}")


async def upsert_semantic_memory(memory: SemanticMemory) -> None:
    """Embed, search, and upsert a semantic memory to Qdrant, avoiding duplicates."""
    client = get_qdrant_client()
    if not client:
        return

    # 1. Embed the new memory text
    embeddings = await generate_embeddings("upsert_semantic_memory", [memory.text])
    embedding = embeddings[0] if embeddings else None
    if not embedding:
        logger.error("Failed to generate embedding for semantic memory.")
        return

    # 2. Search strictly within semantic_memory collection
    candidates = await search_semantic_memories(query_vector=embedding, limit=5)

    # 3. Rerank candidates using BAAI reranker
    from app.database.vector.reranker import rerank_chunks
    from app.tools.search.schemas import Chunk

    chunks = [
        Chunk(
            id=m["id"],
            content=m.get("text") or "",
            metadata=m
        )
        for m in candidates
    ]

    highest_candidate = None
    if chunks:
        reranked = await rerank_chunks(request_id="semantic_dedup", query=memory.text, chunks=chunks, top_k=5)
        if reranked:
            highest_candidate = reranked[0]

    # 4. Decision logic
    if not highest_candidate or highest_candidate.score < memory_duplicate_threshold:
        # Insert new memory
        points = [
            PointStruct(
                id=memory.id,
                vector=embedding,
                payload=memory.model_dump()
            )
        ]
        try:
            client.upsert(collection_name=SEMANTIC_COLLECTION, points=points)
            logger.info(f"Stored new semantic memory: {memory.id}")
        except Exception as exc:
            logger.error(f"Failed to store semantic memory: {exc}")
    else:
        # Update existing memory
        existing_payload = highest_candidate.metadata
        existing_id = existing_payload["id"]
        existing_text = existing_payload.get("text") or ""
        new_text = memory.text

        now = datetime.utcnow().isoformat()
        updated_payload = dict(existing_payload)
        updated_payload["last_accessed"] = now
        updated_payload["updated_at"] = now

        # Unique union of tags
        existing_tags = existing_payload.get("tags") or []
        new_tags = memory.tags or []
        merged_tags = list(set(existing_tags + new_tags))
        updated_payload["tags"] = merged_tags

        text_changed = len(new_text) > len(existing_text)
        if text_changed:
            updated_payload["text"] = new_text
            updated_payload["importance"] = memory.importance
            try:
                client.upsert(
                    collection_name=SEMANTIC_COLLECTION,
                    points=[
                        PointStruct(
                            id=existing_id,
                            vector=embedding,
                            payload=updated_payload
                        )
                    ]
                )
                logger.info(f"Upserted semantic memory {existing_id} with updated text and embedding.")
            except Exception as exc:
                logger.error(f"Failed to upsert updated semantic memory {existing_id}: {exc}")
        else:
            try:
                client.set_payload(
                    collection_name=SEMANTIC_COLLECTION,
                    payload=updated_payload,
                    points=[existing_id]
                )
                logger.info(f"Updated metadata for semantic memory {existing_id}.")
            except Exception as exc:
                logger.error(f"Failed to set payload for semantic memory {existing_id}: {exc}")


async def upsert_episodic_memory(memory: EpisodicMemory) -> None:
    """Embed, search, and upsert an episodic memory to Qdrant, avoiding duplicates."""
    client = get_qdrant_client()
    if not client:
        return

    # 1. Embed the new memory summary
    embeddings = await generate_embeddings("upsert_episodic_memory", [memory.summary])
    embedding = embeddings[0] if embeddings else None
    if not embedding:
        logger.error("Failed to generate embedding for episodic memory.")
        return

    # 2. Search strictly within episodic_memory collection
    candidates = await search_episodic_memories(query_vector=embedding, limit=5)

    # 3. Rerank candidates using BAAI reranker
    from app.database.vector.reranker import rerank_chunks
    from app.tools.search.schemas import Chunk

    chunks = [
        Chunk(
            id=m["id"],
            content=m.get("summary") or "",
            metadata=m
        )
        for m in candidates
    ]

    highest_candidate = None
    if chunks:
        reranked = await rerank_chunks(request_id="episodic_dedup", query=memory.summary, chunks=chunks, top_k=5)
        if reranked:
            highest_candidate = reranked[0]

    # 4. Decision logic
    if not highest_candidate or highest_candidate.score < memory_duplicate_threshold:
        # Insert new memory
        points = [
            PointStruct(
                id=memory.id,
                vector=embedding,
                payload=memory.model_dump()
            )
        ]
        try:
            client.upsert(collection_name=EPISODIC_COLLECTION, points=points)
            logger.info(f"Stored new episodic memory: {memory.id}")
        except Exception as exc:
            logger.error(f"Failed to store episodic memory: {exc}")
    else:
        # Update existing memory
        existing_payload = highest_candidate.metadata
        existing_id = existing_payload["id"]
        existing_summary = existing_payload.get("summary") or ""
        new_summary = memory.summary

        now = datetime.utcnow().isoformat()
        updated_payload = dict(existing_payload)
        updated_payload["last_accessed"] = now
        updated_payload["updated_at"] = now

        # Unique union of tags
        existing_tags = existing_payload.get("tags") or []
        new_tags = memory.tags or []
        merged_tags = list(set(existing_tags + new_tags))
        updated_payload["tags"] = merged_tags

        summary_changed = len(new_summary) > len(existing_summary)
        if summary_changed:
            updated_payload["summary"] = new_summary
            updated_payload["importance"] = memory.importance
            try:
                client.upsert(
                    collection_name=EPISODIC_COLLECTION,
                    points=[
                        PointStruct(
                            id=existing_id,
                            vector=embedding,
                            payload=updated_payload
                        )
                    ]
                )
                logger.info(f"Upserted episodic memory {existing_id} with updated summary and embedding.")
            except Exception as exc:
                logger.error(f"Failed to upsert updated episodic memory {existing_id}: {exc}")
        else:
            try:
                client.set_payload(
                    collection_name=EPISODIC_COLLECTION,
                    payload=updated_payload,
                    points=[existing_id]
                )
                logger.info(f"Updated metadata for episodic memory {existing_id}.")
            except Exception as exc:
                logger.error(f"Failed to set payload for episodic memory {existing_id}: {exc}")

