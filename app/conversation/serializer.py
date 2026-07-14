"""State serialization helpers utilizing LangChain message serializations."""

import json
from abc import ABC, abstractmethod
from typing import Any
from langchain_core.messages import messages_to_dict, messages_from_dict


class StateSerializer(ABC):
    """Abstract Base Class specifying serialization operations for the AgentState."""

    @abstractmethod
    def serialize(self, state: dict[str, Any]) -> str:
        """Convert the AgentState dictionary to a string representation.

        Args:
            state: The active state dictionary.

        Returns:
            The serialized string.
        """
        pass

    @abstractmethod
    def deserialize(self, data: str) -> dict[str, Any]:
        """Convert a serialized string representation back into an AgentState dictionary.

        Args:
            data: The serialized string.

        Returns:
            The parsed state dictionary.
        """
        pass


class JSONStateSerializer(StateSerializer):
    """Concrete serializer using JSON and LangChain message dictionary utilities."""

    def serialize(self, state: dict[str, Any]) -> str:
        """Serialize the entire state block to JSON, encoding LangChain messages.

        Args:
            state: The active state dictionary.

        Returns:
            JSON-formatted string representation.
        """
        # Capture raw messages sequence
        messages = state.get("messages") or []
        serialized_messages = messages_to_dict(messages)
        
        # Build copy of state containing serialized message structure
        serializable_state = dict(state)
        serializable_state["messages"] = serialized_messages
        
        # Wrap in versioned container
        payload = {
            "version": 1,
            "state": serializable_state
        }
        return json.dumps(payload)

    def deserialize(self, data: str) -> dict[str, Any]:
        """Deserialize JSON representation and convert messages back to BaseMessage instances.

        Args:
            data: JSON-formatted string representation.

        Returns:
            Decoded state dictionary.
        """
        payload = json.loads(data)
        state_data = payload.get("state") or {}
        
        # Deserialize message array
        serialized_messages = state_data.get("messages") or []
        messages = messages_from_dict(serialized_messages)
        
        # Build copy and restore message instances
        parsed_state = dict(state_data)
        parsed_state["messages"] = messages
        
        return parsed_state
