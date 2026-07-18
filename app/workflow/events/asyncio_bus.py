import asyncio
from typing import AsyncIterator, Dict, List, Any
import logging

from app.workflow.events.bus import EventBus

logger = logging.getLogger("openclaw-workflow-asynciobus")

class AsyncioEventBus(EventBus):
    """In-memory Event Bus implementation utilizing asyncio.Queue."""

    def __init__(self):
        # Maps topic_name -> List of active subscription queues
        self._listeners: Dict[str, List[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def publish(self, topic: str, data: Dict[str, Any]) -> None:
        """Pushes data payload to all queues subscribed to the topic."""
        async with self._lock:
            queues = list(self._listeners.get(topic, []))
        
        if queues:
            logger.debug(f"Publishing event to {topic} (Listeners: {len(queues)})")
            for q in queues:
                await q.put(data)
        else:
            logger.debug(f"Publishing event to {topic} (No listeners active)")

    async def subscribe(self, topic: str) -> AsyncIterator[Dict[str, Any]]:
        """Returns an async iterator that yields incoming events on this topic."""
        q = asyncio.Queue()
        async with self._lock:
            if topic not in self._listeners:
                self._listeners[topic] = []
            self._listeners[topic].append(q)

        try:
            while True:
                event = await q.get()
                yield event
                q.task_done()
        finally:
            # Cleanup listener on cancellation or exit
            async with self._lock:
                if topic in self._listeners:
                    self._listeners[topic].remove(q)
                    if not self._listeners[topic]:
                        del self._listeners[topic]
