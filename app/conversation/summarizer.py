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

        # Format message log (only human and AI messages to keep context low and relevant)
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
            raw_content = response.content
           
            def extract_and_parse_json(content: str) -> dict[str, Any] | None:
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

            data = None
            if raw_content:
                data = extract_and_parse_json(raw_content)

            if not data:
                raise ValueError(f"Could not parse response content as JSON. Raw response: {repr(raw_content)}")

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
