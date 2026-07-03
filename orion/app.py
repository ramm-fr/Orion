"""Orion Application - Main GTK4/Adwaita application class."""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gst', '1.0')

from gi.repository import Gtk, Adw, Gio, GLib, Gdk, Gst
import sys
import os

from orion import __app_id__, __app_name__, __version__
from orion.ui.window import OrionWindow


class OrionApplication(Adw.Application):
    """Main Orion application."""

    def __init__(self):
        super().__init__(
            application_id=__app_id__,
            flags=Gio.ApplicationFlags.HANDLES_OPEN,
        )
        self.window = None

        # Initialize GStreamer
        Gst.init(None)

    def do_startup(self):
        Adw.Application.do_startup(self)

        # Register custom icon path
        icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        icon_theme.add_search_path(str(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'icons')))
        self._setup_actions()
        self._load_css()

    def do_activate(self):
        if not self.window:
            self.window = OrionWindow(self)
        self.window.present()

    def do_open(self, files, n_files, hint):
        """Handle files opened from file manager."""
        self.do_activate()
        if files:
            filepath = files[0].get_path()
            if filepath:
                self.window.play_file(filepath)

    def _setup_actions(self):
        """Setup application actions for menus."""
        actions = [
            ('open-file', self._on_open_file),
            ('open-folder', self._on_open_folder),
            ('open-stream', self._on_open_stream),
            ('equalizer', self._on_equalizer),
            ('subtitle-settings', self._on_subtitle_settings),
            ('statistics', self._on_statistics),
            ('mini-player', self._on_mini_player),
            ('always-on-top', self._on_always_on_top),
            ('preferences', self._on_preferences),
            ('shortcuts', self._on_shortcuts),
            ('about', self._on_about),
            ('quit', self._on_quit),
        ]

        for name, callback in actions:
            action = Gio.SimpleAction.new(name, None)
            action.connect('activate', callback)
            self.add_action(action)

        # Keyboard shortcuts
        self.set_accels_for_action('app.open-file', ['<Control>o'])
        self.set_accels_for_action('app.open-stream', ['<Control>l'])
        self.set_accels_for_action('app.quit', ['<Control>q'])
        self.set_accels_for_action('app.preferences', ['<Control>comma'])

    def _load_css(self):
        """Load custom CSS stylesheet."""
        css_provider = Gtk.CssProvider()
        css_data = self._get_css()
        css_provider.load_from_string(css_data)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _get_css(self):
        """Return application CSS."""
        return """
        /* Orion Video Player - GNOME Style */

        .video-area {
            background-color: #000000;
            border-radius: 0;
        }

        .home-screen {
            background-color: #1a1a1a;
        }

        .home-screen.drag-hover {
            background-color: #2a2a2a;
            border: 2px dashed rgba(255, 255, 255, 0.3);
        }

        .stat-card {
            background-color: #2a2a2a;
            border-radius: 12px;
            padding: 16px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }

        .graph-area {
            border-radius: 12px;
        }

        .player-controls {
            padding: 8px 16px;
            border-radius: 12px 12px 0 0;
            transition: opacity 300ms ease;
            background-color: alpha(black, 0.7);
        }

        .seek-slider trough {
            min-height: 8px;
            border-radius: 99px;
            background-color: rgba(255, 255, 255, 0.2);
        }

        .seek-slider trough highlight {
            border-radius: 99px;
            background-color: #ffffff;
        }

        .seek-slider slider {
            min-width: 0px;
            min-height: 0px;
            margin: 0;
            padding: 0;
            background: transparent;
            border: none;
            box-shadow: none;
            opacity: 0;
        }

        .volume-slider {
            margin-top: 0;
            margin-bottom: 0;
        }

        .volume-slider trough {
            min-height: 6px;
            border-radius: 99px;
            background-color: rgba(255, 255, 255, 0.2);
        }

        .volume-slider trough highlight {
            border-radius: 99px;
            background-color: #ffffff;
        }

        .volume-slider slider {
            min-width: 0px;
            min-height: 0px;
            margin: 0;
            padding: 0;
            background: transparent;
            border: none;
            box-shadow: none;
            opacity: 0;
        }

        /* Browse popup */
        .browse-popup {
            border-radius: 16px;
        }

        .folder-card {
            border-radius: 12px;
            padding: 12px;
        }

        .folder-card:hover {
            background-color: alpha(@accent_bg_color, 0.1);
        }

        .folder-icon-box {
            background-color: #2d2d2d;
            border-radius: 14px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            min-height: 120px;
        }

        .video-card {
            border-radius: 12px;
            padding: 8px;
        }

        .video-card:hover {
            background-color: alpha(@accent_bg_color, 0.15);
        }

        .video-thumbnail {
            background-color: #2a2a2a;
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            min-height: 85px;
        }

        .title-1 {
            font-size: 48px;
        }

        .title-2 {
            font-size: 24px;
            font-weight: bold;
        }

        .circular {
            min-width: 48px;
            min-height: 48px;
            border-radius: 50%;
        }

        /* Fullscreen overlay */
        .fullscreen-controls {
            background-color: alpha(black, 0.7);
            border-radius: 12px;
            padding: 12px;
            margin: 12px;
        }

        /* Mini player */
        .mini-player {
            border-radius: 12px;
        }

        /* Toast styling */
        toast {
            border-radius: 99px;
        }
        """

    # Action callbacks
    def _on_open_file(self, action, param):
        if self.window:
            self.window.open_file_dialog()

    def _on_open_folder(self, action, param):
        if self.window:
            self.window.open_folder_dialog()

    def _on_open_stream(self, action, param):
        if self.window:
            self.window.open_stream_dialog()

    def _on_equalizer(self, action, param):
        if self.window:
            self.window.open_equalizer()

    def _on_subtitle_settings(self, action, param):
        if self.window:
            self.window.open_subtitle_dialog()

    def _on_statistics(self, action, param):
        if self.window:
            self.window.open_statistics()

    def _on_mini_player(self, action, param):
        if self.window:
            self.window.toggle_mini_player()

    def _on_always_on_top(self, action, param):
        if self.window:
            self.window.toggle_always_on_top()

    def _on_preferences(self, action, param):
        if self.window:
            self.window.open_settings()

    def _on_shortcuts(self, action, param):
        if self.window:
            self.window.open_settings()

    def _on_about(self, action, param):
        if self.window:
            self.window.open_about()

    def _on_quit(self, action, param):
        self.quit()


def main():
    """Application entry point."""
    app = OrionApplication()
    return app.run(sys.argv)
