import gi

gi.require_version("Gtk", "3.0")
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
import modules.icons as icons
from services.network import NetworkClient

class Wired(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="network-connections",
            h_expand=True,
            v_expand=True,
            spacing=4,
            orientation="h",
            **kwargs,
        )
        self.network_client = NetworkClient()
        self.left_button_childs = Box(
            name="wired-left-button-childs",
            orientation="h",
            spacing=8,
        )
        self.left_button = Button(
            name="wired-left-button",
            h_expand=True,
            child=self.left_button_childs,
        )
        self.wired_status_text = Label(
            name="wired-status", label="Ethernet", all_visible=True, visible=True
        )
        self.wired_icon = Label(name="wired-icon", markup=icons.ethernet_off)

        self.left_button_childs.add(self.wired_icon)
        self.left_button_childs.add(self.wired_status_text)
        self.add(self.left_button)
        # TODO : make it work
