import os
import socket
import asyncio
import logging
from typing import Dict, Optional, Literal
from datetime import datetime
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
            session = self._sessions[session_id]
            if session.container_id:
                try:
                    status = await self.docker_manager.status(session.container_id)
                    if status == "running":
                        session.last_accessed_at = datetime.utcnow()
                        return session
                except Exception:
                    pass
            await self.destroy_session(session_id, keep_workspace=True)

        logger.info(f"Creating runtime session: {session_id}...")
        
        # Ensure image is ready
        await self.image_manager.ensure()

        # Allocate host ports for all standard web ports (8000, 3000, 5173, etc.)
        docker_ports, port_mappings = self.network_manager.create_session_port_mappings()
        primary_host_port = port_mappings.get(8000, list(port_mappings.values())[0])

        # Create local workspace directory
        workspace_path = await self.workspace_manager.create(session_id)

        # Spin up container
        container_id = await self.docker_manager.create(
            session_id=session_id,
            workspace_path=str(workspace_path),
            port_mapping=docker_ports
        )

        session = RuntimeSession(
            session_id=session_id,
            workspace=workspace_path,
            container_id=container_id,
            host_port=primary_host_port,
            port_mappings=port_mappings,
            status=RuntimeStatus.RUNNING
        )
        # Store in-memory registry
        self._sessions[session_id] = session
        logger.info(f"Session {session_id} successfully created. Container: {container_id[:12]}. Ports: {port_mappings}.")
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

        session.last_accessed_at = datetime.utcnow()

        workdir = self.config.mount_path
        if cwd:
            workdir = os.path.normpath(os.path.join(self.config.mount_path, cwd)).replace("\\", "/")

        if env:
            env_str = " ".join(f'{k}="{v}"' for k, v in env.items())
            final_cmd = ["bash", "-c", f"{env_str} {command}"]
        else:
            final_cmd = ["bash", "-c", command]

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

    async def get_preview_url(self, session_id: str, port: int = 8000) -> Optional[str]:
        """Start ngrok preview or fetch active preview url for specified container port."""
        session = self._sessions.get(session_id)
        if not session or not session.container_id:
            return None

        # Look up mapped host port for container port
        host_port = session.port_mappings.get(port, session.host_port)
        if not host_port:
            return None

        preview_info = self.preview_manager.info()
        if not preview_info or preview_info.host_port != host_port:
            preview_info = await self.preview_manager.start(host_port)
        
        session.preview = preview_info
        return preview_info.url

    async def wait_for_server_ready(self, session_id: str, port: int = 8000, timeout: int = 60) -> bool:
        """Poll host port until TCP/socket connections succeed, verifying web server readiness."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        host_port = session.port_mappings.get(port, session.host_port)
        if not host_port:
            return False

        loop = asyncio.get_running_loop()
        start_time = loop.time()

        def check_socket():
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1.5)
                    return s.connect_ex(("127.0.0.1", host_port)) == 0
            except Exception:
                return False

        while loop.time() - start_time < timeout:
            is_ready = await loop.run_in_executor(None, check_socket)
            if is_ready:
                await asyncio.sleep(1)  # Buffer to allow app listener initialization
                logger.info(f"[Runtime] Web server on container port {port} (host port {host_port}) verified ready!")
                return True
            await asyncio.sleep(1)

        logger.warning(f"[Runtime] Server readiness polling timed out after {timeout}s on port {port} (host port {host_port})")
        return False

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

    async def cleanup_idle_sessions(self) -> int:
        """Stop container sessions that have exceeded the idle timeout while preserving workspace files on disk."""
        now = datetime.utcnow()
        idle_timeout = self.config.session_idle_timeout
        cleaned = 0

        for session_id, session in list(self._sessions.items()):
            idle_seconds = (now - session.last_accessed_at).total_seconds()
            if idle_seconds > idle_timeout:
                logger.info(f"[Runtime] Session {session_id} idle for {int(idle_seconds)}s (limit: {idle_timeout}s). Cleaning up container while keeping workspace...")
                try:
                    await self.destroy_session(session_id, keep_workspace=True)
                    cleaned += 1
                except Exception as e:
                    logger.error(f"[Runtime] Error cleaning idle session {session_id}: {e}")

        return cleaned
