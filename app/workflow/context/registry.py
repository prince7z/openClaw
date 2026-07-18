from typing import Any, Dict, List, Optional, Callable
import logging
import asyncio

from app.tools import get_tools

logger = logging.getLogger("openclaw-workflow-registry")

class WorkflowTool:
    """Standardized wrapper for execution tools inside the workflow engine.
    
    Adheres to capabilities locking, input/output validating, and custom retries/timeouts.
    """
    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        callable_fn: Callable,
        resources: Optional[List[str]] = None,
        timeout: float = 30.0,
        retryable: bool = True,
        output_schema: Optional[Dict[str, Any]] = None
    ):
        self.name: str = name
        self.description: str = description
        self.input_schema: Dict[str, Any] = input_schema
        self.output_schema: Dict[str, Any] = output_schema or {"type": "string"}
        self.callable: Callable = callable_fn
        self.resources: List[str] = resources or []
        self.timeout: float = timeout
        self.retryable: bool = retryable

    def invoke(self, inputs: Dict[str, Any]) -> Any:
        """Invokes the underlying tool synchronously."""
        if hasattr(self.callable, "invoke"):
            return self.callable.invoke(inputs)
        # Fallback to direct function call
        if isinstance(inputs, dict):
            return self.callable(**inputs)
        return self.callable(inputs)

    async def ainvoke(self, inputs: Dict[str, Any]) -> Any:
        """Invokes the underlying tool asynchronously, offloading to threads if synchronous."""
        if hasattr(self.callable, "ainvoke"):
            try:
                return await self.callable.ainvoke(inputs)
            except NotImplementedError:
                # If ainvoke raises NotImplementedError (e.g. custom langchain tool without async definition)
                pass
        
        if asyncio.iscoroutinefunction(self.callable):
            if isinstance(inputs, dict):
                return await self.callable(**inputs)
            return await self.callable(inputs)
            
        return await asyncio.to_thread(self.invoke, inputs)


class ToolRegistry:
    """Manages the registration and capability mapping of OpenClaw tools."""
    
    _registry: Dict[str, WorkflowTool] = {}

    @classmethod
    def initialize(cls) -> None:
        """Loads tools from OpenClaw's primary registry and wraps them with workflow metadata."""
        if cls._registry:
            return  # Already initialized

        registered_tools = get_tools()
        for t in registered_tools:
            # Determine locked capabilities based on tool classification
            name = t.name
            resources = []
            if name.startswith("browser_"):
                resources.append("browser.default")
            elif name in ("read_file", "write_file", "manage_file", "list_files", "search_files"):
                resources.append("filesystem.workspace")
            elif name.startswith("gmail_"):
                resources.append("gmail.default")
            elif name in ("list_calendar", "manage_event", "manage_task", "calendar_free_busy") or name.startswith("calendar_"):
                resources.append("calendar.default")
            elif name == "retrieve_memory":
                resources.append("memory.default")

            # Extract arguments schema
            input_schema = {}
            if hasattr(t, "args"):
                input_schema = t.args
            elif hasattr(t, "args_schema") and t.args_schema:
                input_schema = t.args_schema.schema().get("properties", {})

            # Default timeout configuration
            timeout = 30.0
            if name.startswith("browser_"):
                timeout = 60.0  # Browser automation can take longer
            elif name == "web_search":
                timeout = 15.0

            workflow_tool = WorkflowTool(
                name=name,
                description=t.description,
                input_schema=input_schema,
                callable_fn=t, # Pass tool object directly
                resources=resources,
                timeout=timeout,
                retryable=True
            )
            cls._registry[name] = workflow_tool
            logger.debug(f"Registered workflow tool: {name} (Resources: {resources})")

    @classmethod
    def get_tool(cls, name: str) -> Optional[WorkflowTool]:
        """Fetches a wrapped tool from the registry. Initializes if empty."""
        if not cls._registry:
            cls.initialize()
        return cls._registry.get(name)

    @classmethod
    def list_tools(cls) -> List[WorkflowTool]:
        """Lists all registered tools with their metadata summaries."""
        if not cls._registry:
            cls.initialize()
        return list(cls._registry.values())
