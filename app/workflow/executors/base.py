import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from app.workflow.repository.models import SessionStep

class BaseExecutor(ABC):
    """Abstract Base Class for all workflow step executors.
    
    Provides standard capabilities for resolving step input references from the variables store.
    """
    def __init__(self, step: SessionStep, session_id: str):
        self.step: SessionStep = step
        self.session_id: str = session_id

    @abstractmethod
    async def execute(self, variables: Dict[str, Any]) -> Any:
        """Executes the step logic, utilizing resolved variables.
        
        Args:
            variables: Read-only dictionary of current variables in the session.
            
        Returns:
            The raw output of the step.
        """
        pass

    def resolve_inputs(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Resolves template references like ${variable_name} inside inputs config."""
        inputs = self.step.inputs
        return self._resolve_value(inputs, variables)

    def _resolve_value(self, val: Any, variables: Dict[str, Any]) -> Any:
        """Recursively parses templates or direct references in nested dicts, lists, and strings."""
        if isinstance(val, str):
            # Check if it is a pure variable reference, e.g. "${variable_name}"
            # This preserves original types (like ints, lists, dicts) stored in variables
            exact_match = re.match(r'^\$\{(\w+)\}$', val)
            if exact_match:
                var_name = exact_match.group(1)
                return variables.get(var_name)
            
            # String interpolation
            def replace_match(match):
                var_name = match.group(1)
                return str(variables.get(var_name, ''))
            return re.sub(r'\$\{(\w+)\}', replace_match, val)
            
        elif isinstance(val, dict):
            return {k: self._resolve_value(v, variables) for k, v in val.items()}
        elif isinstance(val, list):
            return [self._resolve_value(item, variables) for item in val]
            
        return val
