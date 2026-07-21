import os
import asyncio
import logging
from typing import AsyncGenerator, Dict
import docker
from app.runtime.config import RuntimeConfig
from app.runtime.exceptions import ContainerError
from app.runtime.models import CommandResult

logger = logging.getLogger("openclaw-agent")

class DockerManager:
    def __init__(self, config: RuntimeConfig):
        self.config = config
        self._client = None

    @property
    def client(self) -> docker.DockerClient:
        if self._client is None:
            self._client = docker.from_env()
        return self._client

    async def create(self, session_id: str, workspace_path: str, port_mapping: Dict[str, int]) -> str:
        """Create and start a Docker container mapping workspace and ports."""
        container_name = f"openclaw-session-{session_id}"
        image_tag = f"{self.config.image_name}:{self.config.image_tag}"
        abs_workspace_path = os.path.abspath(workspace_path)
        loop = asyncio.get_running_loop()

        def do_create():
            try:
                existing = self.client.containers.get(container_name)
                logger.info(f"[Docker] Removing pre-existing container for session {session_id}")
                existing.remove(force=True)
            except docker.errors.NotFound:
                pass

            logger.info(f"[Docker] Launching container '{container_name}' (port mapping: {port_mapping})")
            container = self.client.containers.run(
                image=image_tag,
                name=container_name,
                command="tail -f /dev/null",
                volumes={
                    abs_workspace_path: {
                        "bind": self.config.mount_path,
                        "mode": "rw"
                    }
                },
                ports=port_mapping,
                mem_limit=self.config.memory_limit,
                nano_cpus=int(self.config.cpu_limit * 1e9),
                network_mode=self.config.network_mode,
                detach=True,
                working_dir=self.config.mount_path
            )
            return container.id

        try:
            container_id = await loop.run_in_executor(None, do_create)
            logger.info(f"[Docker] Container created successfully for session {session_id} (ID: {container_id[:12]})")
            return container_id
        except Exception as e:
            logger.error(f"[Docker] Failed to launch container for session {session_id}: {e}")
            raise ContainerError(f"Failed to create Docker container for session {session_id}: {e}")

    async def destroy(self, container_id: str) -> None:
        """Stop and remove a container by ID."""
        logger.info(f"[Docker] Destroying container {container_id[:12]}")
        loop = asyncio.get_running_loop()
        def do_destroy():
            try:
                container = self.client.containers.get(container_id)
                container.remove(force=True)
            except docker.errors.NotFound:
                pass
        try:
            await loop.run_in_executor(None, do_destroy)
            logger.info(f"[Docker] Container {container_id[:12]} destroyed successfully")
        except Exception as e:
            logger.error(f"[Docker] Failed to destroy container {container_id[:12]}: {e}")
            raise ContainerError(f"Failed to destroy Docker container {container_id}: {e}")

    async def exec(self, container_id: str, cmd: str, workdir: str = "/workspace", timeout: float | None = None) -> CommandResult:
        """Execute a command synchronously inside the container and demux outputs."""
        logger.debug(f"[Docker] Running exec command in {container_id[:12]} (workdir: {workdir}): {cmd}")
        loop = asyncio.get_running_loop()
        def do_exec():
            container = self.client.containers.get(container_id)
            return container.exec_run(cmd, workdir=workdir, demux=True)
        try:
            exit_code, output_tuple = await asyncio.wait_for(
                loop.run_in_executor(None, do_exec),
                timeout=timeout or self.config.execution_timeout
            )
            stdout_bytes, stderr_bytes = output_tuple
            stdout = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
            stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""
            return CommandResult(exit_code=exit_code, stdout=stdout, stderr=stderr)
        except asyncio.TimeoutError:
            logger.error(f"[Docker] Exec command timed out in container {container_id[:12]} after {timeout}s: {cmd}")
            raise ContainerError(f"Command execution timed out after {timeout} seconds")
        except Exception as e:
            logger.error(f"[Docker] Exec command failed in container {container_id[:12]}: {e}")
            raise ContainerError(f"Failed executing command inside container: {e}")

    async def exec_detached(self, container_id: str, cmd: str, workdir: str = "/workspace") -> str:
        """Create and start a detached exec session, returning its exec_id."""
        logger.info(f"[Docker] Starting detached exec command in {container_id[:12]}: {cmd}")
        loop = asyncio.get_running_loop()
        def do_exec_detached():
            container = self.client.containers.get(container_id)
            res = container.exec_run(cmd, workdir=workdir, detach=True)
            exec_id = res.output if isinstance(res.output, str) else res.output.decode("utf-8")
            return exec_id.strip()
        try:
            exec_id = await loop.run_in_executor(None, do_exec_detached)
            logger.info(f"[Docker] Detached exec started. Session ID: {exec_id[:12]}")
            return exec_id
        except Exception as e:
            logger.error(f"[Docker] Failed to start detached exec in container {container_id[:12]}: {e}")
            raise ContainerError(f"Failed to launch detached exec process: {e}")

    async def exec_inspect(self, exec_id: str) -> dict:
        """Inspect the status of a detached exec session."""
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, self.client.api.exec_inspect, exec_id)
        except Exception as e:
            raise ContainerError(f"Failed to inspect exec session {exec_id}: {e}")

    async def logs(self, container_id: str, tail: int = 100) -> str:
        """Fetch container system logs."""
        loop = asyncio.get_running_loop()
        def do_logs():
            container = self.client.containers.get(container_id)
            return container.logs(tail=tail)
        try:
            logs_bytes = await loop.run_in_executor(None, do_logs)
            return logs_bytes.decode("utf-8", errors="replace")
        except Exception as e:
            raise ContainerError(f"Failed reading container logs: {e}")

    async def stream_logs(self, container_id: str, tail: int = 100) -> AsyncGenerator[str, None]:
        """Stream container logs line-by-line asynchronously."""
        loop = asyncio.get_running_loop()
        def get_stream():
            container = self.client.containers.get(container_id)
            return container.logs(stream=True, tail=tail, follow=True)

        try:
            stream = await loop.run_in_executor(None, get_stream)
        except Exception as e:
            raise ContainerError(f"Failed to initiate log stream: {e}")

        try:
            while True:
                def get_next():
                    try:
                        return next(stream)
                    except StopIteration:
                        return None
                
                line_bytes = await loop.run_in_executor(None, get_next)
                if line_bytes is None:
                    break
                yield line_bytes.decode("utf-8", errors="replace")
        finally:
            if hasattr(stream, "close"):
                try:
                    stream.close()
                except Exception:
                    pass

    async def status(self, container_id: str) -> str:
        """Check container lifecycle status."""
        loop = asyncio.get_running_loop()
        def do_status():
            try:
                container = self.client.containers.get(container_id)
                container.reload()
                return container.status
            except docker.errors.NotFound:
                return "not_found"
        try:
            return await loop.run_in_executor(None, do_status)
        except Exception as e:
            raise ContainerError(f"Failed fetching container status: {e}")
