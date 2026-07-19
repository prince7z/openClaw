import unittest
import tempfile
import shutil
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from app.runtime.config import RuntimeConfig
from app.runtime.manager import RuntimeManager

class TestFullPythonFlow(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config = RuntimeConfig(workspace_root=self.temp_dir)
        self.runtime_mgr = RuntimeManager(self.config)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_integration_flow(self):
        async def run():
            # 1. Initialize manager (pulls/builds image and cleans up dangling containers)
            await self.runtime_mgr.initialize()

            session_id = "test_flow_session"
            
            # 2. Create session
            session = await self.runtime_mgr.create_session(session_id)
            self.assertIsNotNone(session.container_id)
            
            # 3. Write hello.py to workspace
            hello_file = Path(session.workspace) / "hello.py"
            hello_file.write_text("print('hello from integration script')", encoding="utf-8")
            
            # 4. Execute python command inside container
            res = await self.runtime_mgr.execute(session_id, "python hello.py")
            self.assertEqual(res.exit_code, 0)
            self.assertIn("hello from integration script", res.stdout)
            
            # 5. Destroy session (cleanup workspaces = False to let tearDown clean it)
            await self.runtime_mgr.destroy_session(session_id, keep_workspace=True)
            
            # 6. Shutdown manager
            await self.runtime_mgr.shutdown()

        asyncio.run(run())

if __name__ == "__main__":
    unittest.main()
