from __future__ import annotations

from pathlib import Path
from typing import Any
import re

from langchain.tools import tool

from app.tools.filesystem._common import (
    absolute_path_strings,
    make_result,
    matches_name,
    should_ignore,
    to_path,
)


@tool
def search(
    path: str,
    pattern: str,
    case_sensitive: bool = False,
    regex: bool = False,
) -> dict[str, Any]:
    """Search filenames inside a single directory.

    Args:
        path: Directory to search.
        pattern: Filename pattern or substring to match.
        case_sensitive: Whether matching should respect case.

    Returns:
        A structured JSON response containing matching paths.
    """
    try:
        directory = to_path(path)
        if not directory.exists():
            return make_result(False, None, f"Path does not exist: {directory}")
        if not directory.is_dir():
            return make_result(False, None, f"Path is not a directory: {directory}")

        matches: list[Path] = []
        if regex:
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                compiled = re.compile(pattern, flags)
            except re.error as exc:
                return make_result(False, None, f"Invalid regular expression: {exc}")

            for child in directory.iterdir():
                if should_ignore(child):
                    continue
                if compiled.search(child.name):
                    matches.append(child.resolve(strict=False))
        else:
            for child in directory.iterdir():
                if should_ignore(child):
                    continue
                if matches_name(child.name, pattern, case_sensitive):
                    matches.append(child.resolve(strict=False))

        return make_result(True, absolute_path_strings(matches), None)
    except Exception as exc:
        return make_result(False, None, str(exc))


@tool
def find(pattern: str, root: str = ".", recursive: bool = True) -> dict[str, Any]:
    """Recursively search for filenames by glob pattern.

    Args:
        pattern: Glob pattern to match.
        root: Root directory to search from.
        recursive: Whether to search recursively.

    Returns:
        A structured JSON response containing matching paths.
    """
    try:
        base = to_path(root)
        if not base.exists():
            return make_result(False, None, f"Path does not exist: {base}")
        if not base.is_dir():
            return make_result(False, None, f"Path is not a directory: {base}")

        iterator = base.rglob(pattern) if recursive else base.glob(pattern)
        matches = [
            candidate.resolve(strict=False)
            for candidate in iterator
            if not should_ignore(candidate)
        ]
        return make_result(True, absolute_path_strings(matches), None)
    except Exception as exc:
        return make_result(False, None, str(exc))


@tool
def glob(pattern: str, root: str = ".") -> dict[str, Any]:
    """Search for paths using a glob pattern.

    Args:
        pattern: Glob pattern to match.
        root: Root directory to evaluate from.

    Returns:
        A structured JSON response containing matching paths.
    """
    try:
        base = to_path(root)
        if not base.exists():
            return make_result(False, None, f"Path does not exist: {base}")
        if not base.is_dir():
            return make_result(False, None, f"Path is not a directory: {base}")

        matches = [
            candidate.resolve(strict=False)
            for candidate in base.glob(pattern)
            if not should_ignore(candidate)
        ]
        return make_result(True, absolute_path_strings(matches), None)
    except Exception as exc:
        return make_result(False, None, str(exc))
