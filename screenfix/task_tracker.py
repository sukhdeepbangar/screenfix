"""Task tracker for managing tasks.md file."""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from .config import config


def add_task(instruction: str, screenshot_path: Optional[str] = None) -> str:
    """
    Add a task to the tasks.md file.

    Args:
        instruction: Task instruction text
        screenshot_path: Optional path to related screenshot

    Returns:
        The formatted task entry that was added
    """
    tasks_path = Path(config.tasks_file)

    # Create parent directory if needed
    tasks_path.parent.mkdir(parents=True, exist_ok=True)

    # Create file with header if it doesn't exist
    if not tasks_path.exists():
        with open(tasks_path, "w") as f:
            f.write("# Tasks for Claude Code\n\n")

    # Format the task entry
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Build task lines
    task_lines = [f"- [ ] {instruction.strip()}"]

    # Add screenshot reference if provided
    if screenshot_path:
        task_lines.append(f"  - Screenshot: `{screenshot_path}`")

    task_lines.append(f"  - Added: {timestamp}")
    task_lines.append("")  # Blank line after entry

    task_entry = "\n".join(task_lines) + "\n"

    # Append to file
    with open(tasks_path, "a") as f:
        f.write(task_entry)

    return task_entry


def get_tasks() -> list[dict]:
    """
    Read all tasks from tasks.md.

    Returns:
        List of task dictionaries with keys: text, completed, screenshot, added
    """
    tasks_path = Path(config.tasks_file)

    if not tasks_path.exists():
        return []

    tasks = []
    current_task = None

    with open(tasks_path, "r") as f:
        for line in f:
            # Check for task line
            if line.startswith("- [ ] ") or line.startswith("- [x] "):
                if current_task:
                    tasks.append(current_task)
                completed = line.startswith("- [x] ")
                current_task = {
                    "text": line[6:].strip(),
                    "completed": completed,
                    "screenshot": None,
                    "added": None,
                }
            elif current_task and line.strip().startswith("- Screenshot:"):
                # Extract screenshot path
                path = line.strip()[14:].strip().strip("`")
                current_task["screenshot"] = path
            elif current_task and line.strip().startswith("- Added:"):
                # Extract timestamp
                current_task["added"] = line.strip()[9:].strip()

        # Don't forget the last task
        if current_task:
            tasks.append(current_task)

    return tasks


def get_pending_tasks() -> list[dict]:
    """Get only incomplete tasks."""
    return [t for t in get_tasks() if not t["completed"]]


def mark_task_complete(task_text: str) -> bool:
    """
    Mark a task as complete by its text.

    Args:
        task_text: The task text to find and mark complete

    Returns:
        True if task was found and marked, False otherwise
    """
    tasks_path = Path(config.tasks_file)

    if not tasks_path.exists():
        return False

    with open(tasks_path, "r") as f:
        content = f.read()

    # Find and replace the checkbox
    search = f"- [ ] {task_text}"
    replace = f"- [x] {task_text}"

    if search in content:
        content = content.replace(search, replace, 1)
        with open(tasks_path, "w") as f:
            f.write(content)
        return True

    return False
