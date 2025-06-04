from fabric.utils.helpers import exec_shell_command_async
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.widgets.wayland import WaylandWindow
from gi.repository import GLib

import modules.icons as icons

class PowerMenuDropdown(WaylandWindow):
    def __init__(self, parent_button, **kwargs):
        super().__init__(
            layer="overlay",
            anchor="top right",
            exclusivity="none",
            visible=False,
            **kwargs,
        )

        self.parent_button = parent_button
        self.parent_box = parent_button.get_parent()

        # Create box for power options
        self.power_options = Box(
            name="power-options-container",
            orientation="v",
            spacing=8,
            margin=8,
        )

        # Create power option buttons
        self.btn_lock = Button(
            name="power-option-button",
            child=Box(
                orientation="h",
                spacing=8,
                h_align="start",
                children=[
                    Label(name="option-icon", markup=icons.lock),
                    Label(name="option-label", label="Lock"),
                ],
            ),
            on_clicked=self.lock,
            h_align="fill",
        )

        self.btn_logout = Button(
            name="power-option-button",
            child=Box(
                orientation="h",
                spacing=8,
                h_align="start",
                children=[
                    Label(name="option-icon", markup=icons.logout),
                    Label(name="option-label", label="Logout"),
                ],
            ),
            on_clicked=self.logout,
            h_align="fill",
        )

        self.btn_reboot = Button(
            name="power-option-button",
            child=Box(
                orientation="h",
                spacing=8,
                h_align="start",
                children=[
                    Label(name="option-icon", markup=icons.reboot),
                    Label(name="option-label", label="Restart"),
                ],
            ),
            on_clicked=self.reboot,
            h_align="fill",
        )

        self.btn_shutdown = Button(
            name="power-option-button",
            child=Box(
                orientation="h",
                spacing=8,
                h_align="start",
                children=[
                    Label(name="option-icon", markup=icons.shutdown),
                    Label(name="option-label", label="Power Off"),
                ],
            ),
            on_clicked=self.poweroff,
            h_align="fill",
        )

        # Add buttons to the options box
        self.buttons = [
            self.btn_lock,
            self.btn_logout,
            self.btn_reboot,
            self.btn_shutdown,
        ]

        for button in self.buttons:
            self.power_options.add(button)

        # Add the container to our window
        container = Box(
            name="power-menu-dropdown",
            orientation="v",
            children=[self.power_options],
        )
        self.add(container)

        # Position window next to the button
        GLib.timeout_add(100, self.position_window)

    def position_window(self):
        if not self.is_visible() or not self.parent_button:
            return False

        # Position right below the button and align with right edge
        # This is a simplified approach and might need adjustment
        button_alloc = self.parent_button.get_allocation()
        parent_alloc = self.parent_box.get_allocation()

        # Move the window to position it right below the button
        x = (
            parent_alloc.x
            + button_alloc.x
            + button_alloc.width
            - self.get_allocated_width()
        )
        y = parent_alloc.y + button_alloc.y + button_alloc.height + 8

        self.move(x, y)
        return False  # Stop the timeout

    def toggle_visibility(self):
        if self.is_visible():
            self.hide()
        else:
            self.show_all()
            self.position_window()
            # Make sure our window has focus so we can detect focus out events
            self.present()

    def lock(self, *args):
        print("Locking screen...")
        exec_shell_command_async("hyprlock")
        self.hide()

    def logout(self, *args):
        print("Logging out...")
        exec_shell_command_async("hyprctl dispatch exit")
        self.hide()

    def reboot(self, *args):
        print("Rebooting system...")
        exec_shell_command_async("systemctl reboot")
        self.hide()

    def poweroff(self, *args):
        print("Powering off...")
        exec_shell_command_async("systemctl poweroff")
        self.hide()


class PowerMenu(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="power-menu-container",
            orientation="h",
            spacing=4,
            v_align="center",
            h_align="center",
            visible=True,
            **kwargs,
        )

        # Main power button
        self.power_button = Button(
            name="power-menu-main-button",
            child=Label(name="button-label", markup=icons.power_balanced),
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )

        # Add the button to our container
        self.add(self.power_button)

        # Create dropdown window
        self.dropdown = PowerMenuDropdown(self.power_button)

        # Connect button to toggle dropdown
        self.power_button.connect("clicked", self.toggle_dropdown)

    def toggle_dropdown(self, button):
        self.dropdown.toggle_visibility()
