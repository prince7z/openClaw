from typing import List, Set
from app.workflow.graph import ExecutionGraph
from app.workflow.repository.models import SessionStep

class TopologicalScheduler:
    """Decoupled scheduler operating on in-memory ExecutionGraph.
    
    Identifies steps ready for dispatch based on completed upstream dependencies and capability locks.
    """

    @staticmethod
    def get_ready_steps(graph: ExecutionGraph, locked_capabilities: Set[str]) -> List[SessionStep]:
        """Queries the in-memory graph to find steps with no unresolved dependencies or capability locks.
        
        Args:
            graph: The in-memory ExecutionGraph instance.
            locked_capabilities: Set of capability tokens currently occupied by active executions.
            
        Returns:
            List of SessionStep records ready to be dispatched.
        """
        return graph.get_ready_steps(locked_capabilities)
