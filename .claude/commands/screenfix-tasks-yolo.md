---
allowed-tools: mcp__screenfix__get_tasks, mcp__screenfix__get_last_screenshot, mcp__screenfix__read_screenshot, mcp__screenfix__complete_task, Read, Edit, Write, Bash, Glob, Grep
description: Execute all pending ScreenFix tasks automatically
---

Get all pending tasks using `mcp__screenfix__get_tasks` with `pending_only: true`.

For each pending task:
1. Read the associated screenshot using `mcp__screenfix__read_screenshot`
2. Analyze the screenshot and the task instructions
3. Implement the fix described in the instructions
4. Mark the task complete using `mcp__screenfix__complete_task`

Execute all tasks without asking for confirmation. Just do it.
