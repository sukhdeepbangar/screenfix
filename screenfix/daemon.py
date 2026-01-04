#!/usr/bin/env python3
"""
ScreenFix Daemon - Standalone hotkey listener and screen capture.

This runs separately from the MCP server and handles:
- Global hotkey listening (Ctrl+Option+S)
- Screen capture
- Annotation window UI
- Saving screenshots and tasks

Run with: python -m screenfix.daemon
Or: screenfix-daemon
"""

import json
import os
import queue
import signal
import sys
from datetime import datetime
from pathlib import Path

# Import AppKit first to ensure proper initialization
from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSApplicationActivationPolicyRegular,
    NSEventMaskAny,
)
from Foundation import NSRunLoop, NSDefaultRunLoopMode, NSDate

from .config import config
from .capture import capture_screen_region, save_screenshot, cleanup_temp_file
from .task_tracker import add_task
from .hotkey import HotkeyListener


# State file for communication with MCP server
STATE_FILE = Path.home() / ".config" / "screenfix" / "state.json"


def update_state(listening: bool = None, last_capture: str = None):
    """Update the state file for MCP server to read."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    state = {"pid": os.getpid(), "listening": False}

    # Read existing state
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
    """Standalone daemon for hotkey listening and screen capture."""

    def __init__(self):
        self._running = False
        self._hotkey_listener = None
        self._app = None
        self._main_thread_queue = queue.Queue()

    def _on_hotkey(self):
        """Called when the hotkey is pressed (from background thread)."""
        print("Hotkey detected! Capturing screen...", file=sys.stderr)

        # Capture screen region
        temp_path = capture_screen_region()

        if temp_path:
            print(f"Captured to: {temp_path}", file=sys.stderr)
            # Queue the annotation window to be shown on main thread
            self._main_thread_queue.put(temp_path)
        else:
            print("Capture cancelled", file=sys.stderr)

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

        # Switch to Regular policy to allow user interaction with the window
        self._app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
        self._app.activateIgnoringOtherApps_(True)
        show_annotation_window(image_path)

    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def handle_signal(signum, frame):
            print(f"\nReceived signal {signum}, shutting down...", file=sys.stderr)
            self.stop()

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

    def start(self):
        """Start the daemon."""
        if self._running:
            return

        self._running = True

        # Ensure directories exist
        config.ensure_directories()

        # Initialize NSApplication for UI
        self._app = NSApplication.sharedApplication()
        self._app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        self._app.finishLaunching()

        # Set up signal handlers
        self._setup_signal_handlers()

        # Start hotkey listener
        print("Starting hotkey listener (Ctrl+Option+S)...", file=sys.stderr)
        print(f"Screenshots will be saved to: {config.save_directory}", file=sys.stderr)
        print(f"Tasks will be saved to: {config.tasks_file}", file=sys.stderr)
        print("\nIMPORTANT: Make sure Terminal has Accessibility permission in:", file=sys.stderr)
        print("System Settings > Privacy & Security > Accessibility", file=sys.stderr)
        print("\nPress Ctrl+C to stop.\n", file=sys.stderr)

        self._hotkey_listener = HotkeyListener(self._on_hotkey)
        self._hotkey_listener.start()

        # Update state
        update_state(listening=True)

        # Run the main loop for UI events
        while self._running:
            # Process any pending annotation windows from background threads
            self._process_main_thread_queue()

            # Process all pending UI events
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

        if self._hotkey_listener:
            self._hotkey_listener.stop()
            self._hotkey_listener = None

        clear_state()

        # Terminate the app
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
            # Check if process is running
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                # Process not running, clean up stale state
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
