from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain.tools import tool

from app.tools.filesystem._common import (
    build_tree_node,
    iter_directory,
    make_result,
    mime_type_for_path,
    permissions_for_path,
    stat_to_metadata,
    to_path,
    validate_positive_int,
)


@tool
def list_directory(path: str = ".", recursive: bool = False, show_hidden: bool = False) -> dict[str, Any]:
    """List the contents of a directory.

    Args:
        path: Directory path to inspect.
        recursive: Whether to include all descendants.
        show_hidden: Whether to include hidden files and directories.

    Returns:
        A structured JSON response containing directory entries.
    """
    try:
        directory = to_path(path)
        if not directory.exists():
            return make_result(False, None, f"Path does not exist: {directory}")
        if not directory.is_dir():
            return make_result(False, None, f"Path is not a directory: {directory}")

        entries: list[dict[str, Any]] = []
        for child in iter_directory(directory, recursive=recursive, show_hidden=show_hidden):
            entries.append(
                {
                    "name": child.name,
                    "path": str(child.resolve(strict=False)),
                    "type": "directory" if child.is_dir() else "file",
                    "size": child.stat().st_size if child.exists() and child.is_file() else 0,
                }
            )

        return make_result(True, entries, None)
    except Exception as exc:
        return make_result(False, None, str(exc))


@tool
def tree(path: str = ".", max_depth: int = 3, show_hidden: bool = False) -> dict[str, Any]:
    """Build a nested directory tree.

    Args:
        path: Root directory path.
        max_depth: Maximum recursion depth to include.
        show_hidden: Whether to include hidden files and directories.

    Returns:
        A structured JSON tree representation.
    """
    try:
        root = to_path(path)
        depth = validate_positive_int(max_depth, "max_depth")
        if not root.exists():
            return make_result(False, None, f"Path does not exist: {root}")

        return make_result(True, build_tree_node(root, depth, show_hidden), None)
    except Exception as exc:
        return make_result(False, None, str(exc))


@tool
def current_directory() -> dict[str, Any]:
    """Return the current working directory.

    Returns:
        The absolute current working directory path.
    """
    try:
        return make_result(True, str(Path.cwd().resolve(strict=False)), None)
    except Exception as exc:
        return make_result(False, None, str(exc))


@tool
def exists(path: str) -> dict[str, Any]:
    """Check whether a path exists.

    Args:
        path: Path to check.

    Returns:
        True when the path exists, otherwise False.
    """
    try:
        target = to_path(path)
        return make_result(True, target.exists(), None)
    except Exception as exc:
        return make_result(False, None, str(exc))


@tool
def metadata(path: str) -> dict[str, Any]:
    """Return metadata for a filesystem path.

    Args:
        path: File or directory path.

    Returns:
        A metadata dictionary describing the target path.
    """
    try:
        raw_path = Path(path).expanduser()
        target = to_path(path)
        if not target.exists():
            return make_result(False, None, f"Path does not exist: {target}")

        data = stat_to_metadata(target)
        data["mime_type"] = mime_type_for_path(target)
        data["permissions"] = permissions_for_path(target)
        data["is_symlink"] = raw_path.is_symlink()
        return make_result(True, data, None)
    except Exception as exc:
        return make_result(False, None, str(exc))
