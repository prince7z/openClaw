import shutil
import logging
from pathlib import Path
from app.runtime.exceptions import WorkspaceError
from app.runtime.config import RuntimeConfig

logger = logging.getLogger("openclaw-agent")

class WorkspaceManager:
    def __init__(self, config: RuntimeConfig):
        self.config = config
        self.base_dir = Path(self.config.workspace_root).resolve()

    async def create(self, session_id: str) -> Path:
        """Create a workspace directory for the session."""
        try:
            workspace_path = self.base_dir / session_id
            logger.info(f"[Workspace] Creating workspace directory for session {session_id} at {workspace_path}")
            workspace_path.mkdir(parents=True, exist_ok=True)
            return workspace_path
        except Exception as e:
            logger.error(f"[Workspace] Failed to create workspace for session {session_id}: {e}")
            raise WorkspaceError(f"Failed to create workspace directory: {e}")

    async def cleanup(self, session_id: str) -> None:
        """Delete the workspace directory for the session."""
        try:
            workspace_path = self.base_dir / session_id
            if workspace_path.exists():
                logger.info(f"[Workspace] Cleaning up workspace directory for session {session_id} at {workspace_path}")
                import asyncio
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, shutil.rmtree, workspace_path)
        except Exception as e:
            logger.error(f"[Workspace] Failed to clean up workspace for session {session_id}: {e}")
            raise WorkspaceError(f"Failed to delete workspace directory: {e}")

    def resolve(self, session_id: str, relative_path: str = "") -> Path:
        """Resolve and validate a relative path within the session's workspace."""
        workspace_path = self.base_dir / session_id
        resolved = (workspace_path / relative_path).resolve()
        if not str(resolved).startswith(str(workspace_path)):
            logger.warning(f"[Workspace] Blocked path traversal attempt in session {session_id}: {relative_path}")
            raise WorkspaceError("Directory traversal attempt blocked.")
        return resolved

    def exists(self, session_id: str, relative_path: str = "") -> bool:
        """Check if a path exists within the session's workspace."""
        try:
            resolved = self.resolve(session_id, relative_path)
            return resolved.exists()
        except WorkspaceError:
            return False
