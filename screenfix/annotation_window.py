"""Annotation window for adding instructions to screenshots."""

import os
import shutil
from datetime import datetime
from pathlib import Path

from AppKit import (
    NSWindow,
    NSWindowStyleMaskTitled,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskNonactivatingPanel,
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
    NSPanel,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
)
from Quartz import kCGMaximumWindowLevelKey, CGWindowLevelForKey
from Foundation import NSMakeRect, NSObject
import objc

from .config import config
from .task_tracker import add_task


_current_controller = None


def save_screenshot(temp_path: str) -> str:
    """Save screenshot from temp location to final location."""
    save_dir = Path(config.save_directory)
    save_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{timestamp}.png"
    final_path = save_dir / filename

    shutil.move(temp_path, final_path)
    return str(final_path)


def cleanup_temp_file(temp_path: str):
    """Remove temporary file."""
    try:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    except OSError:
        pass


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
        image = NSImage.alloc().initWithContentsOfFile_(self.image_path)
        if not image:
            return

        img_size = image.size()

        max_display_width = 400
        max_display_height = 300

        width_scale = min(1.0, max_display_width / img_size.width) if img_size.width > 0 else 1.0
        height_scale = min(1.0, max_display_height / img_size.height) if img_size.height > 0 else 1.0
        scale = min(width_scale, height_scale)

        display_width = int(img_size.width * scale)
        display_height = int(img_size.height * scale)

        padding = 20
        window_width = max(display_width + padding * 2, 450)
        text_area_height = 80
        button_area_height = 50
        label_height = 25
        window_height = display_height + text_area_height + button_area_height + label_height + padding * 3

        style = NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskNonactivatingPanel
        self.window = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(200, 200, window_width, window_height),
            style,
            NSBackingStoreBuffered,
            False,
        )
        self.window.setTitle_("ScreenFix - Add Instructions")

        self.window.setFloatingPanel_(True)
        self.window.setHidesOnDeactivate_(False)

        max_level = CGWindowLevelForKey(kCGMaximumWindowLevelKey)
        self.window.setLevel_(max_level - 1)

        self.window.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces |
            NSWindowCollectionBehaviorFullScreenAuxiliary
        )

        self.delegate = AnnotationWindowDelegate.alloc().initWithController_(self)
        self.window.setDelegate_(self.delegate)

        content = self.window.contentView()
        y_pos = padding

        # Cancel button
        cancel_btn = NSButton.alloc().initWithFrame_(NSMakeRect(padding, y_pos, 100, 32))
        cancel_btn.setTitle_("Cancel")
        cancel_btn.setBezelStyle_(NSBezelStyleRounded)
        cancel_btn.setTarget_(self)
        cancel_btn.setAction_(objc.selector(self.cancel_, signature=b"v@:@"))
        content.addSubview_(cancel_btn)

        # Save button
        save_btn = NSButton.alloc().initWithFrame_(NSMakeRect(window_width - padding - 100, y_pos, 100, 32))
        save_btn.setTitle_("Save")
        save_btn.setBezelStyle_(NSBezelStyleRounded)
        save_btn.setTarget_(self)
        save_btn.setAction_(objc.selector(self.save_, signature=b"v@:@"))
        save_btn.setKeyEquivalent_("\r")
        content.addSubview_(save_btn)

        y_pos += button_area_height

        # Text view
        scroll_frame = NSMakeRect(padding, y_pos, window_width - padding * 2, text_area_height)
        scroll_view = NSScrollView.alloc().initWithFrame_(scroll_frame)
        scroll_view.setHasVerticalScroller_(True)
        scroll_view.setBorderType_(1)

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
        image_view = NSImageView.alloc().initWithFrame_(NSMakeRect(padding, y_pos, display_width, display_height))
        image_view.setImage_(image)
        image_view.setImageScaling_(NSImageScaleProportionallyDown)
        content.addSubview_(image_view)

    def show(self):
        """Display the window on top of fullscreen apps."""
        self.window.center()
        self.window.orderFrontRegardless()
        self.window.makeKeyWindow()
        self.window.makeFirstResponder_(self.text_view)

    def cancel_(self, sender):
        """Handle cancel button click."""
        cleanup_temp_file(self.image_path)
        self.window.close()

    def save_(self, sender):
        """Handle save button click."""
        instructions = self.text_view.string()
        saved_path = save_screenshot(self.image_path)

        if instructions and instructions.strip():
            add_task(instructions.strip(), saved_path)

        self.window.close()


def show_annotation_window(image_path: str) -> None:
    """Display the annotation window for a screenshot."""
    global _current_controller

    if _current_controller and _current_controller.window:
        _current_controller.window.close()

    _current_controller = AnnotationWindowController.alloc().initWithImagePath_(image_path)
    if _current_controller:
        _current_controller.show()
