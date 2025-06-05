from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.scale import Scale
from fabric.widgets.button import Button
from fabric.widgets.revealer import Revealer
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.audio.service import Audio
import modules.icons as icons
from gi.repository import GLib

class VolumeSlider(Scale):
    def __init__(self, audio, notify=None, **kwargs):
        super().__init__(
            name="control-slider",
            orientation="h",
            h_expand=True,
            h_align="fill",
            has_origin=True,
            increments=(0.01, 0.1),
            **kwargs,
        )
        self.audio = audio
        self.notify = notify
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
            self.notify()

    def on_speaker_changed(self, *_):
        if not self.audio.speaker:
            return
        self.value = self.audio.speaker.volume / 100

        if self.audio.speaker.muted:
            self.add_style_class("muted")
        else:
            self.remove_style_class("muted")


class VolumeIcon(Button):
    def __init__(self, audio: Audio, **kwargs):
        super().__init__(name="volume-icon",  **kwargs)
        self.audio = audio
        self.value = 0
        self.hide_timer = None
        self.hover_counter = 0

        self.label = Label(
            name="volume-icon-label",
            markup=icons.volume_muted,
        )
        self.connect("clicked", self.on_clicked)
        self.add(self.label)

        self.volume_icons = [
            icons.volume_low,
            icons.volume_high,
        ]

        self.set_icon()

    def set_icon(self):
        if not self.audio or not self.audio.speaker:
            return
        percentage = round(
            (self.audio.speaker.volume / self.audio.max_volume) * 100
        )
        if self.audio.speaker.muted:
            icon = icons.volume_muted
        else:
            num_icons = len(self.volume_icons)
            range_per_icon = 100 // num_icons
            icon_index = min(percentage // range_per_icon, num_icons - 1)
            icon = self.volume_icons[icon_index]
        self.label.set_markup(icon)

    def on_clicked(self, _):
        self.audio.speaker.muted = not self.audio.speaker.muted
        self.set_icon()


class VolumeOutputsRevealer(Revealer):
    def __init__(self, **kwargs):
        super().__init__(
            name="outputs-box",
            transition_duration=250,
            transition_type="slide-down",
            child_revealed=False,
            **kwargs,
        )

        self.output_container = Box(spacing=4, orientation="v", name="outputs-container-box")

        self.scrolled_box = ScrolledWindow(
            name="outputs-container",
            child=self.output_container,
            propagate_height=False,
            h_expand=True,
            min_content_size=(-1, 150),
        )
        self.add(self.scrolled_box)

        self.shown = False

    def toggle(self):
        if self.shown:
            self.unreveal()
        else:
            self.reveal()
        self.shown = not self.shown


class MicSlider(Scale):
    def __init__(self, audio, **kwargs):
        super().__init__(
            name="control-slider",
            orientation="h",
            h_expand=True,
            has_origin=True,
            increments=(0.01, 0.1),
            **kwargs,
        )
        self.audio = audio
        self.audio.connect("notify::microphone", self.on_new_microphone)
        if self.audio.microphone:
            self.audio.microphone.connect("changed", self.on_microphone_changed)
        self.connect("value-changed", self.on_value_changed)
        self.add_style_class("mic")
        self.on_microphone_changed()

    def on_new_microphone(self, *args):
        if self.audio.microphone:
            self.audio.microphone.connect("changed", self.on_microphone_changed)
            self.on_microphone_changed()

    def on_value_changed(self, _):
        if self.audio.microphone:
            self.audio.microphone.volume = self.value * 100

    def on_microphone_changed(self, *_):
        if not self.audio.microphone:
            return
        self.value = self.audio.microphone.volume / 100

        if self.audio.microphone.muted:
            self.add_style_class("muted")
        else:
            self.remove_style_class("muted")


class MicIcon(Button):
    def __init__(self, audio: Audio, **kwargs):
        super().__init__(name="volume-icon", **kwargs)
        self.audio = audio
        self.value = 0
        self.hide_timer = None
        self.hover_counter = 0

        self.label = Label(
            name="volume-icon-label",
            markup=icons.mic,
        )
        self.connect("clicked", self.on_clicked)
        self.add(self.label)

        self.set_icon()

    def set_icon(self):
        if not self.audio or not self.audio.microphone:
            return
        if self.audio.microphone.muted:
            icon = icons.mic_muted
        else:
            icon = icons.mic
        self.label.set_markup(icon)

    def on_clicked(self, _):
        self.audio.microphone.muted = not self.audio.microphone.muted
        self.set_icon()


class MicRow(Box):
    def __init__(self, slot=None, **kwargs):
        super().__init__(
            name="mic-row",
            orientation="h",
            spacing=12,
            **kwargs,
        )

        self.slot = slot
        self.audio = Audio()

        self.mic_slider = MicSlider(self.audio)
        self.mic_icon = MicIcon(self.audio)
        self.audio.connect("notify::microphone", self.on_new_microphone)

        self.add(self.mic_icon)
        self.add(self.mic_slider)

    def on_new_microphone(self, *args):
        if self.audio.microphone:
            self.audio.microphone.stream.connect(
                "notify::microphone_changed", self.on_microphone_changed
            )

    def on_microphone_changed(self, *_):
        print(self.audio.microphone.application_id)
        if not self.audio.microphone:
            return
        self.value = self.audio.microphone.volume / 100
        # TODO: display row only if microphone is in use

        if self.audio.microphone.muted:
            self.add_style_class("muted")
        else:
            self.remove_style_class("muted")


class VolumeRow(Box):
    def __init__(self, slot=None, **kwargs):
        super().__init__(
            name="volume-row",
            orientation="h",
            spacing=12,
            **kwargs,
        )

        self.slot = slot
        self.audio = Audio()
        self.outputs_box = VolumeOutputsRevealer()
        self.output_box_button = Button(
            name="bt-outputs-open-button",
            child=Label(markup=icons.chevron_right),
            v_expand=True,
            h_align="center",
            v_align="center",
            on_clicked=lambda _: (self.outputs_box.toggle(), self.notify()),
        )

        self.audio.connect("notify::speaker", self.notify)
        if self.audio.speaker:
            self.audio.speaker.connect("changed", self.notify)

        self.volume_slider = VolumeSlider(self.audio, notify=self.notify)
        self.volume_icon = VolumeIcon(self.audio)

        self.add(self.volume_icon)
        self.add(self.volume_slider)
        self.add(self.output_box_button)
        self.slot.add(self.outputs_box)

    def notify(self, *args):
        self._clear_slot()
        for speaker in self.audio.get_speakers():
            self.add_output(speaker)

        if self.audio.speaker:
            self.volume_slider.on_speaker_changed()
            self.volume_icon.set_icon()
            self.volume_slider.on_new_speaker(*args)

    def _clear_slot(self):
        for child in self.outputs_box.output_container.get_children():
            self.outputs_box.output_container.remove(child)

    def switch_to_output(self, output):
        print(output)

    def add_output(self, output):
        row = CenterBox(
            start_children=Label(label=output.name[:20] or "Unknown Output"),
            end_children=Label(markup=icons.chevron_right),
            h_expand=True,
            h_align="fill",
            v_align="center",
            orientation="h",
        )
        button = Button(
            orientation="h",
            h_align="start",
            spacing=12,
            h_expand=True,
            child=row,
            on_clicked=lambda _: self.switch_to_output(output),
        )
        button.add_style_class("bt-output-item")
        self.outputs_box.output_container.add(button)
