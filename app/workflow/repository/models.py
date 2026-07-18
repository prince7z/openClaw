from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import json

class SessionStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class StepStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"

class StepType(str, Enum):
    TOOL = "TOOL"
    REASONER = "REASONER"
    PLANNER = "PLANNER"
    CONDITION = "CONDITION"
    WAIT = "WAIT"
    APPROVAL = "APPROVAL"

@dataclass
class ExecutionSession:
    id: str
    status: SessionStatus
    version: int = 1
    definition_json: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status.value,
            "version": self.version,
            "definition_json": self.definition_json,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

@dataclass
class SessionTask:
    id: str
    session_id: str
    name: str
    status: TaskStatus
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "name": self.name,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

@dataclass
class SessionStep:
    id: str
    task_id: str
    session_id: str
    name: str
    step_type: StepType
    status: StepStatus
    tool_name: Optional[str] = None
    planner_prompt: Optional[str] = None
    reasoner_prompt: Optional[str] = None
    inputs_json: Optional[str] = None      # JSON serialized inputs/params
    metadata_json: Optional[str] = None    # JSON serialized extra options
    resources_json: Optional[str] = None   # JSON serialized list of capabilities needed
    output_key: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 0
    timeout_seconds: float = 0.0
    created_at: str = ""
    updated_at: str = ""

    # Helper properties for unpacked fields
    @property
    def inputs(self) -> Dict[str, Any]:
        try:
            return json.loads(self.inputs_json) if self.inputs_json else {}
        except Exception:
            return {}

    @property
    def metadata(self) -> Dict[str, Any]:
        try:
            return json.loads(self.metadata_json) if self.metadata_json else {}
        except Exception:
            return {}

    @property
    def resources(self) -> List[str]:
        try:
            return json.loads(self.resources_json) if self.resources_json else []
        except Exception:
            return []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "name": self.name,
            "step_type": self.step_type.value,
            "status": self.status.value,
            "tool_name": self.tool_name,
            "planner_prompt": self.planner_prompt,
            "reasoner_prompt": self.reasoner_prompt,
            "inputs_json": self.inputs_json,
            "metadata_json": self.metadata_json,
            "resources_json": self.resources_json,
            "output_key": self.output_key,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
