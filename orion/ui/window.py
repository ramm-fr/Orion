"""Main application window with GNOME/Adwaita styling."""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gst', '1.0')

from gi.repository import Gtk, Adw, Gdk, Gio, GLib, Gst, GObject
import os
from pathlib import Path

from orion.core.player import Player, PlaybackState, RepeatMode
from orion.core.playlist import PlaylistManager, PlaylistItem, Playlist
from orion.core.library import Library
from orion.core.settings import Settings
from orion.core.statistics import Statistics
from orion.ui.controls import PlayerControls
from orion.ui.video_area import VideoArea
from orion.ui.browse import BrowsePopup
from orion.ui.dialogs import (
    EqualizerDialog, SubtitleDialog,
    SettingsDialog, StatisticsDialog, AboutDialog, StreamDialog
)
from orion.ui.headerbar import HeaderBar


class OrionWindow(Adw.ApplicationWindow):
    """Main application window."""

    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("Orion")
        self.set_default_size(1200, 720)
        self.set_size_request(640, 480)

        # Core components
        self.player = Player()
        self.playlist_manager = PlaylistManager()
        self.library = Library()
        self.settings = Settings()
        self.statistics = Statistics()

        # State
        self._fullscreen = False
        self._mini_player = False
        self._pip_mode = False
        self._theatre_mode = False

        # Build UI
        self._build_ui()
        self._connect_signals()
        self._setup_keyboard_shortcuts()
        self._setup_drag_drop()

        # Apply settings
        self._apply_settings()

        # Initial library scan
        GLib.idle_add(self._initial_scan)

    def _build_ui(self):
        """Build the main UI layout."""
        # Main layout
        self._main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(self._main_box)

        # Header bar
        self.headerbar = HeaderBar(self)
        self._main_box.append(self.headerbar)

        # Toast overlay for notifications
        self._toast_overlay = Adw.ToastOverlay()
        self._main_box.append(self._toast_overlay)
        self._toast_overlay.set_vexpand(True)

        # Content area
        self._content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._toast_overlay.set_child(self._content_box)

        # Video area with controls as overlay
        self._video_overlay = Gtk.Overlay()
        self._video_overlay.set_vexpand(True)
        self._content_box.append(self._video_overlay)

        # Video area (fills full space)
        self.video_area = VideoArea(self.player)
        self._video_overlay.set_child(self.video_area)

        # Player controls (floating at the bottom, on top of video)
        self.controls = PlayerControls(self)
        self.controls.set_halign(Gtk.Align.FILL)
        self.controls.set_valign(Gtk.Align.END)
        self._video_overlay.add_overlay(self.controls)

        # Auto-hide state
        self._hide_timer = None
        self._controls_visible = True
        self._hide_cooldown = False

    def show_controls(self):
        """Show controls."""
        if self._controls_visible or self._hide_cooldown:
            return
        self._controls_visible = True
        self.controls.set_visible(True)

    def _hide_controls(self):
        """Hide controls (called from hide button only)."""
        self._controls_visible = False
        self._hide_cooldown = True
        self.controls.set_visible(False)
        # Cooldown: ignore mouse events for 500ms after hiding
        GLib.timeout_add(500, self._end_cooldown)

    def _end_cooldown(self):
        self._hide_cooldown = False
        return False

    def _connect_signals(self):
        """Connect player and UI signals."""
        self.player.connect('state-changed', self._on_state_changed)
        self.player.connect('position-changed', self._on_position_changed)
        self.player.connect('eos', self._on_eos)
        self.player.connect('error', self._on_error)
        self.player.connect('volume-changed', self._on_volume_changed)

    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts."""
        controller = Gtk.EventControllerKey()
        controller.connect('key-pressed', self._on_key_pressed)
        self.add_controller(controller)

    def _setup_drag_drop(self):
        """Setup drag and drop for files."""
        drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
        drop_target.connect('drop', self._on_file_dropped)
        self.video_area.add_controller(drop_target)

    def _apply_settings(self):
        """Apply saved settings."""
        vol = self.settings.get('default_volume', 1.0)
        self.player.set_volume(vol)

    def _initial_scan(self):
        """Perform initial library scan."""
        self.library.scan_all()
        return False

    # Signal handlers
    def _on_state_changed(self, player, state):
        self.controls.update_play_state(PlaybackState(state))

    def _on_position_changed(self, player, position, duration):
        self.controls.update_position(position, duration)

    def _on_eos(self, player):
        """Handle end of stream."""
        # Record statistics
        current = self.playlist_manager.active_playlist
        if current and current.get_current():
            item = current.get_current()
            self.statistics.record_play(
                item.uri, item.title,
                self.player.get_duration() / Gst.SECOND,
                'video'
            )

        # Handle repeat/next
        if self.player.repeat_mode == RepeatMode.ALL:
            self._play_next()
        elif self.player.repeat_mode == RepeatMode.ONE:
            self.player.seek(0)
            self.player.play()
        else:
            self._play_next()

    def _on_error(self, player, message):
        self.show_toast(f"Error: {message}")

    def _on_volume_changed(self, player, volume):
        self.controls.update_volume(volume)

    def _on_key_pressed(self, controller, keyval, keycode, state):
        """Handle keyboard shortcuts."""
        key = Gdk.keyval_name(keyval)
        ctrl = state & Gdk.ModifierType.CONTROL_MASK

        shortcuts = self.settings.get('shortcuts', {})

        if key == shortcuts.get('play_pause', 'space') or key == 'space':
            self.player.toggle_play_pause()
            return True
        elif key == shortcuts.get('fullscreen', 'f') or key == 'f':
            if not ctrl:
                self.toggle_fullscreen()
                return True
        elif key == shortcuts.get('mute', 'm') or key == 'm':
            self.player.toggle_mute()
            self.controls.update_mute(self.player.get_mute())
            return True
        elif key == 'Escape':
            if self._fullscreen:
                self.toggle_fullscreen()
            return True
        elif key == shortcuts.get('seek_forward', 'Right') or key == 'Right':
            self.player.fast_forward(10)
            return True
        elif key == shortcuts.get('seek_backward', 'Left') or key == 'Left':
            self.player.rewind(10)
            return True
        elif key == 'Up':
            vol = min(1.5, self.player.get_volume() + 0.05)
            self.player.set_volume(vol)
            return True
        elif key == 'Down':
            vol = max(0.0, self.player.get_volume() - 0.05)
            self.player.set_volume(vol)
            return True
        elif key == 'n':
            self._play_next()
            return True
        elif key == 'p':
            self._play_previous()
            return True
        elif key == 's':
            self.player.stop()
            return True
        elif key == 'period':
            self.player.step_frame()
            return True
        elif key == 'bracketright':
            self.player.fast_forward(30)
            return True
        elif key == 'bracketleft':
            self.player.rewind(30)
            return True
        elif key == 'Print' or (ctrl and key == 'p'):
            self._take_screenshot()
            return True
        elif ctrl and key == 'o':
            self.open_file_dialog()
            return True
        elif ctrl and key == 'l':
            self.open_stream_dialog()
            return True
        return False

    def _on_file_dropped(self, target, value, x, y):
        """Handle dropped files."""
        if isinstance(value, Gio.File):
            path = value.get_path()
            if path:
                self.play_file(path)
            return True
        return False

    # Public methods
    def play_file(self, filepath):
        """Play a file by path."""
        uri = filepath if '://' in filepath else f'file://{filepath}'
        self.player.set_uri(uri)
        self.player.play()

        # Add to playlist
        item = PlaylistItem(uri=uri, title=Path(filepath).stem if '://' not in filepath else filepath)
        self.playlist_manager.add_to_recently_played(item)

        # Update title
        title = item.title
        self.set_title(f"{title} — Orion")
        self.headerbar.set_now_playing(title)

    def play_uri(self, uri):
        """Play a URI (network stream, etc.)."""
        self.player.set_uri(uri)
        self.player.play()
        self.set_title(f"Stream — Orion")
        self.headerbar.set_now_playing("Network Stream")

    def _play_next(self):
        """Play next item in playlist."""
        playlist = self.playlist_manager.active_playlist
        if playlist:
            item = playlist.next(
                shuffle=self.player.shuffle,
                repeat_mode=int(self.player.repeat_mode)
            )
            if item:
                self.play_file(item.uri)
        else:
            self.player.stop()

    def _play_previous(self):
        """Play previous item."""
        playlist = self.playlist_manager.active_playlist
        if playlist:
            item = playlist.previous()
            if item:
                self.play_file(item.uri)

    def toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        if self._fullscreen:
            self.unfullscreen()
            self.headerbar.set_visible(True)
            self.controls.set_visible(True)
            self._controls_visible = True
        else:
            self.fullscreen()
            self.headerbar.set_visible(False)
            self.show_controls()
        self._fullscreen = not self._fullscreen

    def toggle_mini_player(self):
        """Toggle mini player mode."""
        if self._mini_player:
            self.set_default_size(1200, 720)
            self._mini_player = False
        else:
            self.set_default_size(400, 300)
            self._mini_player = True

    def toggle_always_on_top(self):
        """Toggle always on top (requires compositor support)."""
        # GTK4 doesn't have direct always-on-top, use present
        self.present()

    def _take_screenshot(self):
        """Take a screenshot of the current video frame."""
        path = self.player.take_screenshot()
        if path:
            self.show_toast(f"Screenshot saved: {os.path.basename(path)}")
        else:
            self.show_toast("Could not capture screenshot")

    def show_toast(self, message):
        """Show a toast notification."""
        toast = Adw.Toast.new(message)
        toast.set_timeout(3)
        self._toast_overlay.add_toast(toast)

    def open_file_dialog(self):
        """Open file chooser dialog."""
        dialog = Gtk.FileDialog()
        dialog.set_title("Open Media File")

        # Filters
        filters = Gio.ListStore.new(Gtk.FileFilter)

        video_filter = Gtk.FileFilter()
        video_filter.set_name("Video Files")
        for ext in ['*.mp4', '*.mkv', '*.avi', '*.mov', '*.wmv', '*.flv', '*.webm', '*.m4v',
                    '*.mpg', '*.mpeg', '*.3gp', '*.ogv', '*.ts', '*.vob', '*.3g2', '*.asf',
                    '*.divx', '*.f4v', '*.m2ts', '*.mts', '*.rm', '*.rmvb', '*.qt',
                    '*.amv', '*.dv', '*.gifv', '*.h264', '*.h265', '*.hevc', '*.xvid']:
            video_filter.add_pattern(ext)
        filters.append(video_filter)

        audio_filter = Gtk.FileFilter()
        audio_filter.set_name("Audio Files")
        for ext in ['*.mp3', '*.flac', '*.ogg', '*.wav', '*.aac', '*.m4a', '*.opus']:
            audio_filter.add_pattern(ext)
        filters.append(audio_filter)

        all_filter = Gtk.FileFilter()
        all_filter.set_name("All Media Files")
        for ext in ['*.mp4', '*.mkv', '*.avi', '*.mov', '*.mp3', '*.flac', '*.ogg',
                    '*.wav', '*.aac', '*.webm', '*.m4v', '*.m4a', '*.opus', '*.wmv']:
            all_filter.add_pattern(ext)
        filters.append(all_filter)

        dialog.set_filters(filters)
        dialog.open(self, None, self._on_file_dialog_response)

    def _on_file_dialog_response(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                path = file.get_path()
                self.play_file(path)
        except GLib.Error:
            pass

    def open_folder_dialog(self):
        """Open folder chooser."""
        dialog = Gtk.FileDialog()
        dialog.set_title("Open Folder")
        dialog.select_folder(self, None, self._on_folder_dialog_response)

    def _on_folder_dialog_response(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                path = folder.get_path()
                self.library.add_folder(path)
                self.show_toast(f"Added folder: {os.path.basename(path)}")
        except GLib.Error:
            pass

    def open_stream_dialog(self):
        """Open network stream dialog."""
        dialog = StreamDialog(self)
        dialog.present()

    def open_equalizer(self):
        """Open equalizer dialog."""
        dialog = EqualizerDialog(self)
        dialog.present()

    def open_browse(self):
        """Open browse popup."""
        popup = BrowsePopup(self)
        popup.present()

    def open_subtitle_dialog(self):
        """Open subtitle settings dialog."""
        try:
            dialog = SubtitleDialog(self)
            dialog.present()
        except Exception as e:
            self.show_toast(f"Error: {e}")

    def open_settings(self):
        """Open settings dialog."""
        dialog = SettingsDialog(self)
        dialog.present()

    def open_statistics(self):
        """Open statistics dialog."""
        dialog = StatisticsDialog(self)
        dialog.present()

    def open_about(self):
        """Open about dialog."""
        dialog = AboutDialog(self)
        dialog.present()

    def do_close_request(self):
        """Handle window close."""
        # Save state
        if self.player.state == PlaybackState.PLAYING:
            pos = self.player.get_position()
            # Save position for resume
            self.settings.set('last_position', pos)

        self.player.cleanup()
        self.playlist_manager.save()
        self.library.save()
        self.statistics.save()
        self.settings.save()
        return False
