import socket
import urllib.parse
import os
from pathlib import Path

# Load local environment variables from .env file
env_path = Path(__file__).resolve().parents[1] / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            val = val.strip().strip("'\"")
            os.environ[key.strip()] = val

hosts = {
    "Telegram API": "https://api.telegram.org",
    "OpenRouter API": "https://openrouter.ai/api/v1",
    "Qdrant URL": os.getenv("QDRANT_URL", "http://localhost:6333"),
    "Infinity URL": os.getenv("INFINITY_URL", "http://localhost:7997"),
}

def test_connection(name, url_str):
    parsed = urllib.parse.urlparse(url_str)
    host = parsed.hostname
    port = parsed.port
    if not port:
        port = 443 if parsed.scheme == "https" else 80
        
    print(f"Testing {name}: {host}:{port} ...", end=" ", flush=True)
    try:
        # Resolve hostname
        ip = socket.gethostbyname(host)
        # Attempt TCP connection
        with socket.create_connection((ip, port), timeout=5) as s:
            print(f"SUCCESS (Resolved to {ip})")
    except Exception as e:
        print(f"FAILED: {e}")

for name, url_str in hosts.items():
    test_connection(name, url_str)
