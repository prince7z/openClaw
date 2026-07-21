import sys
import os
import time
from pathlib import Path

# Reconfigure stdout to handle unicode prints safely on Windows terminal
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

# Add project root to path so 'app' can be imported when running script directly
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

# Load local environment variables from .env file
env_path = project_root / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ[key.strip()] = val.strip().strip("'\"")

# Import sandbox tools
from app.tools.sandbox.commands import (
    execute_bash_command,
    execute_python_code,
    execute_node_code,
    start_sandbox_server,
    stop_sandbox_server,
    get_sandbox_preview,
)

# Import filesystem tools
from app.tools.filesystem import (
    write_file,
    read_file,
    list_files,
    search_files,    
    )

# Target directory for React app files in the session workspace
app_dir = project_root / "workspaces" / "default_sandbox_session" / "react-app"

print("=" * 60)
print("1. Testing execute_python_code")
print("=" * 60)
py_res = execute_python_code.invoke({"code": "import sys, platform; print(f'Python {sys.version} on {platform.system()}')"})
print(py_res)

print("\n" + "=" * 60)
print("2. Testing execute_node_code")
print("=" * 60)
node_res = execute_node_code.invoke({"code": "console.log('Node.js version:', process.version)"})
print(node_res)

print("\n" + "=" * 60)
print("3. Creating React Project files using Filesystem Tools (write_file)")
print("=" * 60)

# Create package.json
package_json = """{
  "name": "react-demo",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host 0.0.0.0 --port 8000",
    "build": "vite build"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "vite": "^5.0.0"
  }
}"""
print("Writing package.json...")
print(write_file.invoke({"path": str(app_dir / "package.json"), "content": package_json}))

# Create vite.config.js
vite_config = """import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    host: '0.0.0.0',
    port: 8000,
    allowedHosts: true
  }
})"""
print("Writing vite.config.js...")
print(write_file.invoke({"path": str(app_dir / "vite.config.js"), "content": vite_config}))

# Create index.html
index_html = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <title>React Sandbox App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>"""
print("Writing index.html...")
print(write_file.invoke({"path": str(app_dir / "index.html"), "content": index_html}))

# Create src/main.jsx
main_jsx = """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)"""
print("Writing src/main.jsx...")
print(write_file.invoke({"path": str(app_dir / "src" / "main.jsx"), "content": main_jsx}))

# Create initial src/App.jsx
initial_app_jsx = """import React from 'react'

export default function App() {
  return (
    <div style={{ fontFamily: 'sans-serif', padding: '2rem', textAlign: 'center' }}>
      <h1>OpenClaw React Sandbox Demo</h1>
      <p>Initial component state inside container sandbox.</p>
    </div>
  )
}"""
print("Writing src/App.jsx...")
print(write_file.invoke({"path": str(app_dir / "src" / "App.jsx"), "content": initial_app_jsx}))

print("\nRunning npm install inside container via execute_bash_command...")
npm_res = execute_bash_command.invoke({"command": "cd react-app && npm install --no-audit --no-fund"})
print(npm_res)

print("\n" + "=" * 60)
print("4. Updating React Component (src/App.jsx) using write_file")
print("=" * 60)
updated_app_jsx = """import React, { useState } from 'react'

export default function App() {
  const [count, setCount] = useState(0)
  return (
    <div style={{ 
      fontFamily: 'system-ui, sans-serif', 
      padding: '3rem', 
      textAlign: 'center', 
      background: '#0f172a', 
      color: '#f8fafc', 
      minHeight: '100vh' 
    }}>
      <h1 style={{ color: '#38bdf8' }}>⚡ Live React App (Managed by Filesystem Tools)</h1>
      <p style={{ fontSize: '1.2rem', color: '#94a3b8' }}>
        This React component was created and edited using native OpenClaw Filesystem tools!
      </p>
      <button 
        onClick={() => setCount(c => c + 1)}
        style={{ 
          marginTop: '1.5rem',
          padding: '12px 24px', 
          fontSize: '18px', 
          borderRadius: '8px', 
          cursor: 'pointer', 
          background: '#0284c7', 
          color: '#ffffff',
          border: 'none', 
          fontWeight: 'bold',
          boxShadow: '0 4px 14px 0 rgba(2, 132, 199, 0.39)'
        }}
      >
        Interactive Counter: {count}
      </button>
    </div>
  )
}"""
print("Updating src/App.jsx via write_file...")
print(write_file.invoke({"path": str(app_dir / "src" / "App.jsx"), "content": updated_app_jsx}))

print("\nVerifying written content via read_file...")
read_res = read_file.invoke({"path": str(app_dir / "src" / "App.jsx")})
print(f"File verified ({read_res.get('data', {}).get('line_count', 0)} lines read successfully).")

print("\n" + "=" * 60)
print("5. Starting React Dev Server & Auto-Fetching Preview URLs (start_sandbox_server)")
print("=" * 60)
server_res = start_sandbox_server.invoke({
    "command": "cd react-app && npm run dev",
    "port": 8000
})
print(server_res)

print("\n" + "=" * 60)
print("6. Stopping Sandbox Server (stop_sandbox_server)")
print("=" * 60)
stop_res = stop_sandbox_server.invoke({"port": 8000})
print(stop_res)

print("\n" + "=" * 60)
print("Filesystem Tools & Sandbox Tools Integration Complete!")
print("=" * 60)
