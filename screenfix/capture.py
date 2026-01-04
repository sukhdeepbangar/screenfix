"""Screen capture functionality using native macOS screencapture."""

import subprocess
import tempfile
import shutil
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import config


def capture_screen_region() -> Optional[str]:
    """
    Capture a screen region using macOS native screencapture.

    Returns:
        Path to captured image in temp directory, or None if cancelled
    """
    # Generate unique filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_path = os.path.join(
        tempfile.gettempdir(), f"screenfix_capture_{timestamp}.png"
    )

    try:
        # Run screencapture in interactive selection mode
        # -i: interactive mode (user selects region)
        # -x: no sound
        # -s: only mouse selection (no window mode)
        result = subprocess.run(
            ["screencapture", "-i", "-x", "-s", temp_path],
            capture_output=True,
            timeout=120,  # 2 minute timeout
        )

        # Check if file was created (user didn't cancel)
        if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
            return temp_path

        # User cancelled
        return None

    except subprocess.TimeoutExpired:
        return None
    except Exception as e:
        print(f"Screen capture failed: {e}")
        return None


def save_screenshot(temp_path: str, filename: Optional[str] = None) -> str:
    """
    Move screenshot from temp location to save directory.

    Args:
        temp_path: Path to temporary screenshot
        filename: Optional custom filename

    Returns:
        Final save path
    """
    # Ensure save directory exists
    config.ensure_directories()

    # Generate filename if not provided
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"

    final_path = os.path.join(config.save_directory, filename)
    shutil.move(temp_path, final_path)

    return final_path


def get_screenshots() -> list[dict]:
    """
    List all screenshots in the save directory.

    Returns:
        List of screenshot info dicts with path and timestamp
    """
    save_dir = Path(config.save_directory)
    if not save_dir.exists():
        return []

    screenshots = []
    for f in sorted(save_dir.glob("*.png"), key=lambda x: x.stat().st_mtime, reverse=True):
        screenshots.append({
            "path": str(f),
            "filename": f.name,
            "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        })

    return screenshots


def get_last_screenshot() -> Optional[dict]:
    """
    Get the most recent screenshot.

    Returns:
        Screenshot info dict or None if no screenshots exist
    """
    screenshots = get_screenshots()
    return screenshots[0] if screenshots else None


def cleanup_temp_file(temp_path: str):
    """Remove a temporary screenshot file."""
    try:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    except OSError:
        pass
