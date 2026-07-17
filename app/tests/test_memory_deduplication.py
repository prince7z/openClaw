"""Integration test for OpenClaw Memory Deduplication."""

import asyncio
import logging
import sys
import uuid
from datetime import datetime

# Setup import path for OpenClaw root
sys.path.append(".")

from app.database.vector.client import get_qdrant_client
from app.database.vector.schemas import SemanticMemory, EpisodicMemory
from app.database.vector.memory import (
    upsert_semantic_memory,
    upsert_episodic_memory,
    search_semantic_memories,
    search_episodic_memories,
    SEMANTIC_COLLECTION,
    EPISODIC_COLLECTION
)
from app.database.vector.collection import init_memory_collections

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("test-memory-deduplication")


async def run_test():
    logger.info("Initializing test workspace...")

    # Ensure Qdrant is running and collections exist
    client = get_qdrant_client()
    if not client:
        logger.error("Qdrant is not available. Cannot run deduplication test.")
        sys.exit(1)

    logger.info("Qdrant client successfully connected. Initializing collections...")
    init_memory_collections(client)

    # Clean up existing test memories if any
    created_ids = []

    try:
        # Create base timestamps
        original_created_at = "2026-07-17T00:00:00.000000"
        
        # Generate completely unique keywords to avoid matching existing points in cloud DB
        rand_suffix = uuid.uuid4().hex[:8]
        user_name = f"User_{rand_suffix}"
        proj_name = f"Project_{rand_suffix}"

        text1 = f"{user_name} is a software developer specializing in Python projects."
        summary1 = f"Decision to use Qdrant for memory stores in the {proj_name} project."

        text2 = f"{user_name} works on Python."
        summary2 = f"We decided to use Qdrant for {proj_name}."

        text3 = f"{user_name} is a senior software engineer specializing in Python development for the {proj_name} system."
        summary3 = f"Decision to use Qdrant database for vector memory storage in the {proj_name} AI agent project."

        # 1. Prepare initial memories (highly descriptive)
        logger.info("1. Inserting initial memories...")
        sem1 = SemanticMemory(
            id=str(uuid.uuid4()),
            type="knowledge",
            category="projects",
            text=text1,
            importance=0.8,
            created_at=original_created_at,
            updated_at=original_created_at,
            last_accessed=original_created_at,
            source_chat="123",
            tags=["python"]
        )
        created_ids.append((SEMANTIC_COLLECTION, sem1.id))
        await upsert_semantic_memory(sem1)

        ep1 = EpisodicMemory(
            id=str(uuid.uuid4()),
            type="discussion",
            summary=summary1,
            importance=0.8,
            created_at=original_created_at,
            updated_at=original_created_at,
            last_accessed=original_created_at,
            source_chat="123",
            tags=["qdrant"]
        )
        created_ids.append((EPISODIC_COLLECTION, ep1.id))
        await upsert_episodic_memory(ep1)

        # Wait a moment for Qdrant updates to index
        await asyncio.sleep(1.0)

        # 2. Attempt to upsert LESS descriptive duplicate memories
        logger.info("2. Attempting to insert LESS descriptive duplicate memories...")
        sem2 = SemanticMemory(
            id=str(uuid.uuid4()),
            type="knowledge",
            category="projects",
            text=text2,
            importance=0.7,
            source_chat="123",
            tags=["code"]
        )
        created_ids.append((SEMANTIC_COLLECTION, sem2.id)) # If deduplication works, this ID won't actually be inserted
        await upsert_semantic_memory(sem2)

        ep2 = EpisodicMemory(
            id=str(uuid.uuid4()),
            type="discussion",
            summary=summary2,
            importance=0.7,
            source_chat="123",
            tags=["db"]
        )
        created_ids.append((EPISODIC_COLLECTION, ep2.id)) # If deduplication works, this ID won't actually be inserted
        await upsert_episodic_memory(ep2)

        await asyncio.sleep(1.0)

        # 3. Retrieve and assert that the text was preserved (since sem1/ep1 were richer)
        # and that tags are merged, created_at preserved, and updated_at updated.
        logger.info("3. Retrieving memories and verifying updates for LESS descriptive run...")
        
        # Verify Semantic
        res_sem = client.retrieve(collection_name=SEMANTIC_COLLECTION, ids=[sem1.id])
        assert len(res_sem) == 1, "Original semantic memory should exist."
        payload_sem = res_sem[0].payload
        assert payload_sem["text"] == text1, "Text should be preserved since original was richer."
        assert set(payload_sem["tags"]) == {"python", "code"}, f"Tags should be uniquely merged. Found: {payload_sem['tags']}"
        assert payload_sem["created_at"] == original_created_at, "created_at should be preserved."
        assert payload_sem["updated_at"] != original_created_at, "updated_at should be updated."

        # Verify sem2 was not inserted as a separate point
        res_sem2 = client.retrieve(collection_name=SEMANTIC_COLLECTION, ids=[sem2.id])
        assert len(res_sem2) == 0, "Deduplicated semantic memory ID should NOT be inserted."

        # Verify Episodic
        res_ep = client.retrieve(collection_name=EPISODIC_COLLECTION, ids=[ep1.id])
        assert len(res_ep) == 1, "Original episodic memory should exist."
        payload_ep = res_ep[0].payload
        assert payload_ep["summary"] == summary1, "Summary should be preserved since original was richer."
        assert set(payload_ep["tags"]) == {"qdrant", "db"}, f"Tags should be uniquely merged. Found: {payload_ep['tags']}"
        assert payload_ep["created_at"] == original_created_at, "created_at should be preserved."
        assert payload_ep["updated_at"] != original_created_at, "updated_at should be updated."

        # Verify ep2 was not inserted as a separate point
        res_ep2 = client.retrieve(collection_name=EPISODIC_COLLECTION, ids=[ep2.id])
        assert len(res_ep2) == 0, "Deduplicated episodic memory ID should NOT be inserted."

        logger.info("✓ Verification for LESS descriptive run completed successfully.")

        # 4. Attempt to upsert MORE descriptive duplicate memories
        logger.info("4. Attempting to insert MORE descriptive duplicate memories...")
        sem3 = SemanticMemory(
            id=str(uuid.uuid4()),
            type="knowledge",
            category="projects",
            text=text3,
            importance=0.9,
            source_chat="123",
            tags=["ai"]
        )
        created_ids.append((SEMANTIC_COLLECTION, sem3.id))
        await upsert_semantic_memory(sem3)

        ep3 = EpisodicMemory(
            id=str(uuid.uuid4()),
            type="discussion",
            summary=summary3,
            importance=0.9,
            source_chat="123",
            tags=["vector"]
        )
        created_ids.append((EPISODIC_COLLECTION, ep3.id))
        await upsert_episodic_memory(ep3)

        await asyncio.sleep(1.0)

        # 5. Retrieve and assert that the text/summary were updated to the richer version
        # and importance was updated, tags merged, and created_at preserved.
        logger.info("5. Retrieving memories and verifying updates for MORE descriptive run...")
        
        # Verify Semantic
        res_sem_rich = client.retrieve(collection_name=SEMANTIC_COLLECTION, ids=[sem1.id])
        payload_sem_rich = res_sem_rich[0].payload
        assert payload_sem_rich["text"] == text3, "Text should be replaced with richer version."
        assert payload_sem_rich["importance"] == 0.9, "Importance should be updated."
        assert set(payload_sem_rich["tags"]) == {"python", "code", "ai"}, "Tags should be uniquely merged."
        assert payload_sem_rich["created_at"] == original_created_at, "created_at should be preserved."

        # Verify sem3 was not inserted as a separate point
        res_sem3 = client.retrieve(collection_name=SEMANTIC_COLLECTION, ids=[sem3.id])
        assert len(res_sem3) == 0, "Deduplicated semantic memory ID should NOT be inserted."

        # Verify Episodic
        res_ep_rich = client.retrieve(collection_name=EPISODIC_COLLECTION, ids=[ep1.id])
        payload_ep_rich = res_ep_rich[0].payload
        assert payload_ep_rich["summary"] == summary3, "Summary should be replaced with richer version."
        assert payload_ep_rich["importance"] == 0.9, "Importance should be updated."
        assert set(payload_ep_rich["tags"]) == {"qdrant", "db", "vector"}, "Tags should be uniquely merged."
        assert payload_ep_rich["created_at"] == original_created_at, "created_at should be preserved."

        # Verify ep3 was not inserted as a separate point
        res_ep3 = client.retrieve(collection_name=EPISODIC_COLLECTION, ids=[ep3.id])
        assert len(res_ep3) == 0, "Deduplicated episodic memory ID should NOT be inserted."

        logger.info("✓ Verification for MORE descriptive run completed successfully.")

    finally:
        # Clean up all created points in Qdrant
        logger.info("Cleaning up Qdrant points...")
        for col, point_id in created_ids:
            try:
                client.delete(collection_name=col, points_selector=[point_id])
            except Exception:
                pass
        logger.info("Cleanup complete.")

    logger.info("All deduplication integration tests passed successfully!")


if __name__ == "__main__":
    asyncio.run(run_test())
