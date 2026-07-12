import logging
import os
import time

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from app.config import OpenRouter_model,OpenRouter_api_key  
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.state import AgentState
from app.tools.filesystem import (
    append_file,
    copy,
    create_directory,
    create_file,
    current_directory,
    delete,
    exists,
    find,
    glob,
    list_directory,
    metadata,
    move,
    read_file,
    read_multiple,
    rename,
    search,
    tree,
    write_file,
)
from app.tools.search import web_search
from app.tools.gmail import (
    gmail_search,
    gmail_read,
    gmail_send,
    gmail_reply,
    gmail_download_attachment
)

logger = logging.getLogger("openclaw-agent")

# Define tools list for LLM binding and runner node execution
tools = [
    web_search,
    gmail_search,
    gmail_read,
    gmail_send,
    gmail_reply,
    gmail_download_attachment,
    append_file,
    copy,
    create_directory,
    create_file,
    current_directory,
    delete,
    exists,
    find,
    glob,
    list_directory,
    metadata,
    move,
    read_file,
    read_multiple,
    rename,
    search,
    tree,
    write_file,
    
]

# Instantiate ChatOpenAI model using configuration or defaults

llm = ChatOpenAI(
        model=OpenRouter_model,
        api_key=OpenRouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=0.0
    )
llm_with_tools = llm.bind_tools(tools)


def planner(state: AgentState) -> dict:
    """Planner node that prepends the system prompt and sends messages to the LLM.

    Args:
        state: The current state of the agent.

    Returns:
        Updated state dictionary with LLM's response message and optionally final response.
    """
    messages = state.get("messages") or []

    # Insert system prompt if not present at the beginning
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)

    logger.info(f"[llm_request] Calling LLM model: {OpenRouter_model}...")

    start_time = time.time()
    try:
        response = llm_with_tools.invoke(messages)
        duration = time.time() - start_time
        logger.info(f"[time] LLM execution completed in {duration:.3f}s")
    except Exception as exc:
        logger.error(f"[error] LLM request execution failed: {exc}")
        raise exc

    updates = {
        "messages": [response]
    }

    # If the response does not trigger any tools, it is the final response
    if not hasattr(response, "tool_calls") or not response.tool_calls:
        updates["final_response"] = response.content

    return updates
