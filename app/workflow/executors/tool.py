import asyncio
import logging
from typing import Any, Dict

from app.workflow.executors.base import BaseExecutor
from app.workflow.context.registry import ToolRegistry

logger = logging.getLogger("openclaw-workflow-toolexecutor")

class ToolExecutor(BaseExecutor):
    """Executor for TOOL type steps.
    
    Dynamically loads from ToolRegistry and executes with resolved variables.
    """
    async def execute(self, variables: Dict[str, Any]) -> Any:
        tool_name = self.step.tool_name
        if not tool_name:
            raise ValueError(f"Step '{self.step.id}' specifies no tool_name.")

        tool_obj = ToolRegistry.get_tool(tool_name)
        if not tool_obj:
            raise ValueError(f"Tool '{tool_name}' not registered in registry.")

        resolved_inputs = self.resolve_inputs(variables)
        logger.info(f"Executing tool '{tool_name}' with resolved inputs: {resolved_inputs}")

        try:
            result = await tool_obj.ainvoke(resolved_inputs)
            logger.info(f"Tool '{tool_name}' executed successfully.")
            return result
        except Exception as exc:
            logger.error(f"Error executing tool '{tool_name}': {exc}")
            raise exc
