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
                try:
                    for t in ngrok.get_tunnels():
                        try:
                            ngrok.disconnect(t.public_url)
                        except Exception:
                            pass
                except Exception:
                    pass
                try:
                    return ngrok.connect(f"127.0.0.1:{port}", "http", host_header="rewrite")
                except Exception as err:
                    err_str = str(err)
                    if "ERR_NGROK_334" in err_str or "already online" in err_str:
                        logger.warning("[Ngrok] Static endpoint conflict (ERR_NGROK_334). Killing stale local ngrok processes and retrying...")
                        try:
                            import subprocess
                            if os.name == 'nt':
                                subprocess.run(["taskkill", "/F", "/IM", "ngrok.exe"], capture_output=True)
                            else:
                                subprocess.run(["pkill", "-f", "ngrok"], capture_output=True)
                        except Exception:
                            pass
                        import time
                        time.sleep(3)
                        return ngrok.connect(f"127.0.0.1:{port}", "http", host_header="rewrite")
                    raise

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
                def do_stop():
                    try:
                        ngrok.disconnect(self.tunnel.public_url)
                    except Exception:
                        pass
                    try:
                        ngrok.kill()
                    except Exception:
                        pass
                await loop.run_in_executor(None, do_stop)
            except Exception as e:
                logger.warning(f"[Ngrok] Error disconnecting tunnel: {e}")
            self.tunnel = None

    def url(self) -> Optional[str]:
        return self.tunnel.public_url if self.tunnel else None
