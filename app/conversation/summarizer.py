"""LLM-based conversation summary and title generator."""

import json
import logging
from typing import Any
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from app.config import OpenRouter_model, OpenRouter_api_key

logger = logging.getLogger("openclaw-agent")


class ConversationSummarizer:
    """Uses the OpenRouter LLM to summarize conversation message logs."""

    def __init__(self, llm: Any | None = None):
        """Initialize the summarizer with a ChatOpenAI instance or a default one."""
        if llm is None:
            self.llm = ChatOpenAI(
                model=OpenRouter_model,
                api_key=OpenRouter_api_key,
                base_url="https://openrouter.ai/api/v1",
                temperature=0.0
            )
        else:
            self.llm = llm

    async def summarize(self, messages: list[Any]) -> dict[str, str]:
        """Summarize conversation message logs into a short title and summary context.

        Args:
            messages: A list of BaseMessage instances.

        Returns:
            A dictionary containing keys "title" and "summary".
        """
        if not messages:
            return {
                "title": "New Conversation",
                "summary": "No messages were recorded."
            }

        # Format message log
        history = []
        for msg in messages:
            role = "User" if msg.type == "human" else "Assistant"
            content = (msg.content or "").strip()
            if content:
                history.append(f"{role}: {content}")

        log_text = "\n".join(history)
        if not log_text:
            return {
                "title": "Empty Conversation",
                "summary": "Conversation messages had no text content."
            }

        prompt = f"""Summarize the following chat conversation history.
Generate a short, concise, and descriptive title (max 6 words) and a brief summary paragraph (max 3 sentences).

Format your output EXACTLY as a JSON object with keys "title" and "summary":
{{"title": "Conversation Title", "summary": "Short paragraph summary"}}

Do NOT include any extra text, code blocks, or explanations. Just return the JSON object.

Conversation history:
{log_text}
"""
        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            
            # Clean Markdown wrapping if the LLM output is wrapped in code blocks
            if content.startswith("```"):
                lines = content.splitlines()
                if lines[0].startswith("```json") or lines[0].startswith("```"):
                    content = "\n".join(lines[1:-1]).strip()
            
            data = json.loads(content)
            return {
                "title": str(data.get("title", "Untitled Conversation")),
                "summary": str(data.get("summary", "No summary generated."))
            }
        except Exception as exc:
            logger.error(f"Failed to generate title and summary: {exc}")
            return {
                "title": "Chat Session",
                "summary": "Archived conversation history."
            }
