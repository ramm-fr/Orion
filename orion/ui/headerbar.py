"""Custom header bar with GNOME styling."""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio


class HeaderBar(Gtk.Box):
    """Application header bar wrapper with menu and search."""

    def __init__(self, window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.window = window

        # Use Adw.HeaderBar as a child widget (not subclass)
        self._headerbar = Adw.HeaderBar()
        self._headerbar.add_css_class('flat')
        self.append(self._headerbar)

        # Title widget
        self._title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER)
        self._title_label = Gtk.Label(label="Orion")
        self._title_label.add_css_class('title')
        self._subtitle_label = Gtk.Label(label="")
        self._subtitle_label.add_css_class('subtitle')
        self._subtitle_label.set_visible(False)
        self._title_box.append(self._title_label)
        self._title_box.append(self._subtitle_label)
        self._headerbar.set_title_widget(self._title_box)

        # Left side: Menu button
        self._build_menu()

        # Left: Open file button
        open_btn = Gtk.Button(icon_name='document-open-symbolic', tooltip_text='Open File (Ctrl+O)')
        open_btn.connect('clicked', lambda b: self.window.open_file_dialog())
        self._headerbar.pack_start(open_btn)

        # Right side: Search
        self._search_btn = Gtk.ToggleButton(icon_name='system-search-symbolic', tooltip_text='Search')
        self._search_btn.connect('toggled', self._on_search_toggled)
        self._headerbar.pack_end(self._search_btn)

        # Search bar (hidden by default)
        self._search_entry = Gtk.SearchEntry()
        self._search_entry.set_placeholder_text("Search library...")
        self._search_entry.connect('search-changed', self._on_search_changed)
        self._search_entry.set_visible(False)
        self._search_entry.set_hexpand(False)
        self._search_entry.set_size_request(250, -1)
        self._headerbar.pack_end(self._search_entry)

        # Fullscreen button
        fs_btn = Gtk.Button(icon_name='view-fullscreen-symbolic', tooltip_text='Fullscreen (F)')
        fs_btn.connect('clicked', lambda b: self.window.toggle_fullscreen())
        self._headerbar.pack_end(fs_btn)

    def _build_menu(self):
        """Build primary menu."""
        menu = Gio.Menu()

        # File section
        file_section = Gio.Menu()
        file_section.append("Open File", "app.open-file")
        file_section.append("Open Folder", "app.open-folder")
        file_section.append("Open Network Stream", "app.open-stream")
        menu.append_section(None, file_section)

        # Tools section
        tools_section = Gio.Menu()
        tools_section.append("Equalizer", "app.equalizer")
        tools_section.append("Subtitle Settings", "app.subtitle-settings")
        tools_section.append("Statistics", "app.statistics")
        menu.append_section("Tools", tools_section)

        # View section
        view_section = Gio.Menu()
        view_section.append("Mini Player", "app.mini-player")
        view_section.append("Always on Top", "app.always-on-top")
        menu.append_section("View", view_section)

        # Settings and about
        settings_section = Gio.Menu()
        settings_section.append("Preferences", "app.preferences")
        settings_section.append("Keyboard Shortcuts", "app.shortcuts")
        settings_section.append("About Orion", "app.about")
        menu.append_section(None, settings_section)

        menu_btn = Gtk.MenuButton(
            icon_name='open-menu-symbolic',
            menu_model=menu,
            tooltip_text='Main Menu',
            primary=True,
        )
        self._headerbar.pack_end(menu_btn)

    def _on_search_toggled(self, button):
        self._search_entry.set_visible(button.get_active())
        if button.get_active():
            self._search_entry.grab_focus()

    def _on_search_changed(self, entry):
        query = entry.get_text()
        if query:
            results = self.window.library.search(query)
            # Show results as toast for now
            count = len([r for r in results if r.media_type == 'video'])
            if count > 0:
                self.window.show_toast(f"Found {count} videos matching '{query}'")

    def set_now_playing(self, title):
        """Update the now playing subtitle."""
        self._subtitle_label.set_label(title)
        self._subtitle_label.set_visible(bool(title))
