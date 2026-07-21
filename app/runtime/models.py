from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

class RuntimeStatus(str, Enum):
    STARTING = "starting"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"

@dataclass
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str

@dataclass
class ProcessInfo:
    exec_id: str
    command: str
    status: str
    pid: Optional[int] = None
    exit_code: Optional[int] = None

@dataclass
class PreviewInfo:
    url: str
    provider: str
    host_port: int
    started_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class RuntimeSession:
    session_id: str
    workspace: Path
    container_id: Optional[str] = None
    host_port: Optional[int] = None
    port_mappings: Dict[int, int] = field(default_factory=dict)
    status: RuntimeStatus = RuntimeStatus.STOPPED
    process: Optional[ProcessInfo] = None
    preview: Optional[PreviewInfo] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
