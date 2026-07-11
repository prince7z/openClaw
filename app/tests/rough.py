import sys
from pathlib import Path

# Add project root to path so 'app' can be imported when running script directly
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

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

print(tree.invoke({"path": "D:/VS/openclaw", "max_depth": 10, "show_hidden": True}))
