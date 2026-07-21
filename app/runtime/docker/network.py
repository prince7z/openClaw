import socket
from typing import Dict, Tuple, List
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

    DEFAULT_WEB_PORTS = [8000, 3000, 5173, 8080, 3001, 5000]

    def create_session_port_mappings(self, extra_ports: List[int] = None) -> Tuple[Dict[str, int], Dict[int, int]]:
        """Generate port mappings for standard container web ports (8000, 3000, 5173, 8080, etc.).
        Returns (docker_ports_dict, container_to_host_map).
        """
        ports_to_map = list(self.DEFAULT_WEB_PORTS)
        if extra_ports:
            for p in extra_ports:
                if p not in ports_to_map:
                    ports_to_map.append(p)

        docker_ports = {}
        container_to_host = {}

        for c_port in ports_to_map:
            h_port = self.allocate_port()
            docker_ports[f"{c_port}/tcp"] = h_port
            container_to_host[c_port] = h_port

        return docker_ports, container_to_host

    def create_port_mapping(self, host_port: int, container_port: int) -> Dict[str, int]:
        """Generate the ports dictionary configuration for container creation."""
        return {f"{container_port}/tcp": host_port}
