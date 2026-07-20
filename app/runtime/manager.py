import os
import asyncio
import logging
from typing import Dict, Optional, Literal
from app.runtime.config import RuntimeConfig
from app.runtime.exceptions import ContainerError, WorkspaceError, OpenClawRuntimeError
from app.runtime.models import RuntimeSession, RuntimeStatus, CommandResult, ProcessInfo, PreviewInfo
from app.runtime.workspace.manager import WorkspaceManager
from app.runtime.docker.network import DockerNetworkManager
from app.runtime.docker.image import DockerImageManager
from app.runtime.docker.manager import DockerManager
from app.runtime.process.manager import ProcessManager
from app.runtime.preview.manager import PreviewManager

logger = logging.getLogger("openclaw-agent")

_instance: Optional['RuntimeManager'] = None

class RuntimeManager:
    @classmethod
    def get_instance(cls) -> 'RuntimeManager':
        global _instance
        if _instance is None:
            _instance = cls()
        return _instance

    def __init__(
        self,
        config: Optional[RuntimeConfig] = None,
        workspace_manager: Optional[WorkspaceManager] = None,
        network_manager: Optional[DockerNetworkManager] = None,
        image_manager: Optional[DockerImageManager] = None,
        docker_manager: Optional[DockerManager] = None,
        process_manager: Optional[ProcessManager] = None,
        preview_manager: Optional[PreviewManager] = None
    ):
        self.config = config or RuntimeConfig()
        
        # Inject dependencies or instantiate defaults
        self.workspace_manager = workspace_manager or WorkspaceManager(self.config)
        self.network_manager = network_manager or DockerNetworkManager()
        
        # Set up Docker objects
        self.docker_manager = docker_manager or DockerManager(self.config)
        self.image_manager = image_manager or DockerImageManager(self.docker_manager.client, self.config)
        
        # Process and preview management
        self.process_manager = process_manager or ProcessManager()
        self.preview_manager = preview_manager or PreviewManager()

        # In-memory session registry
        self._sessions: Dict[str, RuntimeSession] = {}

    async def initialize(self) -> None:
        """Initialize system prerequisites. Prebuilds runtime images and cleans up dangling sessions."""
        logger.info("Initializing RuntimeManager...")
        await self.image_manager.ensure()

        # Auto cleanup dangling container sessions matching naming convention
        try:
            loop = asyncio.get_running_loop()
            def clean_dangling():
                client = self.docker_manager.client
                containers = client.containers.list(all=True, filters={"name": "openclaw-session-"})
                for c in containers:
                    logger.info(f"Cleaning up dangling session container: {c.name}")
                    c.remove(force=True)
            await loop.run_in_executor(None, clean_dangling)
        except Exception as e:
            logger.warning(f"Failed to clean dangling containers during startup: {e}")

    async def shutdown(self) -> None:
        """Gracefully close all session containers, server processes, and preview tunnels."""
        logger.info("Shutting down RuntimeManager...")
        session_ids = list(self._sessions.keys())
        for session_id in session_ids:
            try:
                await self.destroy_session(session_id, keep_workspace=True)
            except Exception as e:
                logger.error(f"Error tearing down session {session_id} on shutdown: {e}")

    async def create_session(self, session_id: str) -> RuntimeSession:
        """Initialize directory, allocate port, and start the sandbox container."""
        if session_id in self._sessions:
            return self._sessions[session_id]

        logger.info(f"Creating runtime session: {session_id}...")
        
        # Ensure image is ready
        await self.image_manager.ensure()

        # Allocate host port
        host_port = self.network_manager.allocate_port()

        # Create local workspace directory
        workspace_path = await self.workspace_manager.create(session_id)

        # Get port specification
        port_mapping = self.network_manager.create_port_mapping(
            host_port=host_port,
            container_port=8000  # Default server port in config or 8000
        )

        # Spin up container
        container_id = await self.docker_manager.create(
            session_id=session_id,
            workspace_path=str(workspace_path),
            port_mapping=port_mapping
        )

        session = RuntimeSession(
            session_id=session_id,
            workspace=workspace_path,
            container_id=container_id,
            host_port=host_port,
            status=RuntimeStatus.RUNNING
        )
        # Store in-memory registry
        self._sessions[session_id] = session
        logger.info(f"Session {session_id} successfully created. Container: {container_id[:12]}. Port: {host_port}.")
        return session

    async def destroy_session(self, session_id: str, keep_workspace: bool = True) -> None:
        """Tear down container, kill background processes, close tunnels, and release port."""
        session = self._sessions.get(session_id)
        if not session:
            return

        logger.info(f"Destroying runtime session: {session_id}...")

        # Stop preview tunnel
        await self.preview_manager.stop()

        # Stop processes running inside container
        if session.container_id and session.process:
            try:
                # Find container port mapped to host_port or 8000
                await self.process_manager.stop(self.docker_manager, session.container_id, port=8000)
            except Exception:
                pass

        # Destroy Docker container
        if session.container_id:
            try:
                await self.docker_manager.destroy(session.container_id)
            except Exception:
                pass

        # Cleanup workspace files if configured
        if not keep_workspace:
            try:
                await self.workspace_manager.cleanup(session_id)
            except Exception:
                pass

        # Remove from registry
        self._sessions.pop(session_id, None)
        logger.info(f"Session {session_id} destroyed.")

    async def execute(
        self,
        session_id: str,
        command: str,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> CommandResult:
        """Unified primitive to execute a command inside the session container."""
        session = self._sessions.get(session_id)
        if not session or not session.container_id:
            raise ContainerError(f"No active container session found for ID: {session_id}")

        workdir = self.config.mount_path
        if cwd:
            workdir = os.path.normpath(os.path.join(self.config.mount_path, cwd)).replace("\\", "/")

        final_cmd = command
        if env:
            env_str = " ".join(f'{k}="{v}"' for k, v in env.items())
            final_cmd = f"sh -c '{env_str} {command}'"

        return await self.docker_manager.exec(
            container_id=session.container_id,
            cmd=final_cmd,
            workdir=workdir,
            timeout=timeout or self.config.execution_timeout
        )

    async def run_python(self, session_id: str, code: str, cwd: Optional[str] = None) -> CommandResult:
        """Run Python code inside the container."""
        # Wrap code string
        cmd = f"{self.config.python_path} -c {repr(code)}"
        return await self.execute(session_id, cmd, cwd=cwd)

    async def run_node(self, session_id: str, code: str, cwd: Optional[str] = None) -> CommandResult:
        """Run Node.js code inside the container."""
        cmd = f"{self.config.node_path} -e {repr(code)}"
        return await self.execute(session_id, cmd, cwd=cwd)

    async def start_server(self, session_id: str, command: str, port: int) -> None:
        """Start a detached server background process inside the container."""
        session = self._sessions.get(session_id)
        if not session or not session.container_id:
            raise ContainerError(f"No active container session found for ID: {session_id}")

        exec_id = await self.process_manager.start(
            docker_manager=self.docker_manager,
            container_id=session.container_id,
            command=command
        )
        
        # Set process info in session
        session.process = ProcessInfo(
            exec_id=exec_id,
            command=command,
            status="running"
        )

    async def stop_server(self, session_id: str, port: int) -> None:
        """Stop any active server process listening on the container port."""
        session = self._sessions.get(session_id)
        if not session or not session.container_id:
            return

        await self.process_manager.stop(self.docker_manager, session.container_id, port)
        session.process = None

    async def get_preview_url(self, session_id: str) -> Optional[str]:
        """Start ngrok preview or fetch active preview url."""
        session = self._sessions.get(session_id)
        if not session or not session.container_id:
            return None

        # Find allocated host port mapping
        client = self.docker_manager.client
        container_name = f"openclaw-session-{session_id}"
        try:
            container = client.containers.get(container_name)
            ports = container.ports or {}
            # Find bound host port for 8000/tcp
            host_bindings = ports.get("8000/tcp")
            if not host_bindings:
                return None
            host_port = int(host_bindings[0]["HostPort"])
        except Exception:
            return None

        preview_info = self.preview_manager.info()
        if not preview_info:
            preview_info = await self.preview_manager.start(host_port)
        
        session.preview = preview_info
        return preview_info.url

    async def status(self, session_id: str) -> RuntimeSession:
        """Poll container and background process status details."""
        session = self._sessions.get(session_id)
        if not session:
            return RuntimeSession(session_id=session_id, workspace=None, status=RuntimeStatus.STOPPED)

        if session.container_id:
            try:
                container_status = await self.docker_manager.status(session.container_id)
                if container_status == "running":
                    session.status = RuntimeStatus.RUNNING
                else:
                    session.status = RuntimeStatus.STOPPED
            except Exception:
                session.status = RuntimeStatus.ERROR

            if session.process and session.process.exec_id:
                try:
                    session.process = await self.process_manager.status(self.docker_manager, session.process.exec_id)
                except Exception:
                    pass

        # Sync preview url details
        session.preview = self.preview_manager.info()
        return session
