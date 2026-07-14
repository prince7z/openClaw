import logging
import time
from typing import Literal

from langchain_core.messages import ToolMessage
from langgraph.graph import START, StateGraph

from app.agent.planner import planner, tools
from app.agent.state import AgentState

logger = logging.getLogger("Agent-Aether")
tool_map = {t.name: t for t in tools}


def call_tool(state: AgentState) -> dict:
    """Executes the requested tool calls from the LLM, timing and logging each."""
    tool_messages = []
    tool_outputs = state.get("tool_outputs") or []
    last_message = state["messages"][-1]

    for tool_call in last_message.tool_calls:
        tool_name, tool_args, tool_id = tool_call["name"], tool_call["args"], tool_call["id"]
        logger.info(f"[tool_exec] Executing tool: [bold yellow]{tool_name}[/] with args: {tool_args}")

        tool_obj = tool_map.get(tool_name)
        start_time = time.time()

        if not tool_obj:
            output = f"Error: Tool '{tool_name}' not found."
            logger.error(f"[error] Tool '{tool_name}' not found in registry.")
        else:
            try:
                result = tool_obj.invoke(tool_args)
                output = str(result)
                logger.info(f"Tool Output: {output[:500]}... (truncated)" if len(output) > 500 else f"Tool Output: {output}")
            except Exception as exc:
                output = f"Error: {exc}"
                logger.error(f"[error] Exception during execution of '{tool_name}': {exc}")

        duration = time.time() - start_time
        tool_outputs.append({
            "tool": tool_name,
            "args": tool_args,
            "output": output,
            "execution_time": duration
        })
        tool_messages.append(ToolMessage(content=output, name=tool_name, tool_call_id=tool_id))

    return {"messages": tool_messages, "tool_outputs": tool_outputs}


def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    """Conditional edge checking whether tool execution is required."""
    messages = state.get("messages") or []
    return "tools" if messages and getattr(messages[-1], "tool_calls", None) else "__end__"


# Build the state graph workflow
workflow = StateGraph(AgentState)
workflow.add_node("planner", planner)
workflow.add_node("tools", call_tool)

workflow.add_edge(START, "planner")
workflow.add_conditional_edges("planner", should_continue)
workflow.add_edge("tools", "planner")

graph = workflow.compile()

