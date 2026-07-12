"""CLI script to test the OpenClaw LangGraph agent."""

import argparse
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Reconfigure stdout to handle unicode prints safely on Windows terminal
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

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


from rich.console import Console
console = Console()


def run_agent(prompt: str):
    console.print(f"[bold cyan]Invoking agent with prompt:[/bold cyan] {prompt!r}\n")
    
    inputs = {
        "messages": [("user", prompt)]
    }
    
    config = {"configurable": {"thread_id": "test-session"}}
    result = graph.invoke(inputs, config)
    
    console.print()
    from rich.panel import Panel
    from rich.table import Table
    
    final_resp = result.get("final_response")
    if final_resp:
        console.print(Panel(
            final_resp,
            title="[bold green]📥 Agent Final Response[/bold green]",
            border_style="green",
            padding=(1, 2)
        ))
    else:
        console.print(Panel(
            "[dim italic]No final response text in state. Final message might have been a tool call or empty.[/]",
            title="[bold red]⚠️ No Response[/bold red]",
            border_style="red",
            padding=(1, 2)
        ))
    
    # Render Tool execution log as a styled Table
    tool_outputs = result.get("tool_outputs") or []
    if tool_outputs:
        table = Table(
            title="🛠  Tool Executions Log",
            title_style="bold blue",
            border_style="blue",
            show_header=True,
            header_style="bold cyan"
        )
        table.add_column("Step", justify="center", style="dim")
        table.add_column("Tool Name", style="yellow")
        table.add_column("Arguments", style="white")
        table.add_column("Duration", justify="right", style="magenta")
        
        for idx, out in enumerate(tool_outputs, start=1):
            # Format arguments to keep them readable
            args_str = str(out['args'])
            if len(args_str) > 80:
                args_str = args_str[:77] + "..."
                
            table.add_row(
                str(idx),
                out['tool'],
                args_str,
                f"{out['execution_time']:.3f}s"
            )
        console.print()
        console.print(table)
    else:
        console.print()
        console.print("[dim italic](No tools were executed during this run)[/]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test OpenClaw LangGraph ReAct agent.")
    parser.add_argument(
        "prompt", 
        type=str, 
        nargs="?", 
        default="search about prince sahu and then save it in form of md file in the d:/princesahu",
        help="The query/instruction to send to the agent."
    )
    args = parser.parse_args()
    
    run_agent(args.prompt)
