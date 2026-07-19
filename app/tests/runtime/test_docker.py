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
from app.runtime.docker.manager import DockerManager
from app.runtime.docker.image import DockerImageManager
from app.runtime.docker.network import DockerNetworkManager
from app.runtime.workspace.manager import WorkspaceManager

class TestDockerManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config = RuntimeConfig(workspace_root=self.temp_dir)
        self.workspace_mgr = WorkspaceManager(self.config)
        self.network_mgr = DockerNetworkManager()
        self.docker_mgr = DockerManager(self.config)
        self.image_mgr = DockerImageManager(self.docker_mgr.client, self.config)
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_container_lifecycle_and_exec(self):
        async def run():
            # 1. Ensure image exists
            await self.image_mgr.ensure()
            
            # 2. Setup workspace and port
            session_id = "test_docker_session"
            workspace_path = await self.workspace_mgr.create(session_id)
            host_port = self.network_mgr.allocate_port()
            port_mapping = self.network_mgr.create_port_mapping(host_port, 8000)
            
            # 3. Create container
            container_id = await self.docker_mgr.create(session_id, str(workspace_path), port_mapping)
            self.assertIsNotNone(container_id)
            
            # Verify status
            status = await self.docker_mgr.status(container_id)
            self.assertEqual(status, "running")
            
            # 4. Exec command
            res = await self.docker_mgr.exec(container_id, "python -c \"print('hello from docker')\"")
            self.assertEqual(res.exit_code, 0)
            self.assertIn("hello from docker", res.stdout)
            
            # 5. Clean up
            await self.docker_mgr.destroy(container_id)
            status = await self.docker_mgr.status(container_id)
            self.assertEqual(status, "not_found")
            
        asyncio.run(run())

if __name__ == "__main__":
    unittest.main()
