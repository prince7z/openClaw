"""Integration test for OpenClaw Memory System V2."""

import asyncio
import logging
import sys
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage

# Setup import path for OpenClaw root
sys.path.append(".")

from app.conversation.manager import ConversationManager
from app.conversation.summarizer import ConversationSummarizer
from app.database.sqlite import repository
from app.tools.memory import retrieve_memory
from app.database.vector.client import get_qdrant_client
from app.database.vector.collection import init_memory_collections

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("test-memory-v2")


async def run_test():
    logger.info("Initializing test workspace...")

    # Ensure Qdrant is running and collections exist
    client = get_qdrant_client()
    if client:
        logger.info("Qdrant client successfully connected. Initializing collections...")
        init_memory_collections(client)
    else:
        logger.warning("Qdrant is not available. Skipping Qdrant vector-based test assertions.")

    # 1. Create a mock active conversation in SQLite
    chat_id = 99999123
    logger.info(f"Setting up mock active conversation for chat_id={chat_id}...")
    
    # Pre-clean active and archive for consistency
    await repository.delete_active(chat_id)
    
    manager = ConversationManager()
    
    # Append message sequence to active conversation
    state = await manager.load(chat_id)
    state["messages"] = [
        HumanMessage(content="Hello! My name is Alex, and I am a software engineer working on Python projects."),
        AIMessage(content="Nice to meet you, Alex! What Python project are we working on?"),
        HumanMessage(content="We are building the OpenClaw AI agent. We also decided to use Qdrant for memory stores."),
        AIMessage(content="Perfect. Qdrant is a great choice for semantic vector storage.")
    ]
    await manager.save(chat_id, state)

    # Load active conversation state to verify it exists
    state = await manager.load(chat_id)
    assert len(state["messages"]) == 4, "Active messages should have exactly 4 items."
    logger.info("✓ Active conversation setup verified successfully.")

    # 2. Verify single LLM extraction pass
    logger.info("Verifying single-call LLM extraction of title, summary, and memories...")
    summarizer = ConversationSummarizer()
    extracted = await summarizer.extract_summary_and_memories(state["messages"])
    
    logger.info(f"Extracted Title: {extracted.get('title')}")
    logger.info(f"Extracted Summary: {extracted.get('summary')}")
    logger.info(f"Extracted Semantic Memories: {extracted.get('semantic_memories')}")
    logger.info(f"Extracted Episodic Memories: {extracted.get('episodic_memories')}")
    
    assert "title" in extracted, "Extracted object must contain title."
    assert "summary" in extracted, "Extracted object must contain summary."
    assert "semantic_memories" in extracted, "Extracted object must contain semantic_memories."
    assert "episodic_memories" in extracted, "Extracted object must contain episodic_memories."
    logger.info("✓ Single LLM extraction validated.")

    # 3. Verify End conversation lifecycle (SQLite archival + Qdrant store + active cleanup)
    logger.info("Testing conversation /end archival flow...")
    archive_res = await manager.end(chat_id)
    
    assert archive_res["success"] is True, "Archival should be successful."
    assert await repository.get_active(chat_id) is None, "Active conversation should be deleted."
    
    # Check if archive exists in SQLite
    archives = await repository.list_archives(chat_id)
    assert len(archives) >= 1, "There should be at least one archive for this chat ID."
    logger.info(f"✓ SQLite archival verified. Title: {archives[0]['title']}")

    # Wait a moment for background Qdrant updates to finish
    await asyncio.sleep(2.0)

    # 4. Verify retrieve_memory tool execution
    logger.info("Testing retrieve_memory tool invocation...")
    
    # Test query searching for user's details
    result = retrieve_memory.invoke({"query": "What is the user's name and project?", "sources": ["semantic", "episodic", "conversation"]})
    logger.info(f"Search Results:\n{result}")

    # Verify query for project architectural choices
    result_choice = retrieve_memory.invoke({"query": "What database did we decide to use for vector stores?", "sources": ["semantic", "episodic"]})
    logger.info(f"Search Results for database choice:\n{result_choice}")

    # Verify default sources (None) fetches successfully
    result_default = retrieve_memory.invoke({"query": "Alex working on Python"})
    logger.info(f"Default search results:\n{result_default}")

    logger.info("✓ retrieve_memory tool tests completed.")

    # Cleanup SQLite test data
    logger.info("Cleaning up SQLite test database entries...")
    # Delete test archive
    conn = await repository.get_db_connection()
    try:
        await conn.execute("DELETE FROM chat_archive WHERE chat_id = ?", (chat_id,))
        await conn.commit()
        logger.info("SQLite test data cleaned successfully.")
    finally:
        await conn.close()

    logger.info("Integration test run finished successfully!")


if __name__ == "__main__":
    asyncio.run(run_test())
