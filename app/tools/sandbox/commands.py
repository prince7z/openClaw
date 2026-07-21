"""LangChain tool interfaces for the secure Docker container runtime sandbox."""

import asyncio
from typing import Optional
from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from concurrent.futures import ThreadPoolExecutor

from app.runtime.manager import RuntimeManager
from app.runtime.models import CommandResult

def run_async_sync(coro):
    """Run async coroutine synchronously inside synchronous LangChain tool handlers."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

    if loop.is_running():
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(lambda: asyncio.run(coro))
            return future.result()
    else:
        return loop.run_until_complete(coro)

def get_session_id(config: RunnableConfig) -> str:
    """Helper to extract chat/session ID from LangChain RunnableConfig."""
    configurable = config.get("configurable", {})
    thread_id = configurable.get("thread_id", "default_sandbox_session")
    # Clean thread prefix if it starts with 'tg-'
    return thread_id.replace("tg-", "")

@tool("execute_bash_command")
def execute_bash_command(command: str, cwd: Optional[str] = None, config: RunnableConfig = None) -> str:
    """Execute a bash shell command inside the secure container sandbox.

    Use this tool to compile files, run install commands, run test scripts,
    or manage directories/files directly in the workspace container.

    Args:
        command: The shell command to execute.
        cwd: Optional directory path relative to /workspace where command should run.
    """
    session_id = get_session_id(config)
    manager = RuntimeManager.get_instance()
    
    async def run():
        # Auto create or resume container session
        await manager.create_session(session_id)
        res = await manager.execute(session_id, command, cwd=cwd)
        if res.exit_code == 0:
           
            return f"Command execution succeeded (Exit Code: 0).\n--- stdout ---\n{res.stdout}"
        else:
            return f"Command execution failed (Exit Code: {res.exit_code}).\n--- stdout ---\n{res.stdout}\n--- stderr ---\n{res.stderr}"
            
    return run_async_sync(run())

@tool("execute_python_code")
def execute_python_code(code: str, cwd: Optional[str] = None, config: RunnableConfig = None) -> str:
    """Run a block of Python code inside the secure container sandbox.

    Use this tool to execute quick calculations, test python scripts,
    process data, or run code snippets.

    Args:
        code: Complete Python script/block of code to run.
        cwd: Optional directory path relative to /workspace.
    """
    session_id = get_session_id(config)
    manager = RuntimeManager.get_instance()
    
    async def run():
        await manager.create_session(session_id)
        res = await manager.run_python(session_id, code, cwd=cwd)
        if res.exit_code == 0:
            return f"Python execution succeeded.\n--- stdout ---\n{res.stdout}"
        else:
            return f"Python execution failed (Exit Code: {res.exit_code}).\n--- stdout ---\n{res.stdout}\n--- stderr ---\n{res.stderr}"

    return run_async_sync(run())

@tool("execute_node_code")
def execute_node_code(code: str, cwd: Optional[str] = None, config: RunnableConfig = None) -> str:
    """Run a block of Node.js code inside the secure container sandbox.

    Use this tool to execute quick javascript snippets, check syntax,
    or test Node features.

    Args:
        code: JavaScript/Node.js block of code to run.
        cwd: Optional directory path relative to /workspace.
    """
    session_id = get_session_id(config)
    manager = RuntimeManager.get_instance()
    
    async def run():
        await manager.create_session(session_id)
        res = await manager.run_node(session_id, code, cwd=cwd)
        if res.exit_code == 0:
            return f"Node.js execution succeeded.\n--- stdout ---\n{res.stdout}"
        else:
            return f"Node.js execution failed (Exit Code: {res.exit_code}).\n--- stdout ---\n{res.stdout}\n--- stderr ---\n{res.stderr}"

    return run_async_sync(run())

@tool("start_sandbox_server")
def start_sandbox_server(command: str, port: int = 8000, get_preview: bool = True, config: RunnableConfig = None) -> dict:
    """Start a long-running background/daemon server process inside the sandbox container, wait for HTTP readiness, and return preview URLs.

    Args:
        command: Command to start the server (e.g. 'cd react-app && npm run dev', 'python -m http.server 8000').
        port: The container port the server listens on (default: 8000).
        get_preview: Whether to automatically generate and return local/public preview URLs (default: True).
    """
    session_id = get_session_id(config)
    manager = RuntimeManager.get_instance()
    
    async def run():
        session = await manager.create_session(session_id)
        await manager.start_server(session_id, command, port)
        
        # Poll host port until server is verified ready over TCP/HTTP (up to 60s)
        is_ready = await manager.wait_for_server_ready(session_id, port=port, timeout=60)
        
        status = await manager.status(session_id)
        running = status.process and status.process.status == "running" and is_ready
        
        mapped_host_port = session.port_mappings.get(port, session.host_port)
        local_url = f"http://localhost:{mapped_host_port}" if mapped_host_port else None
        preview_url = None
        
        if get_preview and running:
            try:
                preview_url = await manager.get_preview_url(session_id, port=port)
            except Exception as e:
                preview_url = None

        if not is_ready:
            return {
                "success": False,
                "port": port,
                "error": f"Server process started, but did not respond to HTTP/socket requests on container port {port} within 60 seconds."
            }

        return {
            "success": True,
            "port": port,
            "local_url": local_url,
            "preview_url": preview_url,
        }

    return run_async_sync(run())

@tool("stop_sandbox_server")
def stop_sandbox_server(port: int, config: RunnableConfig = None) -> str:
    """Stop any background server process running in the container sandbox listening on the specified port.

    Args:
        port: The container port to stop listeners on.
    """
    session_id = get_session_id(config)
    manager = RuntimeManager.get_instance()
    
    async def run():
        await manager.create_session(session_id)
        await manager.stop_server(session_id, port)
        return f"Successfully stopped background server listening on container port {port}."

    return run_async_sync(run())

@tool("get_sandbox_preview")
def get_sandbox_preview(port: int = 8000, config: RunnableConfig = None) -> str:
    """Expose a public Ngrok tunnel preview URL and fetch host port mappings for any active server process.

    Args:
        port: Container port to inspect or expose (default: 8000).
    """
    session_id = get_session_id(config)
    manager = RuntimeManager.get_instance()
    
    async def run():
        session = await manager.create_session(session_id)
        status = await manager.status(session_id)
        mapped_host_port = session.port_mappings.get(port, session.host_port)
        local_url = f"http://localhost:{mapped_host_port}" if mapped_host_port else "not_mapped"
        
        try:
            public_url = await manager.get_preview_url(session_id, port=port)
        except Exception as e:
            public_url = f"Failed to start tunnel: {e}"
            
        return (
            f"Sandbox Network & Preview URLs:\n"
            f"- Container Internal Port: {port}\n"
            f"- Local Host URL: {local_url}\n"
            f"- Public Tunnel URL: {public_url}\n"
        )

    return run_async_sync(run())
