"""Conversation lifecycle manager (Stateless Graph persistence wrapper)."""

import time
import uuid
import logging
import math
import asyncio
from datetime import datetime
from typing import Any, Literal
from langchain_core.messages import HumanMessage


from app.conversation.serializer import StateSerializer, JSONStateSerializer
from app.conversation.summarizer import ConversationSummarizer
from app.conversation import logger as conv_logger
from app.database.sqlite import repository

# Config and memory vectors imports
from app.config import (
    Memory_similarity_weight,
    Memory_importance_weight,
    Memory_recency_weight,
    Memory_minimum_score,
    Memory_top_k,
    Memory_archive_fallback_limit
)
from app.database.vector.memory import (
    upsert_semantic_memory,
    upsert_episodic_memory,
    search_semantic_memories,
    search_episodic_memories,
    update_retrieval_metadata
)
from app.database.vector.schemas import SemanticMemory, EpisodicMemory
from app.tools.search.schemas import Chunk
from app.database.vector.reranker import rerank_chunks
from app.database.vector.embedder import generate_embeddings

logger = logging.getLogger("openclaw-agent")


def get_normalized_similarity(score: float) -> float:
    """Normalize reranking/similarity score to a 0.0 - 1.0 probability range using sigmoid if needed."""
    if 0.0 <= score <= 1.0:
        return score
    try:
        return 1.0 / (1.0 + math.exp(-score))
    except OverflowError:
        return 1.0 if score > 0 else 0.0


def calculate_recency(timestamp_str: str) -> float:
    """Calculate recency score using exponential decay with a 30-day half-life.

    Args:
        timestamp_str: ISO format timestamp string.

    Returns:
        Float decay multiplier between 0.0 and 1.0.
    """
    try:
        dt = datetime.fromisoformat(timestamp_str)
        age_days = (datetime.utcnow() - dt).total_seconds() / (24 * 3600)
        # exponential decay: e^(-lambda * age_days) where lambda = ln(2) / 30
        return math.exp(- (math.log(2) / 30) * max(0.0, age_days))
    except Exception:
        return 0.5  # Neutral fallback


class ConversationManager:
    """Manages creation, retrieval, modification, and archiving of conversation contexts."""

    def __init__(
        self,
        serializer: StateSerializer | None = None,
        summarizer: ConversationSummarizer | None = None
    ):
        """Initialize ConversationManager with dependency-injected helpers.

        Args:
            serializer: Custom state serializer instance.
            summarizer: Custom summarizer instance.
        """
        self.serializer = serializer or JSONStateSerializer()
        self.summarizer = summarizer or ConversationSummarizer()

    async def load(self, chat_id: int) -> dict[str, Any]:
        """Load the conversation state for the specified chat ID.

        If no active conversation is found, initializes and persists a new empty state.

        Args:
            chat_id: Unique identifier for the conversation session.

        Returns:
            The loaded or newly created AgentState dictionary.
        """
        start_time = time.perf_counter()
        active = await repository.get_active(chat_id)

        if active is None:
            # Create a brand new, clean AgentState dictionary
            new_state: dict[str, Any] = {
                "started_at": datetime.utcnow().isoformat(),
                "messages": [],
                "tool_outputs": [],
                "final_response": ""
            }
            state_json = self.serializer.serialize(new_state)
            await repository.create_active(chat_id, state_json)
            conv_logger.log_created(chat_id)
            return new_state

        state = self.serializer.deserialize(active["state_json"])
        duration = (time.perf_counter() - start_time) * 1000.0
        conv_logger.log_loaded(chat_id, duration)
        return state

    async def save(self, chat_id: int, state: dict[str, Any]) -> None:
        """Persist the updated AgentState block to the database.

        Args:
            chat_id: Unique identifier for the session.
            state: The modified state dictionary.
        """
        start_time = time.perf_counter()
        state_json = self.serializer.serialize(state)
        await repository.update_active(chat_id, state_json)
        duration = (time.perf_counter() - start_time) * 1000.0
        conv_logger.log_saved(chat_id, duration)

    async def append_user_message(self, chat_id: int, message: HumanMessage) -> dict[str, Any]:
        """Load the active conversation state, append the user message, and return it.

        Note: Modifies the state ONLY in memory. Does not write to the database.

        Args:
            chat_id: Unique identifier for the session.
            message: The LangChain HumanMessage instance.

        Returns:
            The modified state dictionary.
        """
        state = await self.load(chat_id)
        
        # Modify the message sequence in-memory
        messages_list = list(state.get("messages") or [])
        messages_list.append(message)
        state["messages"] = messages_list
        
        conv_logger.log_appended(chat_id)
        return state

    async def end(self, chat_id: int) -> dict[str, Any]:
        """Summarize, archive, and delete the active conversation inside a single transaction.

        Also extracts and saves semantic/episodic memories to Qdrant.

        Args:
            chat_id: Unique identifier for the session.

        Returns:
            A dictionary summary of the archived conversation.
        """
        start_time = time.perf_counter()
        active = await repository.get_active(chat_id)
        if active is None:
            raise ValueError(f"No active conversation found for chat_id: {chat_id}")

        state = self.serializer.deserialize(active["state_json"])
        messages = state.get("messages") or []

        # 1. Perform single LLM call to extract everything
        extracted = await self.summarizer.extract_summary_and_memories(messages)
        title = extracted.get("title") or "Chat Session"
        summary = extracted.get("summary") or "Archived conversation history."
        semantic_list = extracted.get("semantic_memories") or []
        episodic_list = extracted.get("episodic_memories") or []

        # 2. Store memories in Qdrant (gracefully degrade if Qdrant is not configured)
        from app.database.vector.client import get_qdrant_client
        client = get_qdrant_client()
        stored_semantics = 0
        stored_episodics = 0
        if client:
            try:
                for item in semantic_list:
                    # Ignore rules filter (importance <= 0.1 ignored)
                    importance = float(item.get("importance", 0.5))
                    if importance <= 0.1:
                        continue
                    sem_mem = SemanticMemory(
                        type=item.get("type", "knowledge"),
                        category=item.get("category", "custom"),
                        text=item.get("text", ""),
                        importance=importance,
                        source_chat=str(chat_id),
                        tags=item.get("tags") or []
                    )
                    await upsert_semantic_memory(sem_mem)
                    stored_semantics += 1

                for item in episodic_list:
                    # Ignore rules filter (importance <= 0.1 ignored)
                    importance = float(item.get("importance", 0.5))
                    if importance <= 0.1:
                        continue
                    ep_mem = EpisodicMemory(
                        type=item.get("type", "discussion"),
                        summary=item.get("summary", ""),
                        importance=importance,
                        source_chat=str(chat_id),
                        tags=item.get("tags") or []
                    )
                    await upsert_episodic_memory(ep_mem)
                    stored_episodics += 1
                
                if stored_semantics or stored_episodics:
                    conv_logger.log_memories_stored(stored_semantics, stored_episodics)
            except Exception as q_exc:
                logger.error(f"Failed to store memories in Qdrant: {q_exc}")

        # 3. Archive summary and delete active state in SQLite (single transaction)
        started_at = state.get("started_at") or active["created_at"]
        ended_at = datetime.utcnow().isoformat()
        conversation_id = str(uuid.uuid4())

        archive_payload = {
            "conversation_id": conversation_id,
            "title": title,
            "summary": summary,
            "started_at": started_at,
            "ended_at": ended_at
        }
        await repository.archive_and_delete_active(chat_id, archive_payload)

        duration = (time.perf_counter() - start_time) * 1000.0
        conv_logger.log_archived(chat_id, title, duration)
        conv_logger.log_deleted(chat_id)

        return {
            "success": True,
            "conversation_id": conversation_id,
            "title": title,
            "summary": summary
        }

    async def retrieve_memory_context(
        self,
        query: str,
        sources: list[Literal["conversation", "semantic", "episodic"]] | None = None
    ) -> str:
        """Search, merge, rerank, score, deduplicate, and format relevant memories globally.

        Args:
            query: Semantic query text to search for.
            sources: Target memory sources to search. Defaults to all if empty or None.

        Returns:
            A formatted string of matching memories to supply to the LLM.
        """
        if not sources:
            sources = ["conversation", "semantic", "episodic"]

        conv_logger.log_retrieval_started(query, sources)

        chunks = []

        # 1. Fetch archives from SQLite if requested
        if "conversation" in sources:
            # Try keyword search first
            archive_rows = await repository.search_archives_by_keyword(query)
            if not archive_rows:
                # Fallback: load the most recent N summaries
                archive_rows = await repository.get_recent_archives(Memory_archive_fallback_limit)
            
            for row in archive_rows:
                chunks.append(
                    Chunk(
                        id=row["conversation_id"],
                        content=f"Title: {row['title']}\nSummary: {row['summary']}",
                        metadata={
                            "source": "conversation",
                            "created_at": row["ended_at"],
                            "importance": 0.5
                        }
                    )
                )

        # 2. Query Qdrant if requested
        qdrant_sources = [s for s in sources if s in ("semantic", "episodic")]
        if qdrant_sources:
            # Generate query embedding
            embeddings = await generate_embeddings("memory_retrieval", [query])
            if embeddings and embeddings[0]:
                query_vector = embeddings[0]
                
                # Fetch semantic memories
                if "semantic" in sources:
                    results = await search_semantic_memories(query_vector, limit=20)
                    for hit in results:
                        chunks.append(
                            Chunk(
                                id=hit["id"],
                                content=hit["text"],
                                metadata={
                                    "source": "semantic",
                                    "importance": hit.get("importance", 0.5),
                                    "created_at": hit.get("created_at"),
                                    "last_accessed": hit.get("last_accessed"),
                                    "access_count": hit.get("access_count", 0)
                                }
                            )
                        )
                
                # Fetch episodic memories
                if "episodic" in sources:
                    results = await search_episodic_memories(query_vector, limit=20)
                    for hit in results:
                        chunks.append(
                            Chunk(
                                id=hit["id"],
                                content=hit["summary"],
                                metadata={
                                    "source": "episodic",
                                    "importance": hit.get("importance", 0.5),
                                    "created_at": hit.get("created_at"),
                                    "last_accessed": hit.get("last_accessed"),
                                    "access_count": hit.get("access_count", 0)
                                }
                            )
                        )

        if not chunks:
            conv_logger.log_retrieval_completed(0, 0)
            return "No relevant memories found."

        # 3. Rerank candidates together if there is more than 1
        if len(chunks) > 1:
            try:
                chunks = await rerank_chunks("memory_retrieval", query, chunks, top_k=len(chunks))
            except Exception as exc:
                logger.error(f"Reranking memory candidates failed: {exc}")

        # 4. Calculate combined scores and apply threshold
        valid_chunks = []
        for chunk in chunks:
            similarity = get_normalized_similarity(chunk.score)
            importance = float(chunk.metadata.get("importance", 0.5))
            
            # Calculate recency based on last_accessed or created_at
            date_str = chunk.metadata.get("last_accessed") or chunk.metadata.get("created_at")
            recency = calculate_recency(date_str) if date_str else 0.5

            score = (
                Memory_similarity_weight * similarity +
                Memory_importance_weight * importance +
                Memory_recency_weight * recency
            )
            
            if score >= Memory_minimum_score:
                chunk.score = score  # Assign combined score for sorting
                valid_chunks.append(chunk)

        if not valid_chunks:
            conv_logger.log_retrieval_completed(len(chunks), 0)
            return "No relevant memories found."

        # 5. Sort descending by combined score and deduplicate by content
        sorted_chunks = sorted(valid_chunks, key=lambda x: x.score, reverse=True)
        
        seen_contents = set()
        deduplicated = []
        for chunk in sorted_chunks:
            cleaned = chunk.content.lower().strip()
            if cleaned not in seen_contents:
                seen_contents.add(cleaned)
                deduplicated.append(chunk)

        # Select top K memories
        top_chunks = deduplicated[:Memory_top_k]

        # 6. Format the top K chunks and update retrieval metadata in background
        formatted_memories = []
        for chunk in top_chunks:
            source = chunk.metadata.get("source")
            content = chunk.content.strip()

            # Schedule metadata updates for Qdrant hits
            if source in ("semantic", "episodic"):
                point_id = chunk.id
                access_count = chunk.metadata.get("access_count", 0)
                collection_name = "semantic_memory" if source == "semantic" else "episodic_memory"
                asyncio.create_task(update_retrieval_metadata(collection_name, point_id, access_count))

            # Format cleanly while hiding internal DB/collection terms
            if source == "semantic":
                formatted_memories.append(f"- Fact: {content}")
            elif source == "episodic":
                formatted_memories.append(f"- Past Experience: {content}")
            elif source == "conversation":
                formatted_memories.append(f"- Previous Conversation Summary: {content}")
            else:
                formatted_memories.append(f"- Context: {content}")

        if not formatted_memories:
            conv_logger.log_retrieval_completed(len(chunks), 0)
            return "No relevant memories found."

        conv_logger.log_retrieval_completed(len(chunks), len(formatted_memories))
        return "\n".join(formatted_memories)
