"""MCP server implementation for ScreenFix.

This MCP server communicates with the standalone daemon via state files.
Run the daemon separately with: python -m screenfix.daemon
"""

import asyncio
import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
)

from .config import config
from .capture import get_screenshots, get_last_screenshot
from .task_tracker import get_tasks, get_pending_tasks, mark_task_complete


# State file location (shared with daemon)
STATE_FILE = Path.home() / ".config" / "screenfix" / "state.json"


def get_daemon_state() -> dict:
    """Read the daemon state file."""
    if not STATE_FILE.exists():
        return {"running": False, "listening": False}

    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)

        # Check if daemon is actually running
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
        # Create log directory
        log_dir = Path.home() / ".config" / "screenfix"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "daemon.log"

        # Start daemon as a background subprocess
        # Run from current working directory for project-relative paths
        cwd = os.getcwd()

        with open(log_file, "a") as log:
            process = subprocess.Popen(
                [sys.executable, "-m", "screenfix.daemon"],
                cwd=cwd,
                stdout=log,
                stderr=log,
                start_new_session=True,  # Detach from parent process
            )

        # Wait briefly for daemon to initialize
        time.sleep(0.5)

        # Check if it started successfully
        new_state = get_daemon_state()
        if new_state.get("running"):
            return True, f"Daemon started as background process (PID: {new_state.get('pid')}). Logs: {log_file}"
        else:
            return True, f"Daemon starting... Check logs at {log_file} if hotkey doesn't work."

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
            os.kill(pid, 15)  # SIGTERM
            return True, "Daemon stopped"
        except OSError as e:
            return False, f"Failed to stop daemon: {e}"

    return False, "Could not find daemon PID"


def create_server() -> Server:
    """Create and configure the MCP server."""
    server = Server("screenfix")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available tools."""
        return [
            Tool(
                name="start_daemon",
                description="Start the ScreenFix daemon for hotkey listening (Ctrl+Option+S). Runs as a background process.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="stop_daemon",
                description="Stop the ScreenFix daemon",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="get_status",
                description="Get the current status of ScreenFix (daemon running, screenshots count, pending tasks)",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="get_last_screenshot",
                description="Get the most recent screenshot with its image and any related task",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "include_image": {
                            "type": "boolean",
                            "description": "Whether to include the image data",
                            "default": True,
                        }
                    },
                    "required": [],
                },
            ),
            Tool(
                name="list_screenshots",
                description="List all screenshots in the save directory",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of screenshots to return",
                            "default": 10,
                        }
                    },
                    "required": [],
                },
            ),
            Tool(
                name="get_tasks",
                description="Get all tasks from tasks.md",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pending_only": {
                            "type": "boolean",
                            "description": "Only return incomplete tasks",
                            "default": False,
                        }
                    },
                    "required": [],
                },
            ),
            Tool(
                name="complete_task",
                description="Mark a task as complete in tasks.md",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_text": {
                            "type": "string",
                            "description": "The text of the task to mark complete",
                        }
                    },
                    "required": ["task_text"],
                },
            ),
            Tool(
                name="read_screenshot",
                description="Read a specific screenshot by path and return its image",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the screenshot file",
                        }
                    },
                    "required": ["path"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent | ImageContent]:
        """Handle tool calls."""

        if name == "start_daemon":
            success, message = start_daemon()
            return [TextContent(type="text", text=message)]

        elif name == "stop_daemon":
            success, message = stop_daemon()
            return [TextContent(type="text", text=message)]

        elif name == "get_status":
            state = get_daemon_state()
            screenshots = get_screenshots()
            tasks = get_pending_tasks()

            daemon_status = "Running" if state.get("running") else "Not running"
            listening = "Yes (Ctrl+Option+S)" if state.get("listening") else "No"

            text = f"""ScreenFix Status:
- Daemon: {daemon_status}
- Hotkey listening: {listening}
- Save directory: {config.save_directory}
- Tasks file: {config.tasks_file}
- Screenshots captured: {len(screenshots)}
- Pending tasks: {len(tasks)}

To start capturing, run: start_daemon"""

            return [TextContent(type="text", text=text)]

        elif name == "get_last_screenshot":
            include_image = arguments.get("include_image", True)
            screenshot = get_last_screenshot()

            if not screenshot:
                return [TextContent(type="text", text="No screenshots found. Capture one with Ctrl+Option+S after starting the daemon.")]

            result = []
            result.append(TextContent(
                type="text",
                text=f"Last screenshot:\n- Path: {screenshot['path']}\n- Captured: {screenshot['modified']}"
            ))

            if include_image and os.path.exists(screenshot["path"]):
                with open(screenshot["path"], "rb") as f:
                    image_data = base64.standard_b64encode(f.read()).decode("utf-8")
                result.append(ImageContent(
                    type="image",
                    data=image_data,
                    mimeType="image/png",
                ))

            # Also get related task if any
            tasks = get_tasks()
            for task in tasks:
                if task.get("screenshot") == screenshot["path"]:
                    result.append(TextContent(
                        type="text",
                        text=f"\nRelated task: {task['text']}\nStatus: {'Completed' if task['completed'] else 'Pending'}"
                    ))
                    break

            return result

        elif name == "list_screenshots":
            limit = arguments.get("limit", 10)
            screenshots = get_screenshots()[:limit]

            if not screenshots:
                return [TextContent(type="text", text="No screenshots found.")]

            lines = ["Screenshots:"]
            for i, s in enumerate(screenshots, 1):
                lines.append(f"{i}. {s['filename']} ({s['modified']})")
                lines.append(f"   Path: {s['path']}")

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "get_tasks":
            pending_only = arguments.get("pending_only", False)
            tasks = get_pending_tasks() if pending_only else get_tasks()

            if not tasks:
                msg = "No pending tasks." if pending_only else "No tasks found."
                return [TextContent(type="text", text=msg)]

            lines = ["Tasks:"]
            for i, task in enumerate(tasks, 1):
                status = "[x]" if task["completed"] else "[ ]"
                lines.append(f"{i}. {status} {task['text']}")
                if task.get("screenshot"):
                    lines.append(f"   Screenshot: {task['screenshot']}")
                if task.get("added"):
                    lines.append(f"   Added: {task['added']}")

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "complete_task":
            task_text = arguments.get("task_text", "")
            if not task_text:
                return [TextContent(type="text", text="Please provide the task text to mark complete.")]

            if mark_task_complete(task_text):
                return [TextContent(type="text", text=f"Task marked as complete: {task_text}")]
            else:
                return [TextContent(type="text", text=f"Task not found: {task_text}")]

        elif name == "read_screenshot":
            path = arguments.get("path", "")
            if not path or not os.path.exists(path):
                return [TextContent(type="text", text=f"Screenshot not found: {path}")]

            with open(path, "rb") as f:
                image_data = base64.standard_b64encode(f.read()).decode("utf-8")

            return [
                TextContent(type="text", text=f"Screenshot: {path}"),
                ImageContent(type="image", data=image_data, mimeType="image/png"),
            ]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    return server


async def run_server():
    """Run the MCP server."""
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    """Main entry point for MCP server."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
