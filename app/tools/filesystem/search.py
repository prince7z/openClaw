from __future__ import annotations

from pathlib import Path
from typing import Any, Literal
import re

from langchain.tools import tool
from langchain_core.runnables import RunnableConfig

from app.tools.filesystem._common import (
    absolute_path_strings,
    make_result,
    matches_name,
    should_ignore,
    to_path,
    iter_directory,
    safe_read_bytes,
    looks_binary,
)





@tool
def search_files(
    query: str,
    path: str = ".",
    search_type: Literal["name", "content", "glob"] | None = None,
    case_sensitive: bool = False,
    recursive: bool = True,
    config: RunnableConfig = None
) -> dict[str, Any]:
    """Search files."""
    try:
        if not search_type:
            if any(char in query for char in "*?[]"):
                search_type = "glob"
            else:
                search_type = "name"

        base = to_path(path, config=config)
        if not base.exists():
            return make_result(False, None, f"Path does not exist: {base}")
        if not base.is_dir():
            return make_result(False, None, f"Path is not a directory: {base}")

        if search_type == "glob":
            iterator = base.rglob(query) if recursive else base.glob(query)
            matches = [
                candidate.resolve(strict=False)
                for candidate in iterator
                if not should_ignore(candidate)
            ]
            return make_result(True, absolute_path_strings(matches), None)

        elif search_type == "name":
            matches: list[Path] = []
            for child in iter_directory(base, recursive=recursive, show_hidden=False):
                if matches_name(child.name, query, case_sensitive):
                    matches.append(child.resolve(strict=False))
            return make_result(True, absolute_path_strings(matches), None)

        elif search_type == "content":
            from app.tools.filesystem.files import SUPPORTED_DOCUMENT_EXTENSIONS, UNSUPPORTED_BINARY_EXTENSIONS
            matches: list[Path] = []
            pattern_compiled = re.compile(re.escape(query), 0 if case_sensitive else re.IGNORECASE)
            
            for child in iter_directory(base, recursive=recursive, show_hidden=False):
                if not child.is_file():
                    continue
                ext = child.suffix.lower()
                if ext in UNSUPPORTED_BINARY_EXTENSIONS:
                    continue
                if ext in SUPPORTED_DOCUMENT_EXTENSIONS:
                    try:
                        content = child.read_text(encoding="utf-8", errors="ignore")
                        if pattern_compiled.search(content):
                            matches.append(child.resolve(strict=False))
                    except Exception:
                        pass
                else:
                    try:
                        sample = safe_read_bytes(child)
                        if not looks_binary(sample):
                            content = child.read_text(encoding="utf-8", errors="ignore")
                            if pattern_compiled.search(content):
                                matches.append(child.resolve(strict=False))
                    except Exception:
                        pass
                        
            return make_result(True, absolute_path_strings(matches), None)

        else:
            return make_result(False, None, f"Unsupported search_type: {search_type}")
    except Exception as exc:
        return make_result(False, None, str(exc))
