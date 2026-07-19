from abc import ABC, abstractmethod
from typing import Optional

class PreviewProvider(ABC):
    @abstractmethod
    async def start(self, port: int) -> str:
        """Start the tunnel connecting to the local port and return public URL."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the active tunnel."""
        pass

    @abstractmethod
    def url(self) -> Optional[str]:
        """Get the active public URL if the tunnel is open."""
        pass
