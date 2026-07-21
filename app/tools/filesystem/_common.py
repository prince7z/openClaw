from __future__ import annotations

import ctypes
import fnmatch
import mimetypes
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

try:
    from langchain_core.runnables import RunnableConfig
except ImportError:
    RunnableConfig = Any  # type: ignore


def make_result(success: bool, data: Any = None, error: str | None = None) -> dict[str, Any]:
    """Build a standard filesystem tool response."""
    return {"success": success, "data": data, "error": error}


def get_session_id(config: Optional[RunnableConfig] = None) -> str:
    """Extract chat/session ID from LangChain RunnableConfig."""
    if not config or not isinstance(config, dict):
        return "default_sandbox_session"
    configurable = config.get("configurable", {})
    if not isinstance(configurable, dict):
        return "default_sandbox_session"
    thread_id = configurable.get("thread_id", "default_sandbox_session")
    return str(thread_id).replace("tg-", "")


def get_session_workspace(config: Optional[RunnableConfig] = None) -> Path:
    """Get the resolved host workspace directory for the active session."""
    from app.runtime.config import RuntimeConfig
    session_id = get_session_id(config)
    base_dir = Path(RuntimeConfig().workspace_root).resolve()
    workspace_path = base_dir / session_id
    workspace_path.mkdir(parents=True, exist_ok=True)
    return workspace_path


def to_path(value: str | Path, config: Optional[RunnableConfig] = None) -> Path:
    """Convert a user-supplied value to an absolute resolved path within the session workspace.

    Args:
        value: Path-like input supplied to a filesystem tool.
        config: Optional LangChain RunnableConfig for session context.

    Returns:
        A resolved absolute pathlib.Path instance.

    Raises:
        TypeError: If the input is not path-like.
    """
    if not isinstance(value, (str, Path)):
        raise TypeError("path must be a string or Path")

    session_workspace = get_session_workspace(config)
    path_str = str(value).strip()

    # Normalize backslashes to forward slashes for pattern matching
    normalized = path_str.replace("\\", "/")

    # Check for container path /workspace or workspace/
    if normalized.startswith("/workspace") or normalized.startswith("workspace/"):
        rel = re.sub(r"^/?workspace/?", "", normalized)
        return (session_workspace / rel).resolve(strict=False)

    # Check for /tests/workspace or tests/workspace/
    if normalized.startswith("/tests/workspace") or normalized.startswith("tests/workspace/"):
        rel = re.sub(r"^/?tests/workspace/?", "", normalized)
        return (session_workspace / rel).resolve(strict=False)

    # Check for workspaces/<session_id>
    session_id = get_session_id(config)
    if normalized.startswith(f"workspaces/{session_id}") or normalized.startswith(f"/workspaces/{session_id}"):
        rel = re.sub(rf"^/?workspaces/{re.escape(session_id)}/?", "", normalized)
        return (session_workspace / rel).resolve(strict=False)

    p = Path(path_str)

    # If it is an explicit absolute path on host OS (e.g., C:\... or D:\...)
    if p.is_absolute():
        resolved = p.resolve(strict=False)
        return resolved

    # Relative paths resolve inside the session workspace
    return (session_workspace / p).resolve(strict=False)



def ensure_parent_directory(path: Path) -> None:
    """Create the parent directory for a path if it does not already exist."""
    path.parent.mkdir(parents=True, exist_ok=True)


def is_hidden(path: Path) -> bool:
    """Determine whether a path should be treated as hidden."""
    if path.name.startswith("."):
        return True

    if sys.platform.startswith("win"):
        try:
            attributes = ctypes.windll.kernel32.GetFileAttributesW(str(path))
            if attributes == -1:
                return False
            return bool(attributes & 0x2)
        except Exception:
            return False

    return False


IGNORED_NAMES = {
    "node_modules",
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    ".ipynb_checkpoints",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}


def should_ignore(path: Path) -> bool:
    """Determine whether a path should be ignored (e.g. node_modules, pycache)."""
    return any(part in IGNORED_NAMES for part in path.parts)


def stat_to_metadata(path: Path) -> dict[str, Any]:
    """Build a metadata dictionary for a filesystem path."""
    stat_result = path.stat()
    path_type = "directory" if path.is_dir() else "file"
    return {
        "name": path.name,
        "path": str(path),
        "type": path_type,
        "size": stat_result.st_size,
        "created": datetime.fromtimestamp(stat_result.st_ctime, tz=timezone.utc).isoformat(),
        "modified": datetime.fromtimestamp(stat_result.st_mtime, tz=timezone.utc).isoformat(),
        "extension": path.suffix,
        "is_hidden": is_hidden(path),
    }


def mime_type_for_path(path: Path) -> str:
    """Guess a MIME type for a path."""
    mime_type, _ = mimetypes.guess_type(str(path))
    if mime_type:
        return mime_type

    extension = path.suffix.lower()
    return {
        ".csv": "text/csv",
        ".md": "text/markdown",
        ".yml": "application/x-yaml",
        ".yaml": "application/x-yaml",
        ".json": "application/json",
        ".xml": "application/xml",
        ".odt": "application/vnd.oasis.opendocument.text",
        ".epub": "application/epub+zip",
    }.get(extension, "application/octet-stream")


def permissions_for_path(path: Path) -> dict[str, Any]:
    """Return a portable permissions summary for a path."""
    stat_result = path.stat()
    return {
        "mode": oct(stat_result.st_mode & 0o777),
        "readable": os.access(path, os.R_OK),
        "writable": os.access(path, os.W_OK),
        "executable": os.access(path, os.X_OK),
    }


def looks_binary(sample: bytes) -> bool:
    """Heuristically determine whether a byte sample looks binary."""
    if not sample:
        return False
    if b"\x00" in sample:
        return True

    text_bytes = set(range(32, 127)) | {9, 10, 13, 12, 8}
    non_text = sum(byte not in text_bytes for byte in sample)
    return (non_text / len(sample)) > 0.30


def line_count(text: str) -> int:
    """Count display lines in a string."""
    if not text:
        return 0
    return text.count("\n") + 1


def markdown_table(rows: list[list[Any]], headers: list[str] | None = None) -> str:
    """Render a simple markdown table."""
    def escape_cell(value: Any) -> str:
        cell = "" if value is None else str(value)
        return cell.replace("\n", " ").replace("|", r"\|")

    if not rows and not headers:
        return ""

    if headers is None:
        headers = [f"Column {index + 1}" for index in range(len(rows[0]) if rows else 0)]

    table_rows = [headers, ["---" for _ in headers]]
    for row in rows:
        table_rows.append([escape_cell(cell) for cell in row])

    return "\n".join("| " + " | ".join(row) + " |" for row in table_rows)


def safe_read_bytes(path: Path, limit: int = 8192) -> bytes:
    """Read a small byte sample from a file."""
    with path.open("rb") as handle:
        return handle.read(limit)


def is_pattern_search(pattern: str) -> bool:
    """Return True when the pattern contains glob-style wildcards."""
    return any(char in pattern for char in "*?[]")


def matches_name(name: str, pattern: str, case_sensitive: bool) -> bool:
    """Match a filename against either a glob or substring pattern."""
    if case_sensitive:
        candidate = name
        needle = pattern
    else:
        candidate = name.lower()
        needle = pattern.lower()

    if is_pattern_search(pattern):
        return fnmatch.fnmatchcase(candidate, needle)

    return needle in candidate


def validate_new_name(new_name: str) -> None:
    """Validate a rename target name."""
    if not isinstance(new_name, str) or not new_name.strip():
        raise TypeError("new_name must be a non-empty string")

    if new_name in {".", ".."}:
        raise ValueError("new_name must be a file or directory name, not a path reference")

    if "/" in new_name or "\\" in new_name:
        raise ValueError("new_name must not contain path separators")


def remove_path(path: Path) -> None:
    """Remove a file or directory path."""
    if path.is_dir():
        import shutil

        shutil.rmtree(path)
        return

    path.unlink()


def iter_directory(path: Path, recursive: bool, show_hidden: bool) -> Iterable[Path]:
    """Yield directory entries, optionally walking recursively."""
    if not recursive:
        for child in path.iterdir():
            if should_ignore(child):
                continue
            if show_hidden or not is_hidden(child):
                yield child
        return

    stack = [path]
    while stack:
        current = stack.pop()
        for child in current.iterdir():
            if should_ignore(child):
                continue
            if not show_hidden and is_hidden(child):
                continue
            yield child
            if child.is_dir():
                stack.append(child)


def build_tree_node(path: Path, max_depth: int, show_hidden: bool, current_depth: int = 0) -> dict[str, Any]:
    """Build a nested tree representation for a path."""
    node = {
        "name": path.name or str(path),
        "path": str(path),
        "type": "directory" if path.is_dir() else "file",
        "size": path.stat().st_size if path.exists() and path.is_file() else 0,
    }

    if not path.is_dir() or current_depth >= max_depth:
        node["children"] = []
        return node

    children: list[dict[str, Any]] = []
    for child in sorted(path.iterdir(), key=lambda candidate: candidate.name.lower()):
        if should_ignore(child):
            continue
        if not show_hidden and is_hidden(child):
            continue
        children.append(build_tree_node(child, max_depth, show_hidden, current_depth + 1))

    node["children"] = children
    return node


def absolute_path_strings(paths: Iterable[Path]) -> list[str]:
    """Convert a sequence of paths to absolute string paths."""
    return [str(path.resolve(strict=False)) for path in paths]


def validate_text_content(content: Any) -> str:
    """Validate and normalize text content."""
    if not isinstance(content, str):
        raise TypeError("content must be a string")
    return content


def validate_paths(paths: Any) -> list[Path]:
    """Validate a path list input."""
    if not isinstance(paths, list):
        raise TypeError("paths must be a list of path strings")
    return [to_path(path) for path in paths]


def validate_positive_int(value: Any, field_name: str) -> int:
    """Validate a non-negative integer value."""
    if not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value < 0:
        raise ValueError(f"{field_name} must be greater than or equal to zero")
    return value