from dataclasses import dataclass, field
import os

@dataclass
class RuntimeConfig:
    workspace_root: str = field(default_factory=lambda: os.getenv("RUNTIME_WORKSPACE_ROOT", "workspaces"))
    image_name: str = field(default_factory=lambda: os.getenv("RUNTIME_IMAGE_NAME", "aether-runtime").lower())
    image_tag: str = field(default_factory=lambda: os.getenv("RUNTIME_IMAGE_TAG", "a-one").lower())
    mount_path: str = "/workspace"
    memory_limit: str = "4g"
    cpu_limit: float = 2.0
    execution_timeout: int = 300
    startup_timeout: int = 60
    session_idle_timeout: int = 1800  # Keep idle sessions alive for 30 minutes
    preview_provider: str = "ngrok"
    network_mode: str = "bridge"
    python_path: str = "python"
    node_path: str = "node"
    npm_path: str = "npm"
