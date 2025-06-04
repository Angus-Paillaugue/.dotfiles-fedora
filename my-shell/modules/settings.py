import os
from fabric import Property, Service, Signal
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from fabric.bluetooth.service import BluetoothClient, BluetoothDevice
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.wayland import WaylandWindow
from fabric.widgets.scale import Scale
from services.network import NetworkClient
from fabric.utils import exec_shell_command_async, exec_shell_command, monitor_file
from fabric.audio.service import Audio
from gi.repository import GLib, Gtk
import modules.icons as icons
from fabric.widgets.circularprogressbar import CircularProgressBar
from fabric.widgets.revealer import Revealer
from fabric.core.fabricator import Fabricator
from services.metrics import shared_provider
from fabric.widgets.revealer import Revealer
from fabric.widgets.image import Image
from fabric.widgets.scrolledwindow import ScrolledWindow


class WifiModule(Button):
    def __init__(self, **kwargs):
        super().__init__(
            name="wifi-module",
            orientation="v",
            margin=8,
            h_align="fill",
            **kwargs,
        )

        self.network_client = NetworkClient()

        # Placeholder for WiFi module content
        self.wifi_icon = Label(name="wifi-icon", markup=icons.wifi_3)
        self.wifi_ssid = Label(name="wifi-ssid", label="Not Connected")
        self.add(
            Box(
                name="wifi-button-content",
                orientation="h",
                spacing=12,
                children=[self.wifi_icon, self.wifi_ssid],
            )
        )

        self.on_clicked=lambda *_: (
            self.network_client.wifi_device.toggle_wifi()
            if self.network_client.wifi_device
            else None
        ),


class NetworkModule(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="network-module",
            orientation="v",
            spacing=8,
            margin=8,
            **kwargs,
        )

        # Placeholder for Network module content
        self.network_label = Label(name="network-label", markup=icons.ethernet)
        self.add(self.network_label)


# Discover screen backlight device
try:
    screen_device = os.listdir("/sys/class/backlight")
    screen_device = screen_device[0] if screen_device else ""
except FileNotFoundError:
    screen_device = ""


class Brightness(Service):
    """Service to manage screen brightness levels."""

    instance = None

    @staticmethod
    def get_initial():
        if Brightness.instance is None:
            Brightness.instance = Brightness()

        return Brightness.instance

    @Signal
    def screen(self, value: int) -> None:
        """Signal emitted when screen brightness changes."""
        # Implement as needed for your application

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Path for screen backlight control
        self.screen_backlight_path = f"/sys/class/backlight/{screen_device}"

        # Initialize maximum brightness level
        self.max_screen = self.do_read_max_brightness(self.screen_backlight_path)

        if screen_device == "":
            return

        # Monitor screen brightness file
        self.screen_monitor = monitor_file(f"{self.screen_backlight_path}/brightness")

        self.screen_monitor.connect(
            "changed",
            lambda _, file, *args: self.emit(
                "screen",
                round(int(file.load_bytes()[0].get_data())),
            ),
        )

    def do_read_max_brightness(self, path: str) -> int:
        # Reads the maximum brightness value from the specified path.
        max_brightness_path = os.path.join(path, "max_brightness")
        if os.path.exists(max_brightness_path):
            with open(max_brightness_path) as f:
                return int(f.readline())
        return -1  # Return -1 if file doesn't exist, indicating an error.

    @Property(int, "read-write")
    def screen_brightness(self) -> int:
        # Property to get or set the screen brightness.
        brightness_path = os.path.join(self.screen_backlight_path, "brightness")
        if os.path.exists(brightness_path):
            with open(brightness_path) as f:
                return int(f.readline())
        return -1  # Return -1 if file doesn't exist, indicating error.

    @screen_brightness.setter
    def screen_brightness(self, value: int):
        # Setter for screen brightness property.
        if not (0 <= value <= self.max_screen):
            value = max(0, min(value, self.max_screen))

        try:
            exec_shell_command_async(
                f"brightnessctl --device '{screen_device}' set {value}", lambda _: None
            )
            self.emit("screen", int((value / self.max_screen) * 100))
        except GLib.Error as e:
            print(f"Error setting screen brightness: {e.message}")
        except Exception as e:
            print(f"Unexpected error setting screen brightness: {e}")


class BrightnessSlider(Scale):
    def __init__(self, client, **kwargs):
        super().__init__(
            name="control-slider",
            orientation="h",
            h_expand=True,
            has_origin=True,
            increments=(5, 10),
            **kwargs,
        )

        self.client = client

        self.set_range(0, self.client.max_screen)
        self.set_value(self.client.screen_brightness)
        self.add_style_class("brightness")

        self._pending_value = None
        self._update_source_id = None

        self.connect("change-value", self.on_scale_move)
        self.client.connect("screen", self.on_brightness_changed)

    def on_brightness_changed(self, client, _):
        self.set_value(self.client.screen_brightness)

    def on_scale_move(self, widget, scroll, moved_pos):
        self._pending_value = moved_pos
        if self._update_source_id is None:
            self._update_source_id = GLib.idle_add(self._update_brightness_callback)
        return False

    def _update_brightness_callback(self):
        if self._pending_value is not None:
            value_to_set = self._pending_value
            self._pending_value = None
            if value_to_set != self.client.screen_brightness:
                self.client.screen_brightness = value_to_set
            return True
        else:
            self._update_source_id = None
            return False


class BrightnessRow(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="brightness-row",
            orientation="h",
            spacing=12,
            **kwargs,
        )

        self.client = Brightness.get_initial()
        if self.client.screen_brightness == -1:
            self.destroy()
            return

        self._pending_value = None
        self._update_source_id = None

        self.client.connect("screen", self.set_icon)

        self.brightness_icons = [icons.brightness_low, icons.brightness_high]

        self.brightness_icon = Label(
            name="brightness-icon", markup=self.brightness_icons[0]
        )
        self.add(self.brightness_icon)

        self.brightness_slider = BrightnessSlider(client=self.client)
        self.add(self.brightness_slider)

        self.set_icon()

    def set_icon(self, *args):
        current = int((self.client.screen_brightness / self.client.max_screen) * 100)
        num_icons = len(self.brightness_icons)
        range_per_icon = 100 // num_icons

        icon_index = min(current // range_per_icon, num_icons - 1)
        icon = self.brightness_icons[icon_index]

        self.brightness_icon.set_markup(icon)

    def destroy(self):
        if self._update_source_id is not None:
            GLib.source_remove(self._update_source_id)
        super().destroy()


class VolumeSlider(Scale):
    def __init__(self, **kwargs):
        super().__init__(
            name="control-slider",
            orientation="h",
            h_expand=True,
            h_align="fill",
            has_origin=True,
            increments=(0.01, 0.1),
            **kwargs,
        )
        self.audio = Audio()
        self.audio.connect("notify::speaker", self.on_new_speaker)
        if self.audio.speaker:
            self.audio.speaker.connect("changed", self.on_speaker_changed)
        self.connect("value-changed", self.on_value_changed)
        self.add_style_class("vol")
        self.on_speaker_changed()

    def on_new_speaker(self, *args):
        if self.audio.speaker:
            self.audio.speaker.connect("changed", self.on_speaker_changed)
            self.on_speaker_changed()

    def on_value_changed(self, _):
        if self.audio.speaker:
            self.audio.speaker.volume = self.value * 100

    def on_speaker_changed(self, *_):
        if not self.audio.speaker:
            return
        self.value = self.audio.speaker.volume / 100

        if self.audio.speaker.muted:
            self.add_style_class("muted")
        else:
            self.remove_style_class("muted")


class VolumeRow(Box):
    # TODO: Fix the volume not being responsive with the system
    def __init__(self, **kwargs):
        super().__init__(
            name="volume-row",
            orientation="h",
            spacing=12,
            **kwargs,
        )

        # Placeholder for Volume control
        self.volume_icons = [icons.volume_low, icons.volume_high]
        self.volume_icon = Label(name="volume-icon")
        self.add(self.volume_icon)

        # Placeholder for Volume slider
        self.volume_slider = VolumeSlider()
        self.add(self.volume_slider)
        self.set_icon()

    def set_icon(self):
        percentage = self.get_volume_percentage()
        if percentage == 0:
            icon = icons.volume_muted
        else:
            num_icons = len(self.volume_icons)
            range_per_icon = 100 // num_icons
            icon_index = min(percentage // range_per_icon, num_icons - 1)
            icon = self.volume_icons[icon_index]
        self.volume_icon.set_markup(icon)

    def get_volume_percentage(self):
        # Placeholder for actual volume percentage retrieval logic
        # This should return the current volume level as a percentage
        return 50


class Battery(Button):
    def __init__(self, **kwargs):
        super().__init__(name="battery-container", **kwargs)

        main_box = Box(
            spacing=0,
            orientation="h",
            visible=True,
            all_visible=True,
        )

        self.bat_icon = Label(name="battery-icon", markup=icons.battery_0)
        self.bat_circle = CircularProgressBar(
            name="battery-circle",
            value=0,
            size=30,
            line_width=2,
            start_angle=150,
            end_angle=390,
            style_classes="bat",
            child=self.bat_icon,
        )
        self.bat_level = Label(name="battery-level", style_classes="bat", label="100%")
        self.bat_revealer = Revealer(
            name="battery-level-revealer",
            transition_duration=250,
            transition_type="slide-left",
            child=self.bat_level,
            child_revealed=False,
        )
        self.bat_box = Box(
            name="battery-level-box",
            orientation="h",
            spacing=0,
            children=[self.bat_circle, self.bat_revealer],
        )

        main_box.add(self.bat_box)

        self.add(main_box)

        self.connect("enter-notify-event", self.on_mouse_enter)
        self.connect("leave-notify-event", self.on_mouse_leave)

        self.batt_fabricator = Fabricator(
            poll_from=lambda v: shared_provider.get_battery(),
            on_changed=lambda f, v: self.update_battery,
            interval=1000,
            stream=False,
            default_value=0,
        )
        self.batt_fabricator.changed.connect(self.update_battery)
        GLib.idle_add(self.update_battery, None, shared_provider.get_battery())

        self.hide_timer = None
        self.hover_counter = 0

    def _format_percentage(self, value: int) -> str:
        return f"{value}%"

    def on_mouse_enter(self, widget, event):
        self.hover_counter += 1
        if self.hide_timer is not None:
            GLib.source_remove(self.hide_timer)
            self.hide_timer = None

        self.bat_revealer.set_reveal_child(True)
        return False

    def on_mouse_leave(self, widget, event):
        if self.hover_counter > 0:
            self.hover_counter -= 1
        if self.hover_counter == 0:
            if self.hide_timer is not None:
                GLib.source_remove(self.hide_timer)
            self.hide_timer = GLib.timeout_add(100, self.hide_revealer)
        return False

    def hide_revealer(self):
        self.bat_revealer.set_reveal_child(False)
        self.hide_timer = None
        return False

    def update_battery(self, sender, battery_data):
        value, charging = battery_data
        if value == 0:
            self.set_visible(False)
        else:
            self.set_visible(True)
            self.bat_circle.set_value(value / 100)
        percentage = int(value)
        self.bat_level.set_label(self._format_percentage(percentage))

        if percentage <= 15:
            self.bat_icon.add_style_class("alert")
            self.bat_circle.add_style_class("alert")
        else:
            self.bat_icon.remove_style_class("alert")
            self.bat_circle.remove_style_class("alert")

        if charging == True:
            self.bat_icon.set_markup(icons.battery_charging)
        elif percentage <= 20:
            self.bat_icon.set_markup(icons.battery_0)
        elif percentage <= 40:
            self.bat_icon.set_markup(icons.battery_1)
        elif percentage <= 60:
            self.bat_icon.set_markup(icons.battery_2)
        elif percentage <= 80:
            self.bat_icon.set_markup(icons.battery_3)
        else:
            self.bat_icon.set_markup(icons.battery_4)


class PowerProfile(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="power-profile",
            orientation="h",
            h_align="fill",
            margin=8,
            **kwargs,
        )

        self.profiles = [
            {"name": "balanced", "label": "Balanced", "icon": icons.balanced},
            {
                "name": "throughput-performance",
                "label": "Performance",
                "icon": icons.performance,
            },
            {"name": "powersave", "label": "Eco", "icon": icons.eco},
        ]

        self.active_profile = self.profiles[0]  # Default to the first profile

        # Placeholder for WiFi module content
        self.profile_icon = Label(
            name="power-profile-icon", markup=self.active_profile["icon"]
        )
        self.profile_name = Label(
            name="power-profile-name", label=self.active_profile["label"]
        )

        self.button = Button(
            name="power-profile-button",
            child=Box(
                spacing=12,
                children=[self.profile_icon, self.profile_name],
                orientation="h",
            ),
            on_clicked=lambda b: self.rotate_profile(),
        )
        self.add(self.button)

        self.power_profile_fabricator = Fabricator(
            poll_from=lambda v: self.get_profile(),
            on_changed=lambda f, v: self.update_ui,
            interval=1000,
            stream=False,
            default_value=0,
        )
        self.power_profile_fabricator.changed.connect(self.update_ui)
        GLib.idle_add(self.update_ui, None, self.get_profile())

    def update_ui(self, *args):
        """Update the UI to reflect the current power profile."""
        self.profile_icon.set_markup(self.active_profile["icon"])
        self.profile_name.set_label(self.active_profile["label"])
        self.add_style_class(self.active_profile["name"])

    def get_profile(self):
        res = exec_shell_command("tuned-adm active")
        if res:
            profile_name = res.split(":")[1].strip()
            for profile in self.profiles:
                if profile["name"] == profile_name:
                    self.active_profile = profile
                    return profile_name
        return None  # Return None if no profile matches or command fails

    def rotate_profile(self):
        """Rotate through the available power profiles."""
        current_index = self.profiles.index(self.active_profile)
        next_index = (current_index + 1) % len(self.profiles)
        self.active_profile = self.profiles[next_index]

        # Update the UI to reflect the new profile
        self.update_ui()

        # Apply the new profile using tuned-adm
        exec_shell_command_async(
            f"tuned-adm profile {self.active_profile['name']}",
            lambda _: None,
        )


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


class BluetoothDeviceSlot(CenterBox):
    def __init__(self, device: BluetoothDevice, **kwargs):
        super().__init__(name="bluetooth-device", **kwargs)
        self.device = device
        self.device.connect("changed", self.on_changed)
        self.device.connect(
            "notify::closed", lambda *_: self.device.closed and self.destroy()
        )

        self.connection_label = Label(
            name="bluetooth-connection", markup=icons.bluetooth_off
        )
        self.connect_button = Button(
            name="bluetooth-connect",
            label="Connect",
            on_clicked=lambda *_: self.device.set_connecting(not self.device.connected),
            style_classes=["connected"] if self.device.connected else None,
        )

        self.start_children = [
            Box(
                spacing=8,
                h_expand=True,
                h_align="fill",
                children=[
                    Image(icon_name=device.icon_name + "-symbolic", size=16),
                    Label(
                        label=device.name,
                        h_expand=True,
                        h_align="start",
                        ellipsization="end",
                    ),
                    self.connection_label,
                ],
            )
        ]
        self.end_children = self.connect_button

        self.device.emit("changed")

    def on_changed(self, *_):
        self.connection_label.set_markup(
            icons.bluetooth if self.device.connected else icons.bluetooth_off
        )
        if self.device.connecting:
            self.connect_button.set_label(
                "Connecting..." if not self.device.connecting else "..."
            )
        else:
            self.connect_button.set_label(
                "Connect" if not self.device.connected else "Disconnect"
            )
        if self.device.connected:
            self.connect_button.add_style_class("connected")
        else:
            self.connect_button.remove_style_class("connected")
        return


class BluetoothDevicesDropdown(Revealer):
    def __init__(self, labels, **kwargs):
        super().__init__(
            name="bluetooth-devices-dropdown",
            transition_type="slide-down",
            child_revealed=False,
            h_expand=True,
            transition_duration=250,
            **kwargs,
        )

        self.shown = False
        self.labels = labels
        self.bt_status_text = self.labels["bluetooth_status_text"]
        self.bt_button = self.labels["bluetooth_button"]
        self.bt_icon = self.labels["bluetooth_icon"]

        self.client = BluetoothClient(on_device_added=self.on_device_added)
        self.scan_label = Label(name="bluetooth-scan-label", markup=icons.radar)
        self.scan_button = Button(
            name="bluetooth-scan",
            child=self.scan_label,
            tooltip_text="Scan for Bluetooth devices",
            on_clicked=lambda *_: self.client.toggle_scan(),
        )

        self.client.connect("notify::enabled", lambda *_: self.status_label())
        self.client.connect("notify::scanning", lambda *_: self.update_scan_label())

        self.paired_box = Box(spacing=2, orientation="vertical")
        self.available_box = Box(spacing=2, orientation="vertical")

        content_box = Box(spacing=4, orientation="vertical")
        content_box.add(self.paired_box)
        content_box.add(Label(name="bluetooth-section", label="Available"))
        content_box.add(self.available_box)

        main_container = Box(
            name="bluetooth-devices-container",
            orientation="v",
            h_expand=True,
            spacing=8,
        )

        main_container.add(
            CenterBox(
                name="bluetooth-header",
                start_children=Label(
                    name="bluetooth-devices-title", label="Bluetooth Devices"
                ),
                end_children=self.scan_button,
            )
        )

        main_container.add(
            ScrolledWindow(
                name="bluetooth-devices",
                min_content_size=(-1, 150),  # Set a minimum height
                child=content_box,
                v_expand=True,
                propagate_width=False,
                propagate_height=False,
            )
        )

        self.add(main_container)

        self.client.notify("scanning")
        self.client.notify("enabled")

    def toggle_visibility(self):
        """Toggle the visibility of the Bluetooth devices dropdown."""
        if self.shown:
            self.unreveal()
        else:
            self.reveal()
            self.status_label()
            self.update_scan_label()
        self.shown = not self.shown

    def status_label(self):
        if self.client.enabled:
            self.bt_status_text.set_label("Enabled")
            for i in [
                self.bt_button,
                self.bt_status_text,
                self.bt_icon,
            ]:
                i.remove_style_class("disabled")
            self.bt_icon.set_markup(icons.bluetooth)
        else:
            self.bt_status_text.set_label("Disabled")
            for i in [
                self.bt_button,
                self.bt_status_text,
                self.bt_icon,
            ]:
                i.add_style_class("disabled")
            self.bt_icon.set_markup(icons.bluetooth_off)

    def on_device_added(self, client: BluetoothClient, address: str):
        if not (device := client.get_device(address)):
            return

        # Check if device is already displayed
        for child in self.paired_box.get_children():
            if (
                isinstance(child, BluetoothDeviceSlot)
                and child.device.address == address
            ):
                return

        for child in self.available_box.get_children():
            if (
                isinstance(child, BluetoothDeviceSlot)
                and child.device.address == address
            ):
                return

        slot = BluetoothDeviceSlot(device)

        if device.paired:
            self.paired_box.add(slot)
            self.paired_box.show_all()
        else:
            self.available_box.add(slot)
            self.available_box.show_all()

    def update_scan_label(self):
        if self.client.scanning:
            self.scan_label.add_style_class("scanning")
            self.scan_button.add_style_class("scanning")
            self.scan_button.set_tooltip_text("Stop scanning for Bluetooth devices")
        else:
            self.scan_label.remove_style_class("scanning")
            self.scan_button.remove_style_class("scanning")
            self.scan_button.set_tooltip_text("Scan for Bluetooth devices")


class BluetoothButton(Box):
    def __init__(self, slot = None, **kwargs):
        super().__init__(
            name="bluetooth-button",
            h_expand=True,
            v_expand=True,
            spacing=4,
            orientation="h",
            **kwargs,
        )

        self.left_button_childs = Box(
            name="bluetooth-left-button-childs",
            orientation="h",
            spacing=8,
        )
        self.left_button = Button(
            name="bluetooth-left-button",
            h_expand=True,
            child=self.left_button_childs,
        )

        self.slot = slot
        self.bluetooth_status_text = Label(
            name="bluetooth-status", label="Bluetooth",
            all_visible=True, visible=True
        )
        self.bluetooth_icon = Label(
            name="bluetooth-icon", markup=icons.bluetooth
        )
        self.bluetooth_devices_open_button = Button(
            name="bluetooth-open-button",
            child=Label(name="bluetooth-open-label", markup=icons.chevron_right),
        )
        self.labels = dict()
        self.labels["bluetooth_button"] = self.left_button
        self.labels["bluetooth_status_text"] = self.bluetooth_status_text
        self.labels['bluetooth_icon'] = self.bluetooth_icon
        self.bluetooth_devices_dropdown = BluetoothDevicesDropdown(labels=self.labels)
        self.slot.add(self.bluetooth_devices_dropdown)

        self.left_button_childs.add(self.bluetooth_icon)
        self.left_button_childs.add(self.bluetooth_status_text)
        self.add(self.left_button)
        self.add(self.bluetooth_devices_open_button)
        self.bluetooth_devices_open_button.connect(
            "clicked", lambda *_: self.bluetooth_devices_dropdown.toggle_visibility() if self.bluetooth_devices_dropdown.client.enabled else None
        )
        self.left_button.connect(
            "clicked",
            lambda *_: (
                self.bluetooth_devices_dropdown.client.toggle_power(),
                (
                    self.bluetooth_devices_dropdown.toggle_visibility()
                    if self.bluetooth_devices_dropdown.shown
                    else None
                ),
            ),
        )


class SettingsMenuDropdown(WaylandWindow):
    def __init__(self, parent_button, **kwargs):
        super().__init__(
            layer="overlay",
            anchor="top right",
            exclusivity="none",
            visible=False,
            margin="0 8px 0 0",
            **kwargs,
        )

        self.parent_button = parent_button
        self.parent_box = parent_button.get_parent()

        self.wifi_module = WifiModule()
        self.network_module = NetworkModule()
        self.brightness_module = BrightnessRow()
        self.volume_module = VolumeRow()
        self.battery = Battery()
        self.power_profile = PowerProfile()
        self.power_menu_actions = PowerMenuActions()
        self.bluetooth_devices_dropdown_slot = Box()
        self.bluetooth = BluetoothButton(slot=self.bluetooth_devices_dropdown_slot)
        self.power_menu_button = PowerMenuButton(power_actions=self.power_menu_actions)

        self.buttons_grid = Gtk.Grid(
            column_homogeneous=True,
            row_homogeneous=False,
            name="setting-buttons-grid",
            column_spacing=12,
            row_spacing=12,
        )

        self.buttons_grid.attach(self.wifi_module, 0, 0, 1, 1)
        self.buttons_grid.attach(self.network_module, 1, 0, 1, 1)
        self.buttons_grid.attach(self.bluetooth, 0, 1, 1, 1)
        self.buttons_grid.attach(self.power_profile, 1, 1, 1, 1)

        self.items = [
            CenterBox(
                start_children=[self.battery], end_children=[self.power_menu_button]
            ),
            self.power_menu_actions,
            self.buttons_grid,
            self.bluetooth_devices_dropdown_slot,
            self.volume_module,
            self.brightness_module,
        ]

        # Add the container to our window
        self.settings_container = Box(
            name="settings-container",
            orientation="v",
        )
        self.add(self.settings_container)

        for item in self.items:
            self.settings_container.add(item)

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


class Settings(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="settings-menu-container",
            orientation="h",
            spacing=4,
            v_align="center",
            h_align="center",
            visible=True,
            **kwargs,
        )

        # Main power button
        self.settings_button = Button(
            name="settings-menu-main-button",
            child=Label(name="button-label", markup=icons.settings),
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )

        # Add the button to our container
        self.add(self.settings_button)

        # Create dropdown window
        self.dropdown = SettingsMenuDropdown(self.settings_button)

        # Connect button to toggle dropdown
        self.settings_button.connect("clicked", self.toggle_dropdown)

    def toggle_dropdown(self, button):
        self.dropdown.toggle_visibility()
