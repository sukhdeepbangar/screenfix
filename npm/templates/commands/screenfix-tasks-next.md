---
allowed-tools: Read, Edit, Write, Bash, Glob, Grep
description: Execute the next pending ScreenFix task
---

1. Read the tasks file at `./screenfix/tasks/screenfix-tasks.md`
2. Find the FIRST pending task (line with `- [ ]`)

For that task:
1. The task line contains the screenshot path - read that screenshot using the Read tool
2. Analyze the screenshot and the task instructions
3. Implement the fix described in the instructions
4. Mark the task complete by editing the tasks file: change `- [ ]` to `- [x]`

Execute one task at a time.
