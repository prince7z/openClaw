import os
import logging
import asyncio
from pathlib import Path
import docker
from app.runtime.config import RuntimeConfig
from app.runtime.exceptions import ContainerError

logger = logging.getLogger("openclaw-agent")

class DockerImageManager:
    def __init__(self, client: docker.DockerClient, config: RuntimeConfig):
        self.client = client
        self.config = config

    async def ensure(self) -> None:
        """Ensure the specified image is available locally or build it."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._ensure_sync)

    def _ensure_sync(self) -> None:
        image_tag = f"{self.config.image_name}:{self.config.image_tag}"
        try:
            self.client.images.get(image_tag)
            logger.info(f"Docker image {image_tag} verified locally.")
        except docker.errors.ImageNotFound:
            logger.info(f"Docker image {image_tag} not found locally. Initiating build...")
            self._build_sync()

    def _build_sync(self) -> None:
        image_tag = f"{self.config.image_name}:{self.config.image_tag}"
        # Dockerfile is located at project_root/docker/Dockerfile
        dockerfile_dir = Path(__file__).parent.parent.parent.parent / "docker"
        if not (dockerfile_dir / "Dockerfile").exists():
            raise ContainerError(f"Dockerfile not found at {dockerfile_dir / 'Dockerfile'}")

        try:
            logger.info(f"Building Docker image {image_tag} from {dockerfile_dir}...")
            self.client.images.build(
                path=str(dockerfile_dir),
                tag=image_tag,
                rm=True
            )
            logger.info(f"Docker image {image_tag} built successfully.")
        except Exception as e:
            raise ContainerError(f"Failed to build Docker image {image_tag}: {e}")
