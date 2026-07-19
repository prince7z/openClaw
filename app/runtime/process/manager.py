import logging
from typing import Optional
from app.runtime.exceptions import ProcessError
from app.runtime.models import ProcessInfo

logger = logging.getLogger("openclaw-agent")

class ProcessManager:
    async def start(self, docker_manager, container_id: str, command: str, workdir: str = "/workspace") -> str:
        """Start a long-running process inside the container and return its exec_id."""
        logger.info(f"[Process] Starting daemon process inside container {container_id[:12]}: {command}")
        try:
            shell_cmd = f"sh -c '{command}'"
            exec_id = await docker_manager.exec_detached(container_id, shell_cmd, workdir)
            return exec_id
        except Exception as e:
            logger.error(f"[Process] Failed to start daemon in container {container_id[:12]}: {e}")
            raise ProcessError(f"Failed to start process: {e}")

    async def stop(self, docker_manager, container_id: str, port: int) -> None:
        """Stop the running process by killing standard port listeners inside the container."""
        logger.info(f"[Process] Killing daemon listeners on port {port} in container {container_id[:12]}")
        try:
            # Force kill any process listening on the container port
            kill_port_cmd = f"sh -c 'kill -9 $(lsof -t -i:{port}) || kill -9 $(fuser -t {port}/tcp)'"
            await docker_manager.exec(container_id, kill_port_cmd)
        except Exception as e:
            logger.warning(f"[Process] Stop container port kill failed or process not found: {e}")
            pass

    async def status(self, docker_manager, exec_id: str) -> ProcessInfo:
        """Inspect and return the status of the process exec run."""
        try:
            info = await docker_manager.exec_inspect(exec_id)
            exit_code = info.get("ExitCode")
            running = info.get("Running", False)
            
            cmd_list = info.get("ProcessConfig", {}).get("entrypoint", [])
            command = " ".join(cmd_list) if isinstance(cmd_list, list) else str(cmd_list)
            pid = info.get("Pid")

            status = "running" if running else "stopped"
            logger.debug(f"[Process] Status check for exec {exec_id[:12]} - running: {running}, exit_code: {exit_code}")
            return ProcessInfo(
                exec_id=exec_id,
                command=command,
                status=status,
                pid=pid,
                exit_code=exit_code
            )
        except Exception as e:
            logger.error(f"[Process] Failed to inspect status of exec session {exec_id}: {e}")
            raise ProcessError(f"Failed checking process status: {e}")
