"""
Clipboard watcher for detecting new screenshots.

Watches the system clipboard for new image data and triggers
a callback when detected. Use Cmd+Ctrl+Shift+4 to copy screenshot
to clipboard (instant, no preview delay).
"""

import os
import time
import threading
from pathlib import Path
from typing import Callable, Optional

from AppKit import NSPasteboard, NSPasteboardTypePNG, NSPasteboardTypeTIFF
from Foundation import NSData


# Temp directory for clipboard images
CLIPBOARD_TEMP_DIR = Path("/tmp/screenfix/clipboard")


class ClipboardWatcher:
    """Watches clipboard for new images."""

    def __init__(self, callback: Callable[[str], None], poll_interval: float = 0.3):
        """
        Initialize the clipboard watcher.

        Args:
            callback: Function to call when new image detected.
                     Called with path to saved image file.
            poll_interval: How often to check clipboard (seconds).
        """
        self._callback = callback
        self._poll_interval = poll_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_change_count = 0

    def start(self):
        """Start watching the clipboard."""
        if self._running:
            return

        # Ensure temp directory exists
        CLIPBOARD_TEMP_DIR.mkdir(parents=True, exist_ok=True)

        # Get initial change count
        pasteboard = NSPasteboard.generalPasteboard()
        self._last_change_count = pasteboard.changeCount()

        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop watching the clipboard."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    @property
    def is_running(self) -> bool:
        """Check if watcher is running."""
        return self._running

    def _watch_loop(self):
        """Main watch loop running in background thread."""
        while self._running:
            try:
                self._check_clipboard()
            except Exception as e:
                import sys
                print(f"Clipboard watch error: {e}", file=sys.stderr)

            time.sleep(self._poll_interval)

    def _check_clipboard(self):
        """Check if clipboard has new image data."""
        pasteboard = NSPasteboard.generalPasteboard()
        current_count = pasteboard.changeCount()

        # No change
        if current_count == self._last_change_count:
            return

        self._last_change_count = current_count

        # Check for image data (PNG preferred, fallback to TIFF)
        image_data = None
        extension = ".png"

        # Try PNG first
        png_data = pasteboard.dataForType_(NSPasteboardTypePNG)
        if png_data:
            image_data = png_data
            extension = ".png"
        else:
            # Try TIFF (screenshots are often TIFF on clipboard)
            tiff_data = pasteboard.dataForType_(NSPasteboardTypeTIFF)
            if tiff_data:
                image_data = tiff_data
                extension = ".tiff"

        if not image_data:
            return  # No image on clipboard

        # Save to temp file
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"clipboard_{timestamp}{extension}"
        temp_path = CLIPBOARD_TEMP_DIR / filename

        # Write the image data
        image_data.writeToFile_atomically_(str(temp_path), True)

        # Clear clipboard to prevent re-triggers
        pasteboard.clearContents()

        # Convert TIFF to PNG if needed (for consistency)
        if extension == ".tiff":
            png_path = temp_path.with_suffix(".png")
            if self._convert_to_png(temp_path, png_path):
                os.remove(temp_path)
                temp_path = png_path

        # Trigger callback
        self._callback(str(temp_path))

    def _convert_to_png(self, tiff_path: Path, png_path: Path) -> bool:
        """Convert TIFF to PNG using CoreGraphics."""
        try:
            from Quartz import (
                CGImageSourceCreateWithURL,
                CGImageSourceCreateImageAtIndex,
                CGImageDestinationCreateWithURL,
                CGImageDestinationAddImage,
                CGImageDestinationFinalize,
                kCGImagePropertyOrientation,
            )
            from Foundation import NSURL

            # Read TIFF
            source_url = NSURL.fileURLWithPath_(str(tiff_path))
            source = CGImageSourceCreateWithURL(source_url, None)
            if not source:
                return False

            image = CGImageSourceCreateImageAtIndex(source, 0, None)
            if not image:
                return False

            # Write PNG
            dest_url = NSURL.fileURLWithPath_(str(png_path))
            destination = CGImageDestinationCreateWithURL(dest_url, "public.png", 1, None)
            if not destination:
                return False

            CGImageDestinationAddImage(destination, image, None)
            return CGImageDestinationFinalize(destination)

        except Exception:
            return False
