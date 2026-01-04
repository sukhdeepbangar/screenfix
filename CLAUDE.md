# ScreenFix - Screen Snipping Tool for Claude Code

ScreenFix lets you capture screen regions, add instructions, and create tasks for bug fixes.

## Installation

### 1. Install the package

```bash
pip install screenfix
# or install from source:
pip install -e /path/to/screenfix
```

### 2. Copy configuration to your project

Copy these files to your project root:

```bash
# MCP server configuration (required)
cp /path/to/screenfix/.mcp.json ./

# Slash commands (optional but recommended)
cp -r /path/to/screenfix/.claude ./
```

### 3. Add to .gitignore

Add these lines to your project's `.gitignore`:

```
screenfix/screenshots/
screenfix/tasks/
```

## Quick Start

1. **Start the daemon**: Type `/start-daemon` or ask Claude to start it

2. **Grant permissions** when prompted:
   - System Settings > Privacy & Security > Accessibility (for hotkeys)
   - System Settings > Privacy & Security > Screen Recording (for capture)

3. **Press Ctrl+Option+S** anywhere to capture a screen region

4. **Add instructions** in the popup window and click Save

5. **Review**: Type `/screenshot` or ask Claude to check your last screenshot

## Slash Commands

| Command | Description |
|---------|-------------|
| `/screenshot` | Get and analyze the last screenshot |
| `/start-daemon` | Start the hotkey daemon |
| `/stop-daemon` | Stop the daemon |
| `/status` | Check daemon status |
| `/tasks` | View and manage tasks |

## File Locations (Project-Relative)

- Screenshots: `./screenfix/screenshots/`
- Tasks: `./screenfix/tasks/screenfix-tasks.md`
- Config: `~/.config/screenfix/config.json`

All screenshots and tasks are stored within your project directory, making them easy to share or version control.

## MCP Tools

| Tool | Description |
|------|-------------|
| `start_daemon` | Start the hotkey daemon in a new Terminal |
| `stop_daemon` | Stop the daemon |
| `get_status` | Check if daemon is running |
| `get_last_screenshot` | Get most recent screenshot + related task |
| `list_screenshots` | List all captured screenshots |
| `get_tasks` | Get tasks from tasks.md |
| `complete_task` | Mark a task as done |
| `read_screenshot` | Read a specific screenshot by path |

## Architecture

```
┌─────────────────────────────────┐
│  ScreenFix Daemon (Terminal)    │  ← Runs separately
│  - Hotkey listener              │
│  - Screen capture               │
│  - Annotation window            │
└─────────────────────────────────┘
         ↓ writes state file
┌─────────────────────────────────┐
│  MCP Server                     │  ← Runs via Claude Code
│  - Reads screenshots            │
│  - Reads tasks                  │
│  - Can start/stop daemon        │
└─────────────────────────────────┘
```

## Troubleshooting

**Hotkey not working?**
1. Check Terminal has Accessibility permission
2. Restart the daemon after granting permission

**MCP not loading?**
1. Make sure `.mcp.json` exists in your project root
2. Verify screenfix is installed: `python3 -c "import screenfix"`
