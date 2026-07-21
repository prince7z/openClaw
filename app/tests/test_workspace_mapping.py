import sys
import unittest
import shutil
from pathlib import Path

# Add project root to sys.path when running script directly
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.tools.filesystem import write_file, read_file, list_files, manage_file, search_files
from app.tools.filesystem._common import to_path, get_session_workspace, get_session_id
from app.runtime.config import RuntimeConfig


class TestWorkspaceMapping(unittest.TestCase):
    def setUp(self):
        self.session_id = "test_workspace_session"
        self.config = {"configurable": {"thread_id": self.session_id}}
        self.expected_workspace = Path(RuntimeConfig().workspace_root).resolve() / self.session_id

    tearDown = lambda self: shutil.rmtree(self.expected_workspace, ignore_errors=True)

    def test_to_path_resolution(self):
        # 1. Relative path
        p1 = to_path("hello.py", config=self.config)
        self.assertEqual(p1, self.expected_workspace / "hello.py")

        # 2. Container /workspace path
        p2 = to_path("/workspace/src/App.jsx", config=self.config)
        self.assertEqual(p2, self.expected_workspace / "src" / "App.jsx")

        # 3. /tests/workspace path
        p3 = to_path("/tests/workspace/config.json", config=self.config)
        self.assertEqual(p3, self.expected_workspace / "config.json")

        # 4. workspaces/<session_id> path
        p4 = to_path(f"workspaces/{self.session_id}/index.js", config=self.config)
        self.assertEqual(p4, self.expected_workspace / "index.js")

    def test_write_and_read_file(self):
        # Write file using relative path
        res_write = write_file.invoke({"path": "sample.txt", "content": "Hello Workspace!"}, config=self.config)
        self.assertTrue(res_write["success"])
        
        # Verify it exists on disk at expected_workspace
        file_on_disk = self.expected_workspace / "sample.txt"
        self.assertTrue(file_on_disk.exists())
        self.assertEqual(file_on_disk.read_text(encoding="utf-8"), "Hello Workspace!")

        # Read file using /workspace prefix
        res_read = read_file.invoke({"path": "/workspace/sample.txt"}, config=self.config)
        self.assertTrue(res_read["success"])
        self.assertEqual(res_read["data"]["content"], "Hello Workspace!")

if __name__ == "__main__":
    unittest.main()
