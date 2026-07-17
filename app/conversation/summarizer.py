"""LLM-based conversation summary and title generator."""

import json
import logging
import asyncio
from typing import Any
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from app.config import (
    OpenRouter_model,
    OpenRouter_api_key,
    openrouter_enable_json_mode,
    summarizer_max_retries,
)
from app.conversation.prompts import MEMORY_EXTRACTION_PROMPT

logger = logging.getLogger("openclaw-agent")


class ConversationSummarizer:
    """Uses the OpenRouter LLM to summarize conversation message logs."""

    def __init__(self, llm: Any | None = None):
        """Initialize the summarizer with a ChatOpenAI instance or a default one."""
        if llm is None:
            kwargs = {
                "model": OpenRouter_model,
                "api_key": OpenRouter_api_key,
                "base_url": "https://openrouter.ai/api/v1",
                "temperature": 0.0,
            }
            if openrouter_enable_json_mode:
                kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}
            self.llm = ChatOpenAI(**kwargs)
        else:
            self.llm = llm

    def _format_history(self, messages: list[Any]) -> str:
        """Format messages list into a structured log text string."""
        history = []
        for msg in messages:
            if msg.type == "human":
                content = (msg.content or "").strip()
                if content:
                    history.append(f"User: {content}")
            elif msg.type == "ai":
                content = (msg.content or "").strip()
                if content:
                    history.append(f"Assistant: {content}")
        return "\n".join(history)

    def _parse_json(self, content: str) -> dict[str, Any] | None:
        """Extract and parse JSON from content, falling back to substring parsing if needed."""
        content = content.strip()
        if not content:
            return None
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1 and end >= start:
            json_str = content[start:end+1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        return None

    async def extract_summary_and_memories(self, messages: list[Any]) -> dict[str, Any]:
        """Extract conversation title/summary, semantic memories, and episodic memories in a single LLM call.

        Args:
            messages: A list of BaseMessage instances.

        Returns:
            A dictionary containing keys "title", "summary", "semantic_memories", and "episodic_memories".
        """
        if not messages:
            return {
                "title": "New Conversation",
                "summary": "No messages were recorded.",
                "semantic_memories": [],
                "episodic_memories": []
            }

        log_text = self._format_history(messages)
        if not log_text:
            return {
                "title": "Empty Conversation",
                "summary": "Conversation messages had no text content.",
                "semantic_memories": [],
                "episodic_memories": []
            }

        prompt = MEMORY_EXTRACTION_PROMPT.format(conversation=log_text)

        max_retries = summarizer_max_retries
        for attempt in range(max_retries):
            try:
                response = await self.llm.ainvoke([HumanMessage(content=prompt)])
                raw_content = response.content

                data = None
                if raw_content:
                    data = self._parse_json(raw_content)

                if not data:
                    raise ValueError(f"Could not parse extraction response as JSON. Raw response: {repr(raw_content)}")

                return {
                    "title": str(data.get("title", "Untitled Conversation")),
                    "summary": str(data.get("summary", "No summary generated.")),
                    "semantic_memories": data.get("semantic_memories") or [],
                    "episodic_memories": data.get("episodic_memories") or []
                }
            except Exception as exc:
                if attempt < max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1} failed to extract memories: {exc}. Retrying in 1.5 seconds...")
                    await asyncio.sleep(1.5)
                else:
                    logger.error(f"Failed to extract summary and memories after {max_retries} attempts: {exc}")
                    return {
                        "title": "Chat Session",
                        "summary": "Archived conversation history.",
                        "semantic_memories": [],
                        "episodic_memories": []
                    }
