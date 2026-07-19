import socket
from typing import Dict
from app.runtime.exceptions import ContainerError

class DockerNetworkManager:
    def allocate_port(self) -> int:
        """Find an available TCP port on the host."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", 0))
                return s.getsockname()[1]
        except Exception as e:
            raise ContainerError(f"Failed to dynamically allocate a free host port: {e}")

    def release_port(self, port: int) -> None:
        """No-op on the host since ports are only held transiently during lookup."""
        pass

    def create_port_mapping(self, host_port: int, container_port: int) -> Dict[str, int]:
        """Generate the ports dictionary configuration for container creation."""
        return {f"{container_port}/tcp": host_port}
