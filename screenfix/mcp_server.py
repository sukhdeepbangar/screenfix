"""MCP server for ScreenFix."""

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
from mcp.types import Tool, TextContent, ImageContent

from .config import config
from .task_tracker import get_tasks, get_pending_tasks, mark_task_complete


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


def get_screenshots() -> list[dict]:
    """Get list of screenshots."""
    save_dir = Path(config.save_directory)
    if not save_dir.exists():
        return []

    screenshots = []
    for f in save_dir.glob("*.png"):
        screenshots.append({
            "path": str(f),
            "filename": f.name,
            "modified": f.stat().st_mtime,
        })

    screenshots.sort(key=lambda x: x["modified"], reverse=True)
    return screenshots


def get_last_screenshot() -> dict | None:
    """Get the most recent screenshot."""
    screenshots = get_screenshots()
    return screenshots[0] if screenshots else None


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
                description="Get ScreenFix status",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="get_last_screenshot",
                description="Get the most recent screenshot with its image and related task",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "include_image": {
                            "type": "boolean",
                            "description": "Include image data",
                            "default": True,
                        }
                    },
                    "required": [],
                },
            ),
            Tool(
                name="list_screenshots",
                description="List all screenshots",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 10}
                    },
                    "required": [],
                },
            ),
            Tool(
                name="get_tasks",
                description="Get tasks from tasks.md",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pending_only": {"type": "boolean", "default": False}
                    },
                    "required": [],
                },
            ),
            Tool(
                name="complete_task",
                description="Mark a task as complete",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_text": {"type": "string", "description": "Task text to mark complete"}
                    },
                    "required": ["task_text"],
                },
            ),
            Tool(
                name="read_screenshot",
                description="Read a specific screenshot by path",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to screenshot"}
                    },
                    "required": ["path"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent | ImageContent]:

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

            status = "Running" if state.get("running") else "Not running"
            text = f"""ScreenFix Status:
- Daemon: {status}
- Screenshots: {len(screenshots)}
- Pending tasks: {len(tasks)}

Use Cmd+Ctrl+Shift+4 to capture (instant, no delay)"""
            return [TextContent(type="text", text=text)]

        elif name == "get_last_screenshot":
            include_image = arguments.get("include_image", True)
            screenshot = get_last_screenshot()

            if not screenshot:
                return [TextContent(type="text", text="No screenshots found. Use Cmd+Ctrl+Shift+4 to capture.")]

            result = [TextContent(type="text", text=f"Screenshot: {screenshot['path']}")]

            if include_image and os.path.exists(screenshot["path"]):
                with open(screenshot["path"], "rb") as f:
                    image_data = base64.standard_b64encode(f.read()).decode("utf-8")
                result.append(ImageContent(type="image", data=image_data, mimeType="image/png"))

            tasks = get_tasks()
            for task in tasks:
                if task.get("screenshot") == screenshot["path"]:
                    result.append(TextContent(
                        type="text",
                        text=f"\nTask: {task['text']}\nStatus: {'Done' if task['completed'] else 'Pending'}"
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
                lines.append(f"{i}. {s['filename']}")

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "get_tasks":
            pending_only = arguments.get("pending_only", False)
            tasks = get_pending_tasks() if pending_only else get_tasks()

            if not tasks:
                return [TextContent(type="text", text="No tasks found.")]

            lines = ["Tasks:"]
            for i, task in enumerate(tasks, 1):
                status = "[x]" if task["completed"] else "[ ]"
                lines.append(f"{i}. {status} {task['text']}")

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "complete_task":
            task_text = arguments.get("task_text", "")
            if mark_task_complete(task_text):
                return [TextContent(type="text", text=f"Completed: {task_text}")]
            return [TextContent(type="text", text=f"Task not found: {task_text}")]

        elif name == "read_screenshot":
            path = arguments.get("path", "")
            if not path or not os.path.exists(path):
                return [TextContent(type="text", text=f"Not found: {path}")]

            with open(path, "rb") as f:
                image_data = base64.standard_b64encode(f.read()).decode("utf-8")

            return [
                TextContent(type="text", text=f"Screenshot: {path}"),
                ImageContent(type="image", data=image_data, mimeType="image/png"),
            ]

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
