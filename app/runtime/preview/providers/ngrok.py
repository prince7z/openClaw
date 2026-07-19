import os
import asyncio
import logging
from typing import Optional
from pyngrok import ngrok, conf
from app.runtime.preview.providers.base import PreviewProvider
from app.runtime.exceptions import PreviewError

logger = logging.getLogger("openclaw-agent")

class NgrokProvider(PreviewProvider):
    def __init__(self, authtoken: Optional[str] = None):
        self.authtoken = authtoken or os.getenv("NGROK_AUTHTOKEN")
        self.tunnel = None

    async def start(self, port: int) -> str:
        """Start ngrok tunnel on the host port."""
        logger.info(f"[Ngrok] Initiating HTTP tunnel on host port {port}")
        try:
            if self.authtoken:
                ngrok.set_auth_token(self.authtoken)
            
            loop = asyncio.get_running_loop()
            def connect_tunnel():
                return ngrok.connect(port, "http")

            self.tunnel = await loop.run_in_executor(None, connect_tunnel)
            logger.info(f"[Ngrok] Tunnel created successfully: {self.tunnel.public_url}")
            return self.tunnel.public_url
        except Exception as e:
            logger.error(f"[Ngrok] Tunnel creation failed on port {port}: {e}")
            raise PreviewError(
                f"Ngrok connection failed on port {port}. "
                "Verify NGROK_AUTHTOKEN is set correctly: "
                f"{e}"
            )

    async def stop(self) -> None:
        """Stop ngrok tunnel."""
        if self.tunnel:
            logger.info(f"[Ngrok] Disconnecting tunnel {self.tunnel.public_url}")
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, ngrok.disconnect, self.tunnel.public_url)
            except Exception as e:
                logger.warning(f"[Ngrok] Error disconnecting tunnel: {e}")
                pass
            self.tunnel = None

    def url(self) -> Optional[str]:
        return self.tunnel.public_url if self.tunnel else None
