import unittest
import asyncio
from app.runtime.preview.providers.ngrok import NgrokProvider
from app.runtime.preview.manager import PreviewManager

class TestPreviewManager(unittest.TestCase):
    def test_preview_lifecycle(self):
        async def run():
            # Using custom mock provider to avoid making actual HTTP requests/needing real authtoken during local test runs
            class MockProvider:
                def __init__(self):
                    self._url = None
                async def start(self, port: int) -> str:
                    self._url = f"https://mock-tunnel.ngrok-free.app"
                    return self._url
                async def stop(self) -> None:
                    self._url = None
                def url(self) -> str | None:
                    return self._url
            
            manager = PreviewManager(MockProvider())
            
            # Start
            info = await manager.start(8080)
            self.assertEqual(info.url, "https://mock-tunnel.ngrok-free.app")
            self.assertEqual(info.host_port, 8080)
            
            # Stop
            await manager.stop()
            self.assertIsNone(manager.info())

        asyncio.run(run())

if __name__ == "__main__":
    unittest.main()
