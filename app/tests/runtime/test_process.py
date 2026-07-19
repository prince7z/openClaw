import unittest
import tempfile
import shutil
import asyncio
from app.runtime.config import RuntimeConfig
from app.runtime.docker.manager import DockerManager
from app.runtime.docker.image import DockerImageManager
from app.runtime.docker.network import DockerNetworkManager
from app.runtime.workspace.manager import WorkspaceManager
from app.runtime.process.manager import ProcessManager

class TestProcessManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config = RuntimeConfig(workspace_root=self.temp_dir)
        self.workspace_mgr = WorkspaceManager(self.config)
        self.network_mgr = DockerNetworkManager()
        self.docker_mgr = DockerManager(self.config)
        self.image_mgr = DockerImageManager(self.docker_mgr.client, self.config)
        self.process_mgr = ProcessManager()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_process_lifecycle(self):
        async def run():
            await self.image_mgr.ensure()
            session_id = "test_process_session"
            workspace_path = await self.workspace_mgr.create(session_id)
            host_port = self.network_mgr.allocate_port()
            port_mapping = self.network_mgr.create_port_mapping(host_port, 8000)
            
            container_id = await self.docker_mgr.create(session_id, str(workspace_path), port_mapping)
            
            # Start a background server process (simple HTTP server)
            cmd = "python -m http.server 8000"
            exec_id = await self.process_mgr.start(self.docker_mgr, container_id, cmd)
            self.assertIsNotNone(exec_id)
            
            # Wait for startup
            await asyncio.sleep(2)
            
            # Get status
            info = await self.process_mgr.status(self.docker_mgr, exec_id)
            self.assertEqual(info.status, "running")
            
            # Stop process
            await self.process_mgr.stop(self.docker_mgr, container_id, port=8000)
            
            # Verify stopped
            info = await self.process_mgr.status(self.docker_mgr, exec_id)
            self.assertEqual(info.status, "stopped")
            
            await self.docker_mgr.destroy(container_id)
            
        asyncio.run(run())

if __name__ == "__main__":
    unittest.main()
