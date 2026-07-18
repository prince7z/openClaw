import logging
from typing import List, Set

logger = logging.getLogger("openclaw-workflow-resource")

class ResourceLockManager:
    """Manages active capability locks in-memory to prevent concurrency race conditions."""

    def __init__(self):
        self._active_locks: Set[str] = set()

    def is_locked(self, resource: str) -> bool:
        """Checks if a capability is currently held by a running step."""
        return resource in self._active_locks

    def can_acquire_all(self, resources: List[str]) -> bool:
        """Returns True if all required capabilities can be acquired (none are locked)."""
        return not any(res in self._active_locks for res in resources)

    def acquire_all(self, resources: List[str]) -> bool:
        """Acquires locks on all specified capabilities if they are all available.
        
        Args:
            resources: List of capability string identifiers.
            
        Returns:
            True if all locks were successfully acquired, False otherwise.
        """
        if not self.can_acquire_all(resources):
            return False
        
        for res in resources:
            self._active_locks.add(res)
            logger.debug(f"Acquired capability lock: {res}")
        return True

    def release_all(self, resources: List[str]) -> None:
        """Releases locks on all specified capabilities."""
        for res in resources:
            self._active_locks.discard(res)
            logger.debug(f"Released capability lock: {res}")
