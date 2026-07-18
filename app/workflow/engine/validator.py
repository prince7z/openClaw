from typing import List, Dict, Set, Tuple
import logging

from app.workflow.graph import ExecutionGraph
from app.workflow.repository.models import StepType
from app.workflow.context.registry import ToolRegistry

logger = logging.getLogger("openclaw-workflow-validator")

class ValidationError(ValueError):
    """Raised when workflow validation detects architectural or graph flaws."""
    pass

class GraphValidator:
    """Validates structural layout, schema compliance, and dependency cycles in ExecutionGraph."""

    @staticmethod
    def validate(graph: ExecutionGraph) -> None:
        """Runs cycle detection, missing dependency checks, and tool validations on the graph.
        
        Raises:
            ValidationError: If any structural validation check fails.
        """
        if not graph.nodes:
            return  # Empty graphs are technically valid / terminal

        # 1. Check for missing dependencies
        for step_id, parent_ids in graph.dependencies.items():
            for parent_id in parent_ids:
                if parent_id not in graph.nodes:
                    raise ValidationError(
                        f"Step '{step_id}' depends on missing step ID '{parent_id}'."
                    )

        # 2. Cycle detection (DFS with coloring)
        # States: 0 = unvisited, 1 = visiting (on current path), 2 = visited
        visited: Dict[str, int] = {node_id: 0 for node_id in graph.nodes}

        def has_cycle(node_id: str) -> bool:
            visited[node_id] = 1  # visiting
            # Check all children (nodes that depend on the current node)
            # Or traverse via parent dependencies.
            # Usually: A depends on B. So B runs first, then A. Edge is B -> A.
            # Let's traverse along graph.edges (which has parent -> child mappings).
            for child_id in graph.edges.get(node_id, []):
                state = visited.get(child_id, 0)
                if state == 1:
                    return True  # Found back-edge (cycle!)
                elif state == 0:
                    if has_cycle(child_id):
                        return True
            visited[node_id] = 2  # visited
            return False

        for node_id in graph.nodes:
            if visited[node_id] == 0:
                if has_cycle(node_id):
                    raise ValidationError(
                        f"Dependency cycle detected originating from or passing through step '{node_id}'."
                    )

        # 3. Tool registry validation
        for step_id, step in graph.nodes.items():
            if step.step_type == StepType.TOOL:
                if not step.tool_name:
                    raise ValidationError(
                        f"Step '{step_id}' ({step.name}) is marked as TOOL but specifies no tool_name."
                    )
                tool_meta = ToolRegistry.get_tool(step.tool_name)
                if not tool_meta:
                    raise ValidationError(
                        f"Step '{step_id}' ({step.name}) references unregistered tool '{step.tool_name}'."
                    )
                # Verify that required inputs are provided in step config (except variables resolved at runtime)
                # This check can be basic for V1: check that inputs is a dict.
                if not isinstance(step.inputs, dict):
                    raise ValidationError(
                        f"Step '{step_id}' ({step.name}) has invalid inputs schema (must be dictionary)."
                    )

        logger.info(f"Successfully validated ExecutionGraph with {len(graph.nodes)} steps.")
