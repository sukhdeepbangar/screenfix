# ScreenFix - Screenshot Tool for Claude Code

Capture screenshots instantly and create tasks for Claude Code.

## Quick Start

1. **Start the daemon**: Ask Claude to `start_daemon`

2. **Capture**: Press **Cmd+Ctrl+Shift+4** and select an area
   - Instant capture, no preview delay!

3. **Annotate**: Add instructions in the popup and click Save

4. **Review**: Ask Claude to check your last screenshot

## Installation

```bash
pip install -e /path/to/screenfix
```

Copy `.mcp.json` to your project:
```bash
cp /path/to/screenfix/.mcp.json ./
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `start_daemon` | Start the screenshot daemon |
| `stop_daemon` | Stop the daemon |
| `get_status` | Check status |
| `get_last_screenshot` | Get most recent screenshot + task |
| `list_screenshots` | List all screenshots |
| `get_tasks` | Get tasks |
| `complete_task` | Mark task as done |

## File Locations

- Screenshots: `./screenfix/screenshots/`
- Tasks: `./screenfix/tasks/screenfix-tasks.md`

## How It Works

```
Cmd+Ctrl+Shift+4  →  Clipboard  →  Daemon detects  →  Annotation popup
                                                              ↓
                                                    Save screenshot + task
                                                              ↓
                                                    Claude reads via MCP
```

No special permissions required!
