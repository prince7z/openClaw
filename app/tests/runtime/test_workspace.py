import unittest
import shutil
import tempfile
import asyncio
from pathlib import Path
from app.runtime.config import RuntimeConfig
from app.runtime.exceptions import WorkspaceError
from app.runtime.workspace.manager import WorkspaceManager

class TestWorkspaceManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config = RuntimeConfig(workspace_root=self.temp_dir)
        self.manager = WorkspaceManager(self.config)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_create_and_exists(self):
        async def run():
            workspace_path = await self.manager.create("session_1")
            self.assertTrue(workspace_path.exists())
            self.assertTrue(self.manager.exists("session_1"))
            
            # Subdir check
            resolved = self.manager.resolve("session_1", "src/index.js")
            self.assertEqual(resolved, workspace_path / "src" / "index.js")

        asyncio.run(run())

    def test_directory_traversal_block(self):
        async def run():
            await self.manager.create("session_2")
            with self.assertRaises(WorkspaceError):
                self.manager.resolve("session_2", "../session_1")

        asyncio.run(run())

    def test_cleanup(self):
        async def run():
            workspace_path = await self.manager.create("session_3")
            self.assertTrue(workspace_path.exists())
            await self.manager.cleanup("session_3")
            self.assertFalse(workspace_path.exists())

        asyncio.run(run())

if __name__ == "__main__":
    unittest.main()
