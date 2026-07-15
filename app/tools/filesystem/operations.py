from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Literal

from langchain.tools import tool
from app.tools.filesystem.files import create_file

from app.tools.filesystem._common import (
    make_result,
    remove_path,
    to_path,
    validate_new_name,
)


# Internal helper function, not exposed as tool
def copy(source: str, destination: str, overwrite: bool = False) -> dict[str, Any]:
    """Copy a file or directory.

    Args:
        source: Source path.
        destination: Destination path.
        overwrite: Whether to replace an existing destination.

    Returns:
        The absolute destination path.
    """
    try:
        src = to_path(source)
        dst = to_path(destination)

        if not src.exists():
            return make_result(False, None, f"Source does not exist: {src}")

        target = dst / src.name if dst.exists() and dst.is_dir() else dst
        if target.exists():
            if not overwrite:
                return make_result(False, None, f"Destination already exists: {target}")
            remove_path(target)

        target.parent.mkdir(parents=True, exist_ok=True)

        if src.is_dir():
            shutil.copytree(src, target)
        else:
            shutil.copy2(src, target)

        return make_result(True, str(target.resolve(strict=False)), None)
    except Exception as exc:
        return make_result(False, None, str(exc))


# Internal helper function, not exposed as tool
def move(source: str, destination: str, overwrite: bool = False) -> dict[str, Any]:
    """Move a file or directory.

    Args:
        source: Source path.
        destination: Destination path.
        overwrite: Whether to replace an existing destination.

    Returns:
        The absolute destination path.
    """
    try:
        src = to_path(source)
        dst = to_path(destination)

        if not src.exists():
            return make_result(False, None, f"Source does not exist: {src}")

        target = dst / src.name if dst.exists() and dst.is_dir() else dst
        if target.exists():
            if not overwrite:
                return make_result(False, None, f"Destination already exists: {target}")
            remove_path(target)

        target.parent.mkdir(parents=True, exist_ok=True)

        result_path = shutil.move(str(src), str(target))
        return make_result(True, str(Path(result_path).resolve(strict=False)), None)
    except Exception as exc:
        return make_result(False, None, str(exc))


# Internal helper function, not exposed as tool
def rename(path: str, new_name: str) -> dict[str, Any]:
    """Rename a file or directory.

    Args:
        path: Existing file or directory path.
        new_name: New base name for the path.

    Returns:
        The absolute renamed path.
    """
    try:
        target = to_path(path)
        validate_new_name(new_name)

        if not target.exists():
            return make_result(False, None, f"Path does not exist: {target}")

        destination = target.with_name(new_name)
        if destination.exists():
            return make_result(False, None, f"Destination already exists: {destination}")

        renamed = target.rename(destination)
        return make_result(True, str(renamed.resolve(strict=False)), None)
    except Exception as exc:
        return make_result(False, None, str(exc))


# Internal helper function, not exposed as tool
def delete(path: str, recursive: bool = False, trash: bool = False) -> dict[str, Any]:
    """Delete a file or directory.

    Args:
        path: Path to delete.
        recursive: Whether directory deletion is allowed.

    Returns:
        The absolute path that was deleted.
    """
    try:
        target = to_path(path)
        if not target.exists():
            return make_result(False, None, f"Path does not exist: {target}")

        if target.is_dir() and not recursive:
            return make_result(False, None, "Recursive delete requires recursive=True")

        if trash:
            from send2trash import send2trash

            send2trash(str(target))
        else:
            remove_path(target)
        return make_result(True, str(target), None)
    except Exception as exc:
        return make_result(False, None, str(exc))


# Internal helper function, not exposed as tool
def create_directory(path: str, parents: bool = True, exist_ok: bool = True) -> dict[str, Any]:
    """Create a directory.

    Args:
        path: Directory path to create.
        parents: Whether to create parent directories.
        exist_ok: Whether to allow an existing directory.

    Returns:
        The absolute directory path.
    """
    try:
        target = to_path(path)
        if target.exists() and not target.is_dir():
            return make_result(False, None, f"Path is a file: {target}")

        target.mkdir(parents=parents, exist_ok=exist_ok)
        return make_result(True, str(target.resolve(strict=False)), None)
    except Exception as exc:
        return make_result(False, None, str(exc))


@tool
def manage_file(
    action: Literal["copy", "move", "rename", "delete", "create"],
    path: str,
    target: str | None = None,
    kind: Literal["file", "directory"] | None = None
) -> dict[str, Any]:
    """Manage files and directories."""
    try:
        if action == "copy":
            if not target:
                return make_result(False, None, "copy action requires a target destination")
            return copy(source=path, destination=target, overwrite=True)

        elif action == "move":
            if not target:
                return make_result(False, None, "move action requires a target destination")
            return move(source=path, destination=target, overwrite=True)

        elif action == "rename":
            if not target:
                return make_result(False, None, "rename action requires a target new name")
            return rename(path=path, new_name=target)

        elif action == "delete":
            return delete(path=path, recursive=True)

        elif action == "create":
            if kind == "directory":
                is_dir = True
            elif kind == "file":
                is_dir = False
            else:
                target_path = Path(path)
                is_dir = path.endswith('/') or path.endswith('\\') or not target_path.suffix

            if is_dir:
                return create_directory(path=path, parents=True, exist_ok=True)
            else:
                return create_file(path=path, exist_ok=True)

        else:
            return make_result(False, None, f"Unsupported action: {action}")
    except Exception as exc:
        return make_result(False, None, str(exc))
