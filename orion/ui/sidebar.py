"""Sidebar with library, playlists, and navigation."""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, GLib, Pango
from pathlib import Path


class Sidebar(Gtk.Box):
    """Left sidebar with navigation and library view."""

    def __init__(self, window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window = window
        self.set_size_request(260, -1)
        self.add_css_class('sidebar')
        self.set_overflow(Gtk.Overflow.HIDDEN)

        # Navigation stack
        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)

        # Switcher
        self._switcher = Gtk.StackSwitcher()
        self._switcher.set_stack(self._stack)
        self._switcher.set_halign(Gtk.Align.CENTER)
        self._switcher.set_margin_top(8)
        self._switcher.set_margin_bottom(8)
        self.append(self._switcher)

        # Separator
        self.append(Gtk.Separator())

        # Stack pages
        self._build_library_page()
        self._build_playlist_page()
        self._build_favorites_page()

        self._stack.set_vexpand(True)
        self.append(self._stack)

    def _build_library_page(self):
        """Build library navigation page."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Scrolled container
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        list_box.add_css_class('navigation-sidebar')
        list_box.connect('row-activated', self._on_library_row_activated)
        self._library_list = list_box

        # Library categories
        categories = [
            ('folder-videos-symbolic', 'Movies', 'movies'),
            ('folder-music-symbolic', 'Music', 'music'),
            ('folder-pictures-symbolic', 'Photos', 'photos'),
            ('document-open-recent-symbolic', 'Recently Added', 'recent'),
            ('media-playback-start-symbolic', 'Most Played', 'most_played'),
            ('media-view-subtitles-symbolic', 'Continue Watching', 'continue'),
            ('folder-symbolic', 'Folders', 'folders'),
        ]

        for icon, label, category in categories:
            row = Adw.ActionRow(title=label)
            row.add_prefix(Gtk.Image.new_from_icon_name(icon))
            row.set_activatable(True)
            row._category = category
            list_box.append(row)

        scrolled.set_child(list_box)
        page.append(scrolled)

        # Add folder button
        add_folder_btn = Gtk.Button(label="Add Folder")
        add_folder_btn.set_margin_start(12)
        add_folder_btn.set_margin_end(12)
        add_folder_btn.set_margin_bottom(8)
        add_folder_btn.set_margin_top(8)
        add_folder_btn.add_css_class('flat')
        add_folder_btn.set_icon_name('folder-new-symbolic')
        add_folder_btn.connect('clicked', lambda b: self.window.open_folder_dialog())
        page.append(add_folder_btn)

        self._stack.add_titled(page, 'library', 'Library')

    def _build_playlist_page(self):
        """Build playlist management page."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        toolbar.set_margin_start(8)
        toolbar.set_margin_end(8)
        toolbar.set_margin_top(8)
        toolbar.set_margin_bottom(4)

        new_btn = Gtk.Button(icon_name='list-add-symbolic', tooltip_text='New Playlist')
        new_btn.add_css_class('flat')
        new_btn.connect('clicked', self._on_new_playlist)
        toolbar.append(new_btn)

        toolbar.append(Gtk.Box(hexpand=True))  # Spacer

        page.append(toolbar)
        page.append(Gtk.Separator())

        # Playlists list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._playlist_list = Gtk.ListBox()
        self._playlist_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._playlist_list.add_css_class('navigation-sidebar')
        self._playlist_list.connect('row-activated', self._on_playlist_row_activated)

        # Built-in playlists
        queue_row = Adw.ActionRow(title="Queue")
        queue_row.add_prefix(Gtk.Image.new_from_icon_name('view-list-symbolic'))
        queue_row._playlist_name = '__queue__'
        self._playlist_list.append(queue_row)

        recent_row = Adw.ActionRow(title="Recently Played")
        recent_row.add_prefix(Gtk.Image.new_from_icon_name('document-open-recent-symbolic'))
        recent_row._playlist_name = '__recent__'
        self._playlist_list.append(recent_row)

        scrolled.set_child(self._playlist_list)
        page.append(scrolled)

        self._stack.add_titled(page, 'playlists', 'Playlists')

    def _build_favorites_page(self):
        """Build favorites page."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._favorites_list = Gtk.ListBox()
        self._favorites_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._favorites_list.add_css_class('navigation-sidebar')
        self._favorites_list.set_placeholder(
            Gtk.Label(label="No favorites yet", margin_top=20, opacity=0.5)
        )
        self._favorites_list.connect('row-activated', self._on_favorite_row_activated)

        scrolled.set_child(self._favorites_list)
        page.append(scrolled)

        self._stack.add_titled(page, 'favorites', 'Favorites')

    # Content display area
    def _show_content_list(self, items, title=""):
        """Show items in a content popup/page."""
        # For now, create playlist from items and set active
        from orion.core.playlist import Playlist, PlaylistItem

        playlist = Playlist(name=title)
        for item in items:
            pi = PlaylistItem(uri=item.uri, title=item.title, artist=item.artist)
            playlist.add_item(pi)

        self.window.playlist_manager.playlists[title] = playlist
        self.window.playlist_manager.active_playlist_name = title
        self._refresh_playlist_list()

    # Signal handlers
    def _on_library_row_activated(self, list_box, row):
        category = getattr(row, '_category', '')
        library = self.window.library

        if category == 'movies':
            items = library.get_movies()
            self._show_content_list(items, "Movies")
        elif category == 'music':
            items = library.get_music()
            self._show_content_list(items, "Music")
        elif category == 'photos':
            items = library.get_photos()
            self._show_content_list(items, "Photos")
        elif category == 'recent':
            items = library.get_recently_added()
            self._show_content_list(items, "Recently Added")
        elif category == 'most_played':
            items = library.get_most_played()
            self._show_content_list(items, "Most Played")
        elif category == 'continue':
            items = library.get_continue_watching()
            self._show_content_list(items, "Continue Watching")
        elif category == 'folders':
            self.window.open_folder_dialog()

    def _on_playlist_row_activated(self, list_box, row):
        name = getattr(row, '_playlist_name', '')
        if name == '__queue__':
            pass  # Show queue
        elif name == '__recent__':
            pass  # Show recently played
        elif name in self.window.playlist_manager.playlists:
            self.window.playlist_manager.active_playlist_name = name

    def _on_favorite_row_activated(self, list_box, row):
        uri = getattr(row, '_uri', '')
        if uri:
            self.window.play_file(uri)

    def _on_new_playlist(self, button):
        """Create a new playlist with dialog."""
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="New Playlist",
            body="Enter a name for the new playlist:",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("create", "Create")
        dialog.set_response_appearance("create", Adw.ResponseAppearance.SUGGESTED)

        entry = Gtk.Entry()
        entry.set_placeholder_text("Playlist name")
        entry.set_margin_start(24)
        entry.set_margin_end(24)
        dialog.set_extra_child(entry)

        dialog.connect('response', self._on_new_playlist_response, entry)
        dialog.present()

    def _on_new_playlist_response(self, dialog, response, entry):
        if response == "create":
            name = entry.get_text().strip()
            if name:
                self.window.playlist_manager.create_playlist(name)
                self._refresh_playlist_list()
                self.window.show_toast(f"Created playlist: {name}")
        dialog.close()

    def _refresh_playlist_list(self):
        """Refresh the playlist list."""
        # Remove custom playlists (keep built-in ones at top)
        child = self._playlist_list.get_first_child()
        built_in = 0
        while child:
            next_child = child.get_next_sibling()
            if built_in >= 2:  # Skip queue and recent
                self._playlist_list.remove(child)
            built_in += 1
            child = next_child

        # Add user playlists
        for name in self.window.playlist_manager.playlists:
            row = Adw.ActionRow(title=name)
            row.add_prefix(Gtk.Image.new_from_icon_name('playlist-symbolic'))
            row._playlist_name = name
            # Add delete button
            del_btn = Gtk.Button(icon_name='user-trash-symbolic')
            del_btn.add_css_class('flat')
            del_btn.set_valign(Gtk.Align.CENTER)
            del_btn.connect('clicked', self._on_delete_playlist, name)
            row.add_suffix(del_btn)
            self._playlist_list.append(row)

    def _on_delete_playlist(self, button, name):
        self.window.playlist_manager.delete_playlist(name)
        self._refresh_playlist_list()
        self.window.show_toast(f"Deleted playlist: {name}")

    # Public methods
    def refresh_library(self):
        """Refresh library view after scan."""
        self._refresh_playlist_list()
        self._refresh_favorites()

    def _refresh_favorites(self):
        """Refresh favorites list."""
        # Clear existing
        child = self._favorites_list.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self._favorites_list.remove(child)
            child = next_child

        # Add favorites
        for item in self.window.library.get_favorites():
            row = Adw.ActionRow(title=item.title, subtitle=item.artist or '')
            row.add_prefix(Gtk.Image.new_from_icon_name('starred-symbolic'))
            row._uri = item.uri
            row.set_activatable(True)
            self._favorites_list.append(row)

    def show_search_results(self, results):
        """Display search results."""
        self._stack.set_visible_child_name('library')
        # Temporarily show results in library list
        self.window.show_toast(f"Found {len(results)} results")

    def show_default_view(self):
        """Return to default view."""
        pass
