import os
import sys
import asyncio
import logging
from pathlib import Path

# Insert project root into sys.path to resolve imports correctly
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Setup a clean logger to print verification logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("openclaw-agent")

from app.runtime.manager import RuntimeManager
from app.runtime.config import RuntimeConfig

async def main():
    logger.info("Initializing RuntimeManager...")
    config = RuntimeConfig()
    manager = RuntimeManager(config)
    
    # 1. Start lifecycle initialization (ensures image builds and cleans dangling sessions)
    await manager.initialize()
    
    session_id = "live_agent_session"
    logger.info(f"Step 1: Creating runtime session '{session_id}'...")
    
    # 2. Spin up container and allocate volume mounts/ports
    session = await manager.create_session(session_id)
    logger.info(f"✓ Session created. Container ID: {session.container_id[:12]}")
    logger.info(f"✓ Workspace host directory: {session.workspace}")
    
    # 3. Write the prime number calculation script to the workspace
    prime_script = """
def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

primes = [x for x in range(51) if is_prime(x)]
print(f"Prime numbers from 0-50: {primes}")
"""
    script_path = Path(session.workspace) / "prime.py"
    logger.info(f"Step 2: Writing prime.py to workspace at: {script_path}")
    script_path.write_text(prime_script, encoding="utf-8")
    
    # 4. Execute the python code inside the container namespace
    logger.info("Step 3: Executing 'python prime.py' inside the container...")
    result = await manager.execute(session_id, "python prime.py")
    
    logger.info(f"✓ Exit Code: {result.exit_code}")
    logger.info(f"✓ Standard Output:\n{result.stdout.strip()}")
    if result.stderr.strip():
        logger.info(f"✓ Standard Error:\n{result.stderr.strip()}")
        
    # 5. Clean up container session and workspace
    logger.info("Step 4: Tearing down container session and workspace...")
    await manager.destroy_session(session_id, keep_workspace=True)
    logger.info("✓ Session and workspace cleaned up successfully.")
    
    # 6. Final shutdown hook
    await manager.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
