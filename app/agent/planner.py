import logging
import os
import time

from langchain_core.messages import SystemMessage, ToolMessage, HumanMessage
from langchain_openai import ChatOpenAI
from app.config import OpenRouter_model,OpenRouter_api_key  
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.state import AgentState
from app.tools import tools

logger = logging.getLogger("openclaw-agent")

# Instantiate ChatOpenAI model using configuration or defaults

llm = ChatOpenAI(
        model=OpenRouter_model,
        api_key=OpenRouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=0.0
    )
llm_with_tools = llm.bind_tools(tools)


def analyze_and_log_tokens(messages, response):
    try:
        import tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")
    except Exception:
        encoding = None

    def get_tokens(text: str) -> int:
        if not text:
            return 0
        if encoding:
            return len(encoding.encode(text))
        return len(text) // 4

    system_tokens = 0
    history_tokens = 0

    # Calculate local estimates
    for i, msg in enumerate(messages):
        content_str = ""
        if isinstance(msg.content, str):
            content_str = msg.content
        elif isinstance(msg.content, list):
            content_str = "".join([str(item) for item in msg.content])
        
        tokens = get_tokens(content_str)
        if i == 0 and isinstance(msg, SystemMessage):
            system_tokens += tokens
        else:
            history_tokens += tokens

    # Retrieve exact counts from API metadata if available
    metadata = getattr(response, "response_metadata", {})
    token_usage = metadata.get("token_usage", {})
    api_prompt = token_usage.get("prompt_tokens")
    api_completion = token_usage.get("completion_tokens")
    api_total = token_usage.get("total_tokens")

    logger.info("┌────────────────── 📊 Detailed Token Analysis ──────────────────┐")
    logger.info(f"│  System Prompt Tokens (Est):    {system_tokens:<30} │")
    logger.info(f"│  Message History Tokens (Est):  {history_tokens:<30} │")
    if api_prompt is not None:
        logger.info(f"│  API Reported Prompt Tokens:    {api_prompt:<30} │")
        logger.info(f"│  API Reported Response Tokens:  {api_completion:<30} │")
        logger.info(f"│  API Reported Total Tokens:     {api_total:<30} │")
    else:
        logger.info(f"│  Total Prompt Tokens (Est):     {system_tokens + history_tokens:<30} │")
    logger.info("└────────────────────────────────────────────────────────────────┘")


def log_messages_sent(messages):
    logger.info("┌────────────────── 📤 Messages Sent to LLM ──────────────────┐")
    for i, msg in enumerate(messages):
        role = msg.__class__.__name__.replace("Message", "")
        content = str(msg.content)
        if len(content) > 60:
            content = content[:57] + "..."
        content = content.replace("\n", " ")
        
        extra = ""
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            calls = [f"{tc.get('name')}(...)" for tc in msg.tool_calls]
            extra = f" [Calls: {', '.join(calls)}]"
        elif msg.__class__.__name__ == "ToolMessage":
            tname = getattr(msg, "name", None) or "tool"
            extra = f" [Tool: {tname}]"

        logger.info(f"│  {i+1}. {role:<8}: {content:<60}{extra} │")
    logger.info("└─────────────────────────────────────────────────────────────┘")


def planner(state: AgentState) -> dict:
    """Planner node that prepends the system prompt and sends messages to the LLM.

    Args:
        state: The current state of the agent.

    Returns:
        Updated state dictionary with LLM's response message and optionally final response.
    """
    messages = state.get("messages") or []

    # Find the index of the last HumanMessage in conversation history
    last_human_idx = -1
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], HumanMessage):
            last_human_idx = i
            break

    # Truncate historical ToolMessages (> 500 chars) to first 100 chars
    processed_messages = []
    for i, msg in enumerate(messages):
        if i < last_human_idx and isinstance(msg, ToolMessage) and len(str(msg.content)) > 500:
            truncated_content = str(msg.content)[:100] + "\n...(truncated)"
            truncated_msg = ToolMessage(
                content=truncated_content,
                name=getattr(msg, "name", None),
                tool_call_id=getattr(msg, "tool_call_id", None)
            )
            processed_messages.append(truncated_msg)
        else:
            processed_messages.append(msg)

    # Insert system prompt if not present at the beginning
    if not processed_messages or not isinstance(processed_messages[0], SystemMessage):
        processed_messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(processed_messages)

    log_messages_sent(processed_messages)
    logger.info(f"[llm_request] Calling LLM model: {OpenRouter_model}...")

    start_time = time.time()
    try:
        response = llm_with_tools.invoke(processed_messages)
        print("sent message on call - ",processed_messages)
        duration = time.time() - start_time
        logger.info(f"[time] LLM execution completed in {duration:.3f}s")
        analyze_and_log_tokens(processed_messages, response)
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
