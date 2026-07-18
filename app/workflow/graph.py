from typing import Dict, List, Set, Any, Optional
from app.workflow.repository.models import SessionStep, StepStatus

class ExecutionGraph:
    """In-memory representation of the workflow execution step graph.
    
    Responsible for tracking nodes, building adjacency lists, calculating in-degrees,
    handling graph mutations, and identifying ready steps.
    """
    def __init__(self, session_id: str, version: int = 1):
        self.session_id: str = session_id
        self.version: int = version
        self.nodes: Dict[str, SessionStep] = {}
        # Maps step_id -> list of downstream step_ids
        self.edges: Dict[str, List[str]] = {}
        # Maps step_id -> set of parent step_ids it depends on
        self.dependencies: Dict[str, Set[str]] = {}
        # In-degree of each node (number of uncompleted/unskipped parents)
        self.in_degrees: Dict[str, int] = {}

    def add_node(self, step: SessionStep):
        self.nodes[step.id] = step
        if step.id not in self.edges:
            self.edges[step.id] = []
        if step.id not in self.dependencies:
            self.dependencies[step.id] = set()

    def add_dependency(self, step_id: str, depends_on_step_id: str):
        if step_id not in self.dependencies:
            self.dependencies[step_id] = set()
        self.dependencies[step_id].add(depends_on_step_id)

    def build(self):
        """Calculates adjacency lists (edges) and in-degrees based on active nodes and dependencies."""
        self.edges = {node_id: [] for node_id in self.nodes}
        self.in_degrees = {node_id: 0 for node_id in self.nodes}
        
        # Populate edges (parent -> child)
        for child_id, parents in self.dependencies.items():
            if child_id not in self.nodes:
                continue
            for parent_id in parents:
                if parent_id in self.nodes:
                    self.edges[parent_id].append(child_id)
        
        # Calculate initial in-degrees based on uncompleted/unskipped parents
        for child_id, parents in self.dependencies.items():
            if child_id not in self.nodes:
                continue
            uncompleted_parents = 0
            for parent_id in parents:
                if parent_id in self.nodes:
                    parent_status = self.nodes[parent_id].status
                    if parent_status not in (StepStatus.COMPLETED, StepStatus.SKIPPED):
                        uncompleted_parents += 1
            self.in_degrees[child_id] = uncompleted_parents

    def get_ready_steps(self, locked_capabilities: Set[str]) -> List[SessionStep]:
        """Finds all steps in PENDING state that have 0 uncompleted dependencies and no capability conflicts.
        
        Args:
            locked_capabilities: Set of capabilities currently locked by running steps.
            
        Returns:
            A list of SessionStep instances ready to execute.
        """
        ready_steps = []
        for step_id, step in self.nodes.items():
            if step.status == StepStatus.PENDING:
                # Check if dependencies are resolved
                if self.in_degrees.get(step_id, 0) == 0:
                    # Check capability lock conflicts
                    step_resources = step.resources
                    has_conflict = any(res in locked_capabilities for res in step_resources)
                    if not has_conflict:
                        ready_steps.append(step)
        return ready_steps

    def update_step_status(self, step_id: str, status: StepStatus):
        """Updates a step status and dynamically adjusts downstream in-degrees if completed/skipped."""
        if step_id not in self.nodes:
            return
        
        old_status = self.nodes[step_id].status
        self.nodes[step_id].status = status
        
        # Transition to completed/skipped unlocks downstream
        old_is_terminal = old_status in (StepStatus.COMPLETED, StepStatus.SKIPPED)
        new_is_terminal = status in (StepStatus.COMPLETED, StepStatus.SKIPPED)
        
        if not old_is_terminal and new_is_terminal:
            for child_id in self.edges.get(step_id, []):
                if child_id in self.in_degrees:
                    self.in_degrees[child_id] = max(0, self.in_degrees[child_id] - 1)
        # If transitioning away from terminal (e.g. on retry FAILED -> READY/RUNNING)
        elif old_is_terminal and not new_is_terminal:
            for child_id in self.edges.get(step_id, []):
                if child_id in self.in_degrees:
                    self.in_degrees[child_id] += 1

    def is_terminal(self) -> bool:
        """Returns True if the entire graph has reached a terminal execution state."""
        if not self.nodes:
            return True
        for step in self.nodes.values():
            if step.status not in (StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED):
                return False
        return True
