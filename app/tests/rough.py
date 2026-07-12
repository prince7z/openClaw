import sys
from pathlib import Path

# Reconfigure stdout to handle unicode prints safely on Windows terminal
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

# Add project root to path so 'app' can be imported when running script directly
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Load local environment variables from .env file
env_path = Path(__file__).resolve().parents[2] / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            val = val.strip().strip("'\"")
            import os
            os.environ[key.strip()] = val

from app.tools.filesystem import (  # noqa: E402
    append_file,
    copy,
    create_directory,
    create_file,
    current_directory,
    delete,
    exists,
    find,
    glob,
    list_directory,
    metadata,
    move,
    read_file,
    read_multiple,
    rename,
    search,
    tree,
    write_file,
)
from app.tools.search import web_search
print (web_search.invoke({"query": "prince sahu software engineer and freelancer", "top_k": 10, "max_results": 3}))
