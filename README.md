# ScreenFix

Capture screenshots and create tasks for Claude Code with a single hotkey.

## Installation

```bash
npx create-screenfix
```

This will:
- Install the Python dependencies
- Configure the MCP server
- Add slash commands to your project

**Restart Claude Code** after installation to load the MCP server.

## Usage

### 1. Start the daemon

In Claude Code, run:
```
/screenfix-start
```

### 2. Capture a screenshot

Press **Cmd+Ctrl+Shift+4** and select an area. An annotation popup will appear.

### 3. Add instructions

Type what you want Claude to do with this screenshot and click **Save**.

### 4. Execute tasks

Run one of these commands in Claude Code:
- `/screenfix-tasks-next` - Execute the next pending task
- `/screenfix-tasks-yolo` - Execute all pending tasks automatically

## Commands

| Command | Description |
|---------|-------------|
| `/screenfix-start` | Start the screenshot daemon |
| `/screenfix-stop` | Stop the daemon |
| `/screenfix-status` | Check daemon status |
| `/screenfix-list-tasks` | View all tasks and screenshots |
| `/screenfix-tasks-next` | Execute next pending task |
| `/screenfix-tasks-yolo` | Execute all pending tasks |

## CLI Commands

```bash
npx create-screenfix          # Install ScreenFix
npx create-screenfix doctor   # Diagnose issues
npx create-screenfix update   # Update to latest
npx create-screenfix uninstall # Remove from project
```

## Requirements

- macOS (uses native screenshot functionality)
- Python 3.10+
- Claude Code

## How It Works

```
Cmd+Ctrl+Shift+4  →  Clipboard  →  Daemon detects  →  Annotation popup
                                                            ↓
                                                  Save screenshot + task
                                                            ↓
                                                  Claude reads & executes
```

No special permissions required - uses the standard macOS screenshot-to-clipboard functionality.

## File Locations

- Screenshots: `./screenfix/screenshots/`
- Tasks: `./screenfix/tasks/screenfix-tasks.md`

## License

MIT
