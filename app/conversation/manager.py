"""Conversation lifecycle manager (Stateless Graph persistence wrapper)."""

import time
import uuid
import logging
from datetime import datetime
from typing import Any
from langchain_core.messages import HumanMessage

from app.agent.state import AgentState
from app.conversation.serializer import StateSerializer, JSONStateSerializer
from app.conversation.summarizer import ConversationSummarizer
from app.conversation import logger as conv_logger
from app.database.sqlite import repository

logger = logging.getLogger("openclaw-agent")


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

    async def load(self, chat_id: int) -> AgentState:
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
            new_state: AgentState = {
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

    async def save(self, chat_id: int, state: AgentState) -> None:
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

    async def append_user_message(self, chat_id: int, message: HumanMessage) -> AgentState:
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

        # 1. Generate title and summary context via the summarizer
        summary_result = await self.summarizer.summarize(messages)
        title = summary_result.get("title") or "Chat Session"
        summary = summary_result.get("summary") or "Archived conversation history."

        # 2. Extract starting timestamp from state, falling back to db creation date
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

        # 3. Commit the transaction (archive and delete active context)
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
