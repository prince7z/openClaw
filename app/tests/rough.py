import sys
from pathlib import Path

# Reconfigure stdout to handle unicode prints safely on Windows terminal
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

# Add project root to path so 'app' can be imported when running script directly
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Load local environment variables from .env file
env_path = Path(__file__).resolve().parents[2] / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            val = val.strip().strip("'\"")
            import os
            os.environ[key.strip()] = val

from app.tools.sandbox.commands import (  # noqa: E402
    execute_bash_command,
    execute_python_code,
    execute_node_code,
    start_sandbox_server,
    stop_sandbox_server,
    get_sandbox_preview,
)

#print(execute_bash_command.invoke({"command": "mkdir mydir ; ls"}))

config = {"configurable": {"thread_id": "tg-1833617010"}}

print("Stopping any existing server on port 3000...")
print(stop_sandbox_server.invoke({'port': 3000}, config=config))

print("Starting server on port 3000...")
print(start_sandbox_server.invoke({'get_preview': True, 'port': 3000, 'command': 'cd /workspace/react-app && npm start'}, config=config))

import time
print("Starting server on port 3000...")
print(start_sandbox_server.invoke({'get_preview': True, 'port': 3000, 'command': 'cd /workspace/react-app && npm start'}, config=config))
print("Waiting 15s for React dev server to finish compiling...")
time.sleep(15)
import requests
# Include the Ngrok-Skip-Browser-Warning header so ngrok bypasses its free-tier warning page
headers = {"Ngrok-Skip-Browser-Warning": "true"}
response = requests.get('https://nonadeptly-subconsular-verdie.ngrok-free.dev', headers=headers, verify=False)
print("Preview Response:", response)
print("Status Code:", response.status_code)
print("Keeping the script alive for 300 seconds so ngrok stays online...")
time.sleep(300)