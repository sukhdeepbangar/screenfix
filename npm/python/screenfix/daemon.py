#!/usr/bin/env python3
"""
ScreenFix Daemon - Clipboard watcher for instant screenshot capture.

Watches the clipboard for new images and shows annotation window instantly.
Use Cmd+Ctrl+Shift+4 to capture screenshot to clipboard (no preview delay).

Run with: python -m screenfix.daemon
"""

import json
import os
import queue
import signal
import sys
from datetime import datetime
from pathlib import Path

from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSEventMaskAny,
)
from Foundation import NSDate, NSDefaultRunLoopMode

from .config import config


# State file for communication with MCP server
STATE_FILE = Path.home() / ".config" / "screenfix" / "state.json"


def update_state(listening: bool = None, last_capture: str = None):
    """Update the state file for MCP server to read."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    state = {"pid": os.getpid(), "listening": False}

    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    state["pid"] = os.getpid()
    if listening is not None:
        state["listening"] = listening
    if last_capture is not None:
        state["last_capture"] = last_capture
        state["last_capture_time"] = datetime.now().isoformat()

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def clear_state():
    """Clear the state file on exit."""
    if STATE_FILE.exists():
        try:
            os.remove(STATE_FILE)
        except OSError:
            pass


class ScreenFixDaemon:
    """Daemon that watches clipboard for screenshots."""

    def __init__(self):
        self._running = False
        self._clipboard_watcher = None
        self._app = None
        self._main_thread_queue = queue.Queue()

    def _on_clipboard_image(self, image_path: str):
        """Called when a new image is detected on clipboard."""
        print(f"Screenshot detected: {image_path}", file=sys.stderr)
        self._main_thread_queue.put(image_path)

    def _process_main_thread_queue(self):
        """Process any pending work on the main thread."""
        try:
            while True:
                image_path = self._main_thread_queue.get_nowait()
                self._show_annotation(image_path)
        except queue.Empty:
            pass

    def _show_annotation(self, image_path: str):
        """Show the annotation window. Must be called from main thread."""
        from .annotation_window import show_annotation_window
        show_annotation_window(image_path)

    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def handle_signal(signum, frame):
            print(f"\nShutting down...", file=sys.stderr)
            self.stop()

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

    def start(self):
        """Start the daemon."""
        if self._running:
            return

        self._running = True
        config.ensure_directories()

        # Initialize NSApplication for UI
        self._app = NSApplication.sharedApplication()
        self._app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        self._app.finishLaunching()

        self._setup_signal_handlers()

        print("ScreenFix daemon started", file=sys.stderr)
        print(f"Screenshots will be saved to: {config.save_directory}", file=sys.stderr)
        print(f"Tasks will be saved to: {config.tasks_file}", file=sys.stderr)
        print("\nUse Cmd+Ctrl+Shift+4 to capture (INSTANT, no delay!)", file=sys.stderr)
        print("Press Ctrl+C to stop.\n", file=sys.stderr)

        # Start clipboard watcher
        from .clipboard_watcher import ClipboardWatcher
        self._clipboard_watcher = ClipboardWatcher(self._on_clipboard_image)
        self._clipboard_watcher.start()

        update_state(listening=True)

        # Run the main loop
        while self._running:
            self._process_main_thread_queue()

            while True:
                event = self._app.nextEventMatchingMask_untilDate_inMode_dequeue_(
                    NSEventMaskAny,
                    NSDate.dateWithTimeIntervalSinceNow_(0.05),
                    NSDefaultRunLoopMode,
                    True
                )
                if event is None:
                    break
                self._app.sendEvent_(event)

    def stop(self):
        """Stop the daemon."""
        self._running = False

        if self._clipboard_watcher:
            self._clipboard_watcher.stop()
            self._clipboard_watcher = None

        clear_state()

        if self._app:
            self._app.terminate_(None)


def is_daemon_running() -> bool:
    """Check if the daemon is already running."""
    if not STATE_FILE.exists():
        return False

    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)

        pid = state.get("pid")
        if pid:
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                clear_state()
                return False
    except (json.JSONDecodeError, IOError):
        return False

    return False


def main():
    """Main entry point."""
    if is_daemon_running():
        print("ScreenFix daemon is already running!", file=sys.stderr)
        sys.exit(1)

    daemon = ScreenFixDaemon()

    try:
        daemon.start()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        daemon.stop()


if __name__ == "__main__":
    main()
