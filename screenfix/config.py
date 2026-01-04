"""Configuration management for ScreenFix."""

import os
import json
from pathlib import Path

DEFAULT_CONFIG = {
    "save_directory": "./screenfix/screenshots",
    "tasks_file": "./screenfix/tasks/screenfix-tasks.md",
}

CONFIG_DIR = Path.home() / ".config" / "screenfix"
CONFIG_FILE = CONFIG_DIR / "config.json"


class Config:
    """Configuration manager for ScreenFix."""

    def __init__(self):
        self._config = DEFAULT_CONFIG.copy()
        self._load()

    def _load(self):
        """Load configuration from file."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    saved = json.load(f)
                    self._config.update(saved)
            except (json.JSONDecodeError, IOError):
                pass

    def save(self):
        """Save configuration to file."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(self._config, f, indent=2)

    @property
    def save_directory(self) -> str:
        """Directory where screenshots are saved."""
        return self._config["save_directory"]

    @save_directory.setter
    def save_directory(self, value: str):
        self._config["save_directory"] = os.path.expanduser(value)
        self.save()

    @property
    def tasks_file(self) -> str:
        """Path to the tasks.md file."""
        return self._config["tasks_file"]

    @tasks_file.setter
    def tasks_file(self, value: str):
        self._config["tasks_file"] = os.path.expanduser(value)
        self.save()

    def ensure_directories(self):
        """Ensure save and tasks directories exist."""
        Path(self.save_directory).mkdir(parents=True, exist_ok=True)
        Path(self.tasks_file).parent.mkdir(parents=True, exist_ok=True)


# Global config instance
config = Config()
