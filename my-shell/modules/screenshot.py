import os
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.utils import exec_shell_command_async
import modules.icons as icons


class ScreenshotButton(Button):

    def __init__(self):
        super().__init__(
            name="screenshot-button",
            orientation="h",
            spacing=4,
            v_align="center",
            h_align="center",
            visible=True,
            child=Label(markup=icons.screenshot),
            on_clicked=lambda *_: self._on_click(),
        )

    def _on_click(self):
        path = os.path.expanduser("~/Pictures/screenshots")
        exec_shell_command_async(f"hyprshot -m region -o {path}", lambda *_: None)
