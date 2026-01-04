# ScreenFix - Screenshot Tool for Claude Code

Capture screenshots instantly and create tasks for Claude Code.

## Quick Start

1. **Install**: Run in your project directory:
   ```bash
   npx create-screenfix
   ```

2. **Restart Claude Code** to load the MCP server

3. **Start the daemon**: Run `/screenfix-start`

4. **Capture**: Press **Cmd+Ctrl+Shift+4** and select an area

5. **Annotate**: Add instructions in the popup and click Save

6. **Execute**: Run `/screenfix-tasks-next` or `/screenfix-tasks-yolo`

## Commands

| Command | Description |
|---------|-------------|
| `/screenfix-start` | Start the screenshot daemon |
| `/screenfix-stop` | Stop the daemon |
| `/screenfix-status` | Check status |
| `/screenfix-list-tasks` | View all tasks |
| `/screenfix-tasks-next` | Execute next pending task |
| `/screenfix-tasks-yolo` | Execute all pending tasks |

## CLI Commands

```bash
npx create-screenfix          # Install ScreenFix
npx create-screenfix doctor   # Diagnose issues
npx create-screenfix update   # Update to latest
npx create-screenfix uninstall # Remove from project
```

## File Locations

- Screenshots: `./screenfix/screenshots/`
- Tasks: `./screenfix/tasks/screenfix-tasks.md`

## How It Works

```
Cmd+Ctrl+Shift+4  ->  Clipboard  ->  Daemon detects  ->  Annotation popup
                                                              |
                                                    Save screenshot + task
                                                              |
                                                    Claude reads via MCP
```

No special permissions required!
