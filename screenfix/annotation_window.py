"""
Annotation window for adding instructions to screenshots.
Uses PyObjC to create a native macOS window.
"""

import threading
from typing import Optional, Callable

from AppKit import (
    NSWindow,
    NSWindowStyleMaskTitled,
    NSWindowStyleMaskClosable,
    NSBackingStoreBuffered,
    NSImageView,
    NSImage,
    NSScrollView,
    NSTextView,
    NSButton,
    NSBezelStyleRounded,
    NSTextField,
    NSFont,
    NSApplication,
    NSImageScaleProportionallyDown,
    NSApp,
    NSStatusWindowLevel,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
)
from Foundation import NSMakeRect, NSObject, NSSize
import objc

from .capture import save_screenshot, cleanup_temp_file
from .task_tracker import add_task


# Store reference to prevent garbage collection
_current_controller = None


class AnnotationWindowDelegate(NSObject):
    """Delegate to handle window events."""

    def initWithController_(self, controller):
        self = objc.super(AnnotationWindowDelegate, self).init()
        if self is None:
            return None
        self.controller = controller
        return self

    def windowWillClose_(self, notification):
        """Called when window is about to close."""
        global _current_controller
        _current_controller = None


class AnnotationWindowController(NSObject):
    """Controller for the annotation window."""

    def initWithImagePath_(self, image_path):
        self = objc.super(AnnotationWindowController, self).init()
        if self is None:
            return None

        self.image_path = image_path
        self.window = None
        self.text_view = None
        self.delegate = None

        self._create_window()
        return self

    def _create_window(self):
        """Create the annotation window."""
        # Load image
        image = NSImage.alloc().initWithContentsOfFile_(self.image_path)
        if not image:
            return

        img_size = image.size()

        # Fixed display size for consistent window - scale to fit within max bounds
        max_display_width = 400
        max_display_height = 300

        # Calculate scale to fit within bounds (scale down only, never up)
        width_scale = min(1.0, max_display_width / img_size.width) if img_size.width > 0 else 1.0
        height_scale = min(1.0, max_display_height / img_size.height) if img_size.height > 0 else 1.0
        scale = min(width_scale, height_scale)

        display_width = int(img_size.width * scale)
        display_height = int(img_size.height * scale)

        # Window size: padding + image + label + text area + buttons
        padding = 20
        window_width = max(display_width + padding * 2, 450)
        text_area_height = 80
        button_area_height = 50
        label_height = 25
        window_height = display_height + text_area_height + button_area_height + label_height + padding * 3

        # Create window
        style = NSWindowStyleMaskTitled | NSWindowStyleMaskClosable
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(200, 200, window_width, window_height),
            style,
            NSBackingStoreBuffered,
            False,
        )
        self.window.setTitle_("ScreenFix - Add Instructions")

        # Appear on top of fullscreen apps and on all spaces
        self.window.setLevel_(NSStatusWindowLevel)
        self.window.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces |
            NSWindowCollectionBehaviorFullScreenAuxiliary
        )

        # Set up delegate
        self.delegate = AnnotationWindowDelegate.alloc().initWithController_(self)
        self.window.setDelegate_(self.delegate)

        content = self.window.contentView()

        # Calculate positions (from bottom up)
        y_pos = padding

        # Cancel button (bottom left)
        cancel_btn = NSButton.alloc().initWithFrame_(
            NSMakeRect(padding, y_pos, 100, 32)
        )
        cancel_btn.setTitle_("Cancel")
        cancel_btn.setBezelStyle_(NSBezelStyleRounded)
        cancel_btn.setTarget_(self)
        cancel_btn.setAction_(objc.selector(self.cancel_, signature=b"v@:@"))
        content.addSubview_(cancel_btn)

        # Save button (bottom right)
        save_btn = NSButton.alloc().initWithFrame_(
            NSMakeRect(window_width - padding - 100, y_pos, 100, 32)
        )
        save_btn.setTitle_("Save")
        save_btn.setBezelStyle_(NSBezelStyleRounded)
        save_btn.setTarget_(self)
        save_btn.setAction_(objc.selector(self.save_, signature=b"v@:@"))
        save_btn.setKeyEquivalent_("\r")  # Enter key
        content.addSubview_(save_btn)

        y_pos += button_area_height

        # Text view in scroll view
        scroll_frame = NSMakeRect(padding, y_pos, window_width - padding * 2, text_area_height)
        scroll_view = NSScrollView.alloc().initWithFrame_(scroll_frame)
        scroll_view.setHasVerticalScroller_(True)
        scroll_view.setBorderType_(1)  # Bezel border

        text_frame = NSMakeRect(0, 0, scroll_frame.size.width - 4, scroll_frame.size.height)
        self.text_view = NSTextView.alloc().initWithFrame_(text_frame)
        self.text_view.setFont_(NSFont.systemFontOfSize_(13))
        scroll_view.setDocumentView_(self.text_view)
        content.addSubview_(scroll_view)

        y_pos += text_area_height + 5

        # Label
        label = NSTextField.labelWithString_("Instructions for Claude Code:")
        label.setFrame_(NSMakeRect(padding, y_pos, 300, label_height))
        content.addSubview_(label)

        y_pos += label_height + 5

        # Image view
        image_view = NSImageView.alloc().initWithFrame_(
            NSMakeRect(padding, y_pos, display_width, display_height)
        )
        image_view.setImage_(image)
        image_view.setImageScaling_(NSImageScaleProportionallyDown)
        content.addSubview_(image_view)

    def show(self):
        """Display the window."""
        self.window.center()
        self.window.makeKeyAndOrderFront_(None)
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        # Focus the text view
        self.window.makeFirstResponder_(self.text_view)

    def cancel_(self, sender):
        """Handle cancel button click."""
        cleanup_temp_file(self.image_path)
        self.window.close()

    def save_(self, sender):
        """Handle save button click."""
        # Get instruction text
        instructions = self.text_view.string()

        # Save screenshot to final location
        saved_path = save_screenshot(self.image_path)

        # Add task to tasks.md if instructions provided
        if instructions and instructions.strip():
            add_task(instructions.strip(), saved_path)

        self.window.close()


def show_annotation_window(image_path: str) -> None:
    """
    Display the annotation window for a captured screenshot.

    This function must be called from the main thread.

    Args:
        image_path: Path to the captured screenshot
    """
    global _current_controller

    # Close any existing window
    if _current_controller and _current_controller.window:
        _current_controller.window.close()

    _current_controller = AnnotationWindowController.alloc().initWithImagePath_(image_path)
    if _current_controller:
        _current_controller.show()


def show_annotation_window_async(image_path: str) -> None:
    """
    Display the annotation window from a background thread.

    Schedules the window to be shown on the main thread.

    Args:
        image_path: Path to the captured screenshot
    """
    from AppKit import NSRunLoop, NSDefaultRunLoopMode

    # Schedule on main thread
    def show():
        show_annotation_window(image_path)

    # Use performSelectorOnMainThread
    NSObject.alloc().init().performSelectorOnMainThread_withObject_waitUntilDone_(
        objc.selector(lambda self: show(), signature=b"v@:"),
        None,
        False,
    )
