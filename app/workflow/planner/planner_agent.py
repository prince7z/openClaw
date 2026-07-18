import json
import logging
import re
from typing import Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage
from app.agent.planner import llm
from app.workflow.context.registry import ToolRegistry
from app.workflow.planner.prompts import PLANNER_SYSTEM_PROMPT

logger = logging.getLogger("openclaw-workflow-planner-agent")

class WorkflowPlannerAgent:
    """Invokes LLM to construct a structured Workflow Definition from natural language requests."""

    @staticmethod
    async def plan_workflow(user_goal: str) -> Dict[str, Any]:
        # 1. Format tool registry metadata
        tools = ToolRegistry.list_tools()
        tools_summary = []
        for t in tools:
            tools_summary.append(
                f"- Name: {t.name}\n"
                f"  Description: {t.description}\n"
                f"  Input Schema: {json.dumps(t.input_schema)}\n"
                f"  Required Locks: {t.resources}\n"
            )
        tools_metadata_str = "\n".join(tools_summary)

        # 2. Setup prompt and message history
        system_content = PLANNER_SYSTEM_PROMPT.format(tools_metadata=tools_metadata_str)
        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=f"Generate a workflow definition for: {user_goal}")
        ]

        logger.info("Calling LLM to generate workflow definition...")
        response = await llm.ainvoke(messages)
        content = response.content.strip()

        # 3. Clean LLM markdown code blocks if present
        clean_content = content
        if content.startswith("```"):
            # Strip code fences like ```json ... ```
            match = re.match(r"^```(?:json)?\n(.*?)\n```$", content, re.DOTALL)
            if match:
                clean_content = match.group(1).strip()
            else:
                clean_content = re.sub(r"^```(?:json)?|```$", "", content).strip()

        try:
            workflow_dict = json.loads(clean_content)
            logger.info(f"Successfully generated workflow definition: {workflow_dict.get('name')}")
            return workflow_dict
        except Exception as exc:
            logger.error(f"Failed to parse LLM workflow content as JSON. Content:\n{content}")
            raise ValueError(f"Planner LLM did not return valid JSON: {exc}")
