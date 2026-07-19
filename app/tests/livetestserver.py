import os
import sys
import asyncio
import logging
from pathlib import Path

# Insert project root into sys.path to resolve imports correctly
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("openclaw-agent")

from app.runtime.manager import RuntimeManager
from app.runtime.config import RuntimeConfig

async def main():
    logger.info("Initializing RuntimeManager...")
    config = RuntimeConfig()
    manager = RuntimeManager(config)
    
    # 1. Start lifecycle initialization (ensures Aether-runtime:A-ONE image is built/ensure)
    await manager.initialize()
    
    session_id = "react_demo_session"
    logger.info(f"Step 1: Creating runtime session '{session_id}'...")
    
    # 2. Spin up container and allocate volume mounts/ports
    session = await manager.create_session(session_id)
    logger.info(f"✓ Session created. Container ID: {session.container_id[:12]}")
    logger.info(f"✓ Workspace host directory: {session.workspace}")
    logger.info(f"✓ Mapped host port: {session.host_port}")
    
    # 3. Create a React project using Vite
    logger.info("Step 2: Scaffolding React project using create-vite...")
    res = await manager.execute(
        session_id=session_id,
        command="npx --yes create-vite@latest my-react-app --template react"
    )
    if res.exit_code != 0:
        logger.error(f"Vite scaffolding failed: {res.stderr}")
        return
    logger.info("✓ Scaffolding complete.")

    # 4. Install npm dependencies
    logger.info("Step 3: Installing npm dependencies (running npm install)...")
    res = await manager.execute(
        session_id=session_id,
        command="npm install",
        cwd="my-react-app"
    )
    if res.exit_code != 0:
        logger.error(f"npm install failed: {res.stderr}")
        return
    logger.info("✓ Dependencies installed successfully.")
    
    # Write allowedHosts configuration to vite.config.js to allow Ngrok tunnels
    vite_config = """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: true
  }
})
"""
    config_path = Path(session.workspace) / "my-react-app" / "vite.config.js"
    logger.info(f"Writing allowedHosts config to {config_path}")
    config_path.write_text(vite_config, encoding="utf-8")

    # 5. Start the Vite dev server in the background
    logger.info("Step 4: Starting Vite dev server in the background...")
    await manager.start_server(
        session_id=session_id,
        command="cd my-react-app && npm run dev -- --host 0.0.0.0 --port 8000",
        port=8000
    )
    
    # Wait for the dev server to boot
    logger.info("Waiting 3 seconds for Vite server to startup...")
    await asyncio.sleep(3)
    
    # Check server process status
    session = await manager.status(session_id)
    if session.process and session.process.status == "running":
        logger.info("✓ Vite dev server is running.")
    else:
        logger.warning(f"Vite server status check: {session.process}")

    # 6. Retrieve public and local preview URLs
    logger.info("Step 5: Fetching preview URLs...")
    local_url = f"http://localhost:{session.host_port}"
    
    # Attempt to start Ngrok tunnel
    public_url = None
    try:
        public_url = await manager.get_preview_url(session_id)
    except Exception as e:
        logger.warning(f"Could not initialize Ngrok tunnel (check NGROK_AUTHTOKEN): {e}")

    logger.info("==================================================")
    logger.info("🚀 REACT DEV SERVER IS ONLINE!")
    logger.info(f"👉 Local URL:   {local_url}")
    if public_url:
        logger.info(f"👉 Public URL:  {public_url}")
    else:
        logger.info("👉 Public URL:  Not available (Ngrok was not configured or failed)")
    logger.info("==================================================")

    # 7. Keep the server active for 40 seconds to allow interaction
    logger.info("The React dev server will remain online for 40 seconds. Feel free to visit the link!")
    for remaining in range(40, 0, -10):
        logger.info(f"Time remaining: {remaining} seconds...")
        await asyncio.sleep(10)
        
    # 8. Clean up session and workspace
    logger.info("Step 6: Tearing down container session and clean up...")
    await manager.destroy_session(session_id, keep_workspace=True)
    logger.info("✓ Cleanup complete. Sandbox container removed.")
    
    # Final shutdown
    await manager.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
