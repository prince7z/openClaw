from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Any

class EventBus(ABC):
    """Abstract interface defining standard publish/subscribe messaging for the workflow engine."""
    
    @abstractmethod
    async def publish(self, topic: str, data: Dict[str, Any]) -> None:
        """Publishes an event message to a specific topic."""
        pass

    @abstractmethod
    async def subscribe(self, topic: str) -> AsyncIterator[Dict[str, Any]]:
        """Subscribes to a topic, returning an async iterator yielding event messages."""
        pass
