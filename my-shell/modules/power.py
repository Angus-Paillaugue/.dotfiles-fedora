from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.utils import exec_shell_command_async
import modules.icons as icons
from fabric.widgets.revealer import Revealer
from fabric.widgets.revealer import Revealer

class PowerMenuActions(Revealer):
    def __init__(self, **kwargs):
        super().__init__(
            name="power-options-revealer",
            transition_type="slide-down",
            child_revealed=False,
            transition_duration=250,
            **kwargs,
        )

        self.revealed = False
        self.main_box = Box(
            name="power-options-container",
            orientation="v",
            spacing=8,
            h_align="fill",
            v_align="fill",
        )

        self.actions = [
            {"label": "Logout", "icon": icons.logout, "command": "logout"},
            {"label": "Reboot", "icon": icons.reboot, "command": "systemctl reboot"},
            {
                "label": "Shutdown",
                "icon": icons.shutdown,
                "command": "systemctl poweroff",
            },
        ]

        for action in self.actions:
            button = Button(
                name="power-option-button",
                child=Box(
                    orientation="h",
                    spacing=8,
                    children=[
                        Label(name="option-icon", markup=action["icon"]),
                        Label(name="option-label", label=action["label"]),
                    ],
                ),
                on_clicked=lambda b, cmd=action["command"]: exec_shell_command_async(
                    cmd
                ),
            )
            self.main_box.add(button)

        self.add(self.main_box)

    def toggle_visibility(self):
        """Toggle the visibility of the power menu actions."""
        if self.revealed:
            self.unreveal()
        else:
            self.reveal()

        self.revealed = not self.revealed


class PowerMenuButton(Box):
    def __init__(self, power_actions=None, **kwargs):
        super().__init__(
            name="power-menu-container",
            orientation="h",
            spacing=4,
            v_align="center",
            h_align="center",
            visible=True,
            **kwargs,
        )

        # Reference to the PowerMenuActions instance
        self.power_actions = power_actions

        # Main power button
        self.power_button = Button(
            name="power-menu-main-button",
            child=Label(name="button-label", markup=icons.shutdown),
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )

        # Add the button to our container
        self.add(self.power_button)

        # Connect button to toggle dropdown
        self.power_button.connect("clicked", self.toggle_power_menu)

    def toggle_power_menu(self, button):
        if self.power_actions:
            self.power_actions.toggle_visibility()
