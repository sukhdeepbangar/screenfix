"""Global hotkey listener using pynput."""

import threading
from typing import Callable, Optional
from pynput import keyboard
from pynput.keyboard import Key, KeyCode


class HotkeyListener:
    """
    Global hotkey listener for Ctrl+Option+S.

    Uses pynput to listen for the hotkey combination and trigger a callback.
    """

    def __init__(self, callback: Callable[[], None]):
        """
        Initialize the hotkey listener.

        Args:
            callback: Function to call when hotkey is pressed
        """
        self.callback = callback
        self.listener: Optional[keyboard.Listener] = None
        self._running = False

        # Track currently pressed modifier keys
        self._ctrl_pressed = False
        self._alt_pressed = False

    def _on_press(self, key):
        """Handle key press events."""
        # Track modifier keys
        if key == Key.ctrl or key == Key.ctrl_l or key == Key.ctrl_r:
            self._ctrl_pressed = True
        elif key == Key.alt or key == Key.alt_l or key == Key.alt_r:
            self._alt_pressed = True

        # Check for our hotkey: Ctrl + Option/Alt + S
        if self._ctrl_pressed and self._alt_pressed:
            if isinstance(key, KeyCode) and key.char and key.char.lower() == "s":
                # Trigger callback in a separate thread to not block the listener
                threading.Thread(target=self.callback, daemon=True).start()

    def _on_release(self, key):
        """Handle key release events."""
        if key == Key.ctrl or key == Key.ctrl_l or key == Key.ctrl_r:
            self._ctrl_pressed = False
        elif key == Key.alt or key == Key.alt_l or key == Key.alt_r:
            self._alt_pressed = False

    def start(self):
        """Start listening for the hotkey."""
        if self._running:
            return

        self._running = True
        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self.listener.start()

    def stop(self):
        """Stop listening for the hotkey."""
        self._running = False
        if self.listener:
            self.listener.stop()
            self.listener = None

    @property
    def is_running(self) -> bool:
        """Check if the listener is currently running."""
        return self._running and self.listener is not None and self.listener.is_alive()
