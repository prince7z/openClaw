"""CLI script to test the OpenClaw LangGraph agent."""

import argparse
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Load local environment variables from .env file
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            val = val.strip().strip("'\"")
            os.environ[key.strip()] = val

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app.agent import graph


def run_agent(prompt: str):
    print(f"Invoking agent with prompt: {prompt!r}\n")
    
    inputs = {
        "messages": [("user", prompt)]
    }
    config = {"configurable": {"thread_id": "test-session"}}
    
    # Run the compiled ReAct graph
    result = graph.invoke(inputs, config)
    
    print("\n[bold green]--- Final Response ---[/]")
    print(result.get("final_response", "(No final response content returned)"))
    
    print("\n[bold blue]--- Tool Executions Log ---[/]")
    tool_outputs = result.get("tool_outputs") or []
    if not tool_outputs:
        print("(No tools were executed)")
    for idx, out in enumerate(tool_outputs, start=1):
        print(f"[{idx}] Tool: [yellow]{out['tool']}[/]")
        print(f"    Args: {out['args']}")
        print(f"    Execution Time: {out['execution_time']:.3f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test OpenClaw LangGraph ReAct agent.")
    parser.add_argument(
        "prompt", 
        type=str, 
        nargs="?", 
        default="in cuurent directory you will find report file wht is itthe",
        help="The query/instruction to send to the agent."
    )
    args = parser.parse_args()
    
    run_agent(args.prompt)
