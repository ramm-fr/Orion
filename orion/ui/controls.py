"""Player controls bar with GNOME styling."""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gst', '1.0')

from gi.repository import Gtk, Adw, Gst, GLib
from orion.core.player import PlaybackState, RepeatMode


def format_time(ns):
    """Format nanoseconds to HH:MM:SS or MM:SS."""
    if ns <= 0:
        return "0:00"
    seconds = int(ns / Gst.SECOND)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


class PlayerControls(Gtk.Box):
    """Bottom player controls with seek bar, playback buttons, and volume."""

    def __init__(self, window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window = window
        self.player = window.player
        self._seeking = False

        self.add_css_class('player-controls')
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_bottom(8)
        self.set_margin_top(4)

        # Seek bar row
        self._build_seek_bar()

        # Controls row
        self._build_controls()

    def _build_seek_bar(self):
        """Build the seek bar with time labels."""
        seek_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        seek_box.set_margin_bottom(4)
        self.append(seek_box)

        # Current time
        self._time_label = Gtk.Label(label="0:00")
        self._time_label.add_css_class('caption')
        self._time_label.set_width_chars(7)
        self._time_label.set_xalign(1.0)
        seek_box.append(self._time_label)

        # Seek slider
        self._seek_scale = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL,
            adjustment=Gtk.Adjustment(value=0, lower=0, upper=1000, step_increment=1)
        )
        self._seek_scale.set_hexpand(True)
        self._seek_scale.set_draw_value(False)
        self._seek_scale.add_css_class('seek-slider')
        self._seek_scale.connect('change-value', self._on_seek_change)
        seek_box.append(self._seek_scale)

        # Duration / remaining
        self._duration_label = Gtk.Label(label="0:00")
        self._duration_label.add_css_class('caption')
        self._duration_label.set_width_chars(7)
        self._duration_label.set_xalign(0.0)
        seek_box.append(self._duration_label)

    def _build_controls(self):
        """Build playback control buttons."""
        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        controls_box.set_halign(Gtk.Align.FILL)
        self.append(controls_box)

        # Left: Volume and extra controls
        left_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        left_box.set_hexpand(True)
        left_box.set_halign(Gtk.Align.START)
        controls_box.append(left_box)

        # Volume button
        self._volume_btn = Gtk.Button(icon_name='audio-volume-high-symbolic')
        self._volume_btn.add_css_class('flat')
        self._volume_btn.set_tooltip_text("Mute (M)")
        self._volume_btn.connect('clicked', self._on_mute_clicked)
        left_box.append(self._volume_btn)

        # Volume slider
        self._volume_scale = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL,
            adjustment=Gtk.Adjustment(value=100, lower=0, upper=150, step_increment=5)
        )
        self._volume_scale.set_size_request(100, -1)
        self._volume_scale.set_draw_value(False)
        self._volume_scale.add_css_class('volume-slider')
        self._volume_scale.connect('value-changed', self._on_volume_changed)
        left_box.append(self._volume_scale)

        # Speed control
        self._speed_btn = Gtk.MenuButton(label="1.0x")
        self._speed_btn.add_css_class('flat')
        self._speed_btn.set_tooltip_text("Playback Speed")
        self._speed_btn.set_popover(self._build_speed_popover())
        left_box.append(self._speed_btn)

        # Center: Main playback buttons
        center_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        center_box.set_halign(Gtk.Align.CENTER)
        controls_box.append(center_box)

        # Shuffle
        self._shuffle_btn = Gtk.ToggleButton(icon_name='media-playlist-shuffle-symbolic')
        self._shuffle_btn.add_css_class('flat')
        self._shuffle_btn.set_tooltip_text("Shuffle")
        self._shuffle_btn.connect('toggled', self._on_shuffle_toggled)
        center_box.append(self._shuffle_btn)

        # Previous
        prev_btn = Gtk.Button(icon_name='media-skip-backward-symbolic')
        prev_btn.add_css_class('flat')
        prev_btn.set_tooltip_text("Previous (P)")
        prev_btn.connect('clicked', lambda b: self.window._play_previous())
        center_box.append(prev_btn)

        # Rewind
        rew_btn = Gtk.Button(icon_name='media-seek-backward-symbolic')
        rew_btn.add_css_class('flat')
        rew_btn.set_tooltip_text("Rewind 10s ([)")
        rew_btn.connect('clicked', lambda b: self.player.rewind(10))
        center_box.append(rew_btn)

        # Play/Pause (larger)
        self._play_btn = Gtk.Button(icon_name='media-playback-start-symbolic')
        self._play_btn.add_css_class('circular')
        self._play_btn.add_css_class('suggested-action')
        self._play_btn.set_tooltip_text("Play/Pause (Space)")
        self._play_btn.connect('clicked', self._on_play_clicked)
        center_box.append(self._play_btn)

        # Stop
        stop_btn = Gtk.Button(icon_name='media-playback-stop-symbolic')
        stop_btn.add_css_class('flat')
        stop_btn.set_tooltip_text("Stop (S)")
        stop_btn.connect('clicked', lambda b: self.player.stop())
        center_box.append(stop_btn)

        # Fast forward
        ff_btn = Gtk.Button(icon_name='media-seek-forward-symbolic')
        ff_btn.add_css_class('flat')
        ff_btn.set_tooltip_text("Forward 10s (])")
        ff_btn.connect('clicked', lambda b: self.player.fast_forward(10))
        center_box.append(ff_btn)

        # Next
        next_btn = Gtk.Button(icon_name='media-skip-forward-symbolic')
        next_btn.add_css_class('flat')
        next_btn.set_tooltip_text("Next (N)")
        next_btn.connect('clicked', lambda b: self.window._play_next())
        center_box.append(next_btn)

        # Repeat
        self._repeat_btn = Gtk.Button(icon_name='media-playlist-repeat-symbolic')
        self._repeat_btn.add_css_class('flat')
        self._repeat_btn.set_tooltip_text("Repeat")
        self._repeat_btn.connect('clicked', self._on_repeat_clicked)
        center_box.append(self._repeat_btn)

        # Right: Extra controls
        right_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        right_box.set_hexpand(True)
        right_box.set_halign(Gtk.Align.END)
        controls_box.append(right_box)

        # Browse toggle button
        self._browse_btn = Gtk.Button(icon_name='view-grid-symbolic')
        self._browse_btn.add_css_class('flat')
        self._browse_btn.set_tooltip_text("Browse Videos")
        self._browse_btn.connect('clicked', self._on_browse_clicked)
        right_box.append(self._browse_btn)

        # Subtitle track selector
        self._sub_track_btn = Gtk.MenuButton(icon_name='media-view-subtitles-symbolic')
        self._sub_track_btn.add_css_class('flat')
        self._sub_track_btn.set_tooltip_text("Subtitles")
        self._sub_popover = Gtk.Popover()
        self._sub_track_btn.set_popover(self._sub_popover)
        right_box.append(self._sub_track_btn)

        # Equalizer
        eq_btn = Gtk.Button(icon_name='audio-speakers-symbolic')
        eq_btn.add_css_class('flat')
        eq_btn.set_tooltip_text("Equalizer")
        eq_btn.connect('clicked', lambda b: self.window.open_equalizer())
        right_box.append(eq_btn)

        # Audio track selector
        self._audio_track_btn = Gtk.MenuButton(icon_name='audio-x-generic-symbolic')
        self._audio_track_btn.add_css_class('flat')
        self._audio_track_btn.set_tooltip_text("Audio Track")
        self._audio_track_btn.set_sensitive(False)
        self._audio_track_popover = Gtk.Popover()
        self._audio_track_btn.set_popover(self._audio_track_popover)
        right_box.append(self._audio_track_btn)

        # Screenshot
        ss_btn = Gtk.Button(icon_name='camera-photo-symbolic')
        ss_btn.add_css_class('flat')
        ss_btn.set_tooltip_text("Screenshot (Print)")
        ss_btn.connect('clicked', lambda b: self.window._take_screenshot())
        right_box.append(ss_btn)

        # Aspect ratio
        self._aspect_btn = Gtk.Button(icon_name='view-fullscreen-symbolic')
        self._aspect_btn.add_css_class('flat')
        self._aspect_btn.set_tooltip_text("Aspect Ratio")
        self._aspect_btn.connect('clicked', self._on_aspect_clicked)
        right_box.append(self._aspect_btn)

        # Hide controls button (last button)
        hide_btn = Gtk.Button(icon_name='go-down-symbolic')
        hide_btn.add_css_class('flat')
        hide_btn.set_tooltip_text("Hide Controls")
        hide_btn.connect('clicked', self._on_close_controls)
        right_box.append(hide_btn)

    def _build_speed_popover(self):
        """Build speed selection popover."""
        popover = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)
        popover.set_child(box)

        speeds = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 3.0, 4.0]
        for speed in speeds:
            btn = Gtk.Button(label=f"{speed}x")
            btn.add_css_class('flat')
            btn.connect('clicked', self._on_speed_selected, speed, popover)
            box.append(btn)

        return popover

    # Event handlers
    def _on_seek_change(self, scale, scroll_type, value):
        if self.player.get_duration() > 0:
            position = int(value / 1000.0 * self.player.get_duration())
            self.player.seek(position)
        return False

    def _on_play_clicked(self, button):
        self.player.toggle_play_pause()

    def _on_mute_clicked(self, button):
        self.player.toggle_mute()
        self.update_mute(self.player.get_mute())

    def _on_volume_changed(self, scale):
        volume = scale.get_value() / 100.0
        self.player.set_volume(volume)

    def _on_shuffle_toggled(self, button):
        self.player.shuffle = button.get_active()

    def _on_repeat_clicked(self, button):
        current = int(self.player.repeat_mode)
        new_mode = (current + 1) % 3
        self.player.repeat_mode = new_mode

        if new_mode == RepeatMode.NONE:
            button.set_icon_name('media-playlist-repeat-symbolic')
            button.remove_css_class('accent')
            button.set_tooltip_text("Repeat: Off")
        elif new_mode == RepeatMode.ONE:
            button.set_icon_name('media-playlist-repeat-song-symbolic')
            button.add_css_class('accent')
            button.set_tooltip_text("Repeat: One")
        else:
            button.set_icon_name('media-playlist-repeat-symbolic')
            button.add_css_class('accent')
            button.set_tooltip_text("Repeat: All")

    def _on_speed_selected(self, button, speed, popover):
        self.player.set_playback_speed(speed)
        self._speed_btn.set_label(f"{speed}x")
        popover.popdown()

    # Public update methods
    def update_play_state(self, state):
        if state == PlaybackState.PLAYING:
            self._play_btn.set_icon_name('media-playback-pause-symbolic')
            # Update audio tracks
            GLib.timeout_add(2000, self._update_audio_tracks)
        else:
            self._play_btn.set_icon_name('media-playback-start-symbolic')
            # Show controls when not playing
            self.set_visible(True)
            window = self.get_root()
            if window:
                window._controls_visible = True

    def _update_audio_tracks(self):
        """Update audio and subtitle track buttons based on available tracks."""
        # Audio tracks
        n_audio = self.player.get_audio_track_count()
        if n_audio > 1:
            self._audio_track_btn.set_sensitive(True)
            self._audio_track_btn.set_tooltip_text(f"Audio Track ({n_audio} available)")
            self._build_audio_track_popover(n_audio)
        else:
            self._audio_track_btn.set_sensitive(False)
            self._audio_track_btn.set_tooltip_text("Audio Track (only 1)")

        # Subtitle tracks
        n_text = self.player.get_subtitle_track_count()
        self._build_subtitle_popover(n_text)
        return False

    def _build_audio_track_popover(self, n_audio):
        """Build the audio track selection popover."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)

        for i in range(n_audio):
            info = self.player.get_audio_track_info(i)
            lang = info.get('language', '')
            title = info.get('title', '')
            if lang:
                label = f"{lang}"
                if title:
                    label = f"{lang} — {title}"
            else:
                label = f"Track {i + 1}"

            btn = Gtk.Button(label=label)
            btn.add_css_class('flat')
            btn.connect('clicked', self._on_audio_track_selected, i)
            box.append(btn)

        self._audio_track_popover.set_child(box)

    def _on_audio_track_selected(self, button, index):
        """Switch audio track."""
        self.player.set_audio_track(index)
        info = self.player.get_audio_track_info(index)
        lang = info.get('language', f'Track {index + 1}')
        self.window.show_toast(f"Audio: {lang}")
        self._audio_track_popover.popdown()

    def _build_subtitle_popover(self, n_text):
        """Build the subtitle track selection popover."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)

        # Disable subtitles option
        off_btn = Gtk.Button(label="Off")
        off_btn.add_css_class('flat')
        off_btn.connect('clicked', self._on_subtitle_off)
        box.append(off_btn)

        if n_text > 0:
            box.append(Gtk.Separator())

        # Embedded subtitle tracks
        for i in range(n_text):
            info = self.player.get_subtitle_track_info(i)
            lang = info.get('language', '')
            title = info.get('title', '')
            if lang:
                label = lang
                if title:
                    label = f"{lang} — {title}"
            else:
                label = f"Subtitle {i + 1}"

            btn = Gtk.Button(label=label)
            btn.add_css_class('flat')
            btn.connect('clicked', self._on_subtitle_track_selected, i)
            box.append(btn)

        # Separator + settings option
        box.append(Gtk.Separator())
        settings_btn = Gtk.Button(label="Subtitle Settings…")
        settings_btn.add_css_class('flat')
        settings_btn.connect('clicked', self._on_open_subtitle_settings)
        box.append(settings_btn)

        self._sub_popover.set_child(box)

    def _on_subtitle_off(self, button):
        """Disable subtitles."""
        self.player.set_subtitle_visible(False)
        self.window.show_toast("Subtitles: Off")
        self._sub_popover.popdown()

    def _on_subtitle_track_selected(self, button, index):
        """Switch subtitle track."""
        self.player.set_subtitle_visible(True)
        self.player.set_subtitle_track(index)
        info = self.player.get_subtitle_track_info(index)
        lang = info.get('language', f'Subtitle {index + 1}')
        self.window.show_toast(f"Subtitles: {lang}")
        self._sub_popover.popdown()

    def _on_open_subtitle_settings(self, button):
        """Open full subtitle settings dialog."""
        self._sub_popover.popdown()
        # Delay to let popover close first
        GLib.timeout_add(100, lambda: self.window.open_subtitle_dialog() or False)

    def update_position(self, position, duration):
        if duration > 0:
            progress = position / duration * 1000.0
            self._seek_scale.get_adjustment().set_value(progress)
            self._time_label.set_label(format_time(position))
            self._duration_label.set_label(f"-{format_time(duration - position)}")

    def update_volume(self, volume):
        self._volume_scale.set_value(volume * 100)
        self._update_volume_icon(volume)

    def update_mute(self, muted):
        if muted:
            self._volume_btn.set_icon_name('audio-volume-muted-symbolic')
        else:
            self._update_volume_icon(self.player.get_volume())

    def _update_volume_icon(self, volume):
        if volume == 0:
            self._volume_btn.set_icon_name('audio-volume-muted-symbolic')
        elif volume < 0.33:
            self._volume_btn.set_icon_name('audio-volume-low-symbolic')
        elif volume < 0.66:
            self._volume_btn.set_icon_name('audio-volume-medium-symbolic')
        else:
            self._volume_btn.set_icon_name('audio-volume-high-symbolic')

    def _on_browse_clicked(self, button):
        """Open the browse popup."""
        self.window.open_browse()

    def _on_close_controls(self, button):
        """Hide the entire controls bar."""
        window = self.get_root()
        if window:
            window._hide_controls()

    def _on_aspect_clicked(self, button):
        """Cycle aspect ratio."""
        name = self.window.video_area.cycle_aspect_ratio()
        self.window.show_toast(f"Aspect Ratio: {name}")
