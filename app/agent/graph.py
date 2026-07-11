import logging
import time
from typing import Literal

from langchain_core.messages import ToolMessage
from langgraph.graph import END, START, StateGraph

from app.agent.planner import planner, tools
from app.agent.state import AgentState

logger = logging.getLogger("openclaw-agent")


def call_tool(state: AgentState) -> dict:
    """Executes the requested tool calls from the LLM, timing and logging each.

    Args:
        state: The current agent state.

    Returns:
        Updated state dictionary with tool response messages and tracking info.
    """
    messages = state.get("messages") or []
    last_message = messages[-1]

    tool_messages = []
    tool_outputs = state.get("tool_outputs") or []

    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return {"messages": [], "tool_outputs": tool_outputs}

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]

        logger.info(f"[tool_exec] Executing tool: [bold yellow]{tool_name}[/]")
        logger.info(f"[tool_exec] Arguments: {tool_args}")

        # Locate tool object in the defined filesystem tools list
        tool_obj = next((t for t in tools if t.name == tool_name), None)

        start_time = time.time()
        if tool_obj is None:
            output = f"Error: Tool '{tool_name}' not found."
            duration = time.time() - start_time
            logger.error(f"[error] Tool '{tool_name}' not found in registry.")
        else:
            try:
                result = tool_obj.invoke(tool_args)
                duration = time.time() - start_time
                output = str(result)
                logger.info(f"[time] Tool execution completed in {duration:.3f}s")
                # Truncate output logging for very large files to keep logs concise
                if len(output) > 500:
                    logger.info(f"Tool Output: {output[:500]}... (truncated {len(output)-500} chars)")
                else:
                    logger.info(f"Tool Output: {output}")
            except Exception as exc:
                duration = time.time() - start_time
                output = f"Error: {exc}"
                logger.error(f"[error] Exception during execution of tool '{tool_name}': {exc}")

        # Store structured tool execution logs in agent state
        tool_outputs.append({
            "tool": tool_name,
            "args": tool_args,
            "output": output,
            "execution_time": duration
        })

        # Append LangChain core ToolMessage
        tool_messages.append(
            ToolMessage(
                content=output,
                name=tool_name,
                tool_call_id=tool_id
            )
        )

    return {
        "messages": tool_messages,
        "tool_outputs": tool_outputs
    }


def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    """Conditional edge checking whether tool execution is required.

    Args:
        state: The current agent state.

    Returns:
        The name of the next node ("tools" or "__end__").
    """
    messages = state.get("messages") or []
    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "__end__"


# Define the workflow StateGraph
workflow = StateGraph(AgentState)

# Add Planner and Tool executor nodes
workflow.add_node("planner", planner)
workflow.add_node("tools", call_tool)

# Set starting point of the graph
workflow.add_edge(START, "planner")

# Add conditional execution loop edge
workflow.add_conditional_edges("planner", should_continue)

# Add return path from Tool runner node to Planner node
workflow.add_edge("tools", "planner")

# Compile state graph workflow
graph = workflow.compile()
