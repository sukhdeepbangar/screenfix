"""MCP server for ScreenFix - daemon control only."""

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


STATE_FILE = Path.home() / ".config" / "screenfix" / "state.json"


def get_daemon_state() -> dict:
    """Read the daemon state file."""
    if not STATE_FILE.exists():
        return {"running": False, "listening": False}

    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)

        pid = state.get("pid")
        if pid:
            try:
                os.kill(pid, 0)
                state["running"] = True
            except OSError:
                state["running"] = False
        else:
            state["running"] = False

        return state
    except (json.JSONDecodeError, IOError):
        return {"running": False, "listening": False}


def start_daemon() -> tuple[bool, str]:
    """Start the daemon as a background process."""
    state = get_daemon_state()
    if state.get("running"):
        return True, "Daemon is already running"

    try:
        log_dir = Path.home() / ".config" / "screenfix"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "daemon.log"

        with open(log_file, "a") as log:
            subprocess.Popen(
                [sys.executable, "-m", "screenfix.daemon"],
                cwd=os.getcwd(),
                stdout=log,
                stderr=log,
                start_new_session=True,
            )

        time.sleep(0.5)

        new_state = get_daemon_state()
        if new_state.get("running"):
            return True, f"Daemon started (PID: {new_state.get('pid')}). Use Cmd+Ctrl+Shift+4 to capture."
        else:
            return True, f"Daemon starting... Check logs at {log_file}"

    except Exception as e:
        return False, f"Failed to start daemon: {e}"


def stop_daemon() -> tuple[bool, str]:
    """Stop the daemon."""
    state = get_daemon_state()
    if not state.get("running"):
        return True, "Daemon is not running"

    pid = state.get("pid")
    if pid:
        try:
            os.kill(pid, 15)
            return True, "Daemon stopped"
        except OSError as e:
            return False, f"Failed to stop daemon: {e}"

    return False, "Could not find daemon PID"


def create_server() -> Server:
    """Create the MCP server."""
    server = Server("screenfix")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="start_daemon",
                description="Start ScreenFix daemon. Use Cmd+Ctrl+Shift+4 to capture screenshots instantly.",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="stop_daemon",
                description="Stop the ScreenFix daemon",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="get_status",
                description="Get ScreenFix daemon status",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:

        if name == "start_daemon":
            success, message = start_daemon()
            return [TextContent(type="text", text=message)]

        elif name == "stop_daemon":
            success, message = stop_daemon()
            return [TextContent(type="text", text=message)]

        elif name == "get_status":
            state = get_daemon_state()
            status = "Running" if state.get("running") else "Not running"
            text = f"""ScreenFix Status:
- Daemon: {status}

Use Cmd+Ctrl+Shift+4 to capture (instant, no delay)
Screenshots saved to: ./screenfix/screenshots/
Tasks saved to: ./screenfix/tasks/screenfix-tasks.md"""
            return [TextContent(type="text", text=text)]

        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    return server


async def run_server():
    """Run the MCP server."""
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    """Main entry point."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
