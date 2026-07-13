"""YAML parsing and token-minimized serialization utilities."""

from typing import Any
import yaml

from app.tools.browser.schemas import PageState, StateDiff


def clean_empty_values(data: Any) -> Any:
    """Recursively strip empty lists, dicts, and None values to minimize token payload size.

    Args:
        data: Nested dictionary or list to prune.

    Returns:
        Pruned dictionary/list structure.
    """
    if isinstance(data, dict):
        cleaned = {}
        for key, val in data.items():
            # Skip serializing keys with empty arrays or null values
            if isinstance(val, list) and not val:
                continue
            if val is None:
                continue
            cleaned_val = clean_empty_values(val)
            if cleaned_val or isinstance(cleaned_val, (int, float, bool)):
                cleaned[key] = cleaned_val
        return cleaned
    elif isinstance(data, list):
        return [clean_empty_values(item) for item in data if item is not None]
    return data


def serialize_to_yaml(state: PageState | StateDiff | dict[str, Any]) -> str:
    """Serialize the page model state or state diff to a compact YAML representation.

    Args:
        state: PageState, StateDiff, or raw dictionary data.

    Returns:
        Pruned YAML string layout.
    """
    if hasattr(state, "model_dump"):
        raw_dict = state.model_dump()
    else:
        raw_dict = dict(state)

    pruned_dict = clean_empty_values(raw_dict)
    return yaml.safe_dump(pruned_dict, sort_keys=False, allow_unicode=True)
