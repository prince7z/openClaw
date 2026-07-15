from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from langchain.tools import tool

from app.tools.filesystem._common import (
    build_tree_node,
    iter_directory,
    make_result,
    to_path,
    validate_positive_int,
    matches_name,
)



# Internal helper function, not exposed as tool
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
def list_files(
    path: str = ".",
    view: Literal["list", "tree"] = "list",
    recursive: bool = False,
    pattern: str | None = None
) -> dict[str, Any]:
    """List files and directories."""
    try:
        if view == "tree":
            return tree(path=path, max_depth=3)

        directory = to_path(path)
        if not directory.exists():
            return make_result(False, None, f"Path does not exist: {directory}")
        if not directory.is_dir():
            return make_result(False, None, f"Path is not a directory: {directory}")

        entries: list[dict[str, Any]] = []
        for child in iter_directory(directory, recursive=recursive, show_hidden=False):
            if pattern and not matches_name(child.name, pattern, case_sensitive=False):
                continue
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
