from typing import Optional
from datetime import datetime
from app.runtime.preview.providers.base import PreviewProvider
from app.runtime.preview.providers.ngrok import NgrokProvider
from app.runtime.exceptions import PreviewError
from app.runtime.models import PreviewInfo

class PreviewManager:
    def __init__(self, provider: Optional[PreviewProvider] = None):
        self.provider = provider or NgrokProvider()
        self._host_port = None
        self._started_at = None

    async def start(self, port: int) -> PreviewInfo:
        """Start the tunnel using the provider and return detailed PreviewInfo."""
        try:
            url = await self.provider.start(port)
            self._host_port = port
            self._started_at = datetime.utcnow()
            return PreviewInfo(
                url=url,
                provider=self.provider.__class__.__name__,
                host_port=port,
                started_at=self._started_at
            )
        except Exception as e:
            raise PreviewError(f"Failed starting preview tunnel: {e}")

    async def stop(self) -> None:
        """Stop the active tunnel."""
        await self.provider.stop()
        self._host_port = None
        self._started_at = None

    def info(self) -> Optional[PreviewInfo]:
        """Get current PreviewInfo if running."""
        url = self.provider.url()
        if url and self._host_port and self._started_at:
            return PreviewInfo(
                url=url,
                provider=self.provider.__class__.__name__,
                host_port=self._host_port,
                started_at=self._started_at
            )
        return None
