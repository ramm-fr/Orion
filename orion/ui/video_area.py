"""Video display area with overlay controls."""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gst', '1.0')

from gi.repository import Gtk, Adw, Gdk, GLib, Graphene, Pango, Gio


class VideoArea(Gtk.Overlay):
    """Video display widget with click-to-play and overlay support."""

    def __init__(self, player):
        super().__init__()
        self.player = player
        self.set_vexpand(True)
        self.set_hexpand(True)
        self._click_timer = None

        # Video drawing area
        self._video_widget = Gtk.Picture()
        self._video_widget.set_content_fit(Gtk.ContentFit.CONTAIN)
        self._video_widget.add_css_class('video-area')
        self.set_child(self._video_widget)

        # Aspect ratio modes
        self._aspect_modes = [
            ('Default', Gtk.ContentFit.CONTAIN),
            ('Fill', Gtk.ContentFit.COVER),
            ('Stretch', Gtk.ContentFit.FILL),
            ('Fit Width', Gtk.ContentFit.SCALE_DOWN),
        ]
        self._current_aspect = 0

        # Try to get paintable from GTK4 sink
        video_sink = player.get_video_sink()
        if video_sink and hasattr(video_sink, 'get_property'):
            try:
                paintable = video_sink.get_property('paintable')
                if paintable:
                    self._video_widget.set_paintable(paintable)
            except Exception:
                pass

        # Placeholder when no video - Home screen
        self._placeholder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._placeholder.set_halign(Gtk.Align.FILL)
        self._placeholder.set_valign(Gtk.Align.FILL)
        self._placeholder.add_css_class('home-screen')

        # Center content
        center_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        center_box.set_halign(Gtk.Align.CENTER)
        center_box.set_valign(Gtk.Align.CENTER)
        center_box.set_vexpand(True)
        center_box.set_size_request(450, -1)
        self._placeholder.append(center_box)

        # Icon
        icon = Gtk.Image.new_from_icon_name('folder-videos-symbolic')
        icon.set_pixel_size(80)
        icon.set_opacity(0.4)
        center_box.append(icon)

        # Title
        title_label = Gtk.Label(label="Drop a file or enter URL to play")
        title_label.add_css_class('title-3')
        title_label.set_opacity(0.8)
        center_box.append(title_label)

        # Description
        desc_label = Gtk.Label(label="Drag and drop video files here, or paste a stream URL below")
        desc_label.add_css_class('dim-label')
        desc_label.set_wrap(True)
        desc_label.set_justify(Gtk.Justification.CENTER)
        center_box.append(desc_label)

        # URL entry
        url_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        url_box.add_css_class('linked')
        url_box.set_margin_top(8)

        self._url_entry = Gtk.Entry()
        self._url_entry.set_placeholder_text("Enter stream URL or file path...")
        self._url_entry.set_hexpand(True)
        self._url_entry.connect('activate', self._on_url_play)
        url_box.append(self._url_entry)

        play_url_btn = Gtk.Button(label="Play")
        play_url_btn.add_css_class('suggested-action')
        play_url_btn.connect('clicked', self._on_url_play)
        url_box.append(play_url_btn)

        center_box.append(url_box)

        # Action buttons
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        actions_box.set_halign(Gtk.Align.CENTER)
        actions_box.set_margin_top(12)

        open_btn = Gtk.Button(label="Open File")
        open_btn.add_css_class('pill')
        open_btn.connect('clicked', self._on_open_file)
        actions_box.append(open_btn)

        browse_btn = Gtk.Button(label="Browse")
        browse_btn.add_css_class('pill')
        browse_btn.connect('clicked', self._on_open_browse)
        actions_box.append(browse_btn)

        center_box.append(actions_box)

        self.add_overlay(self._placeholder)

        # Drag and drop on placeholder
        drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
        drop_target.connect('drop', self._on_drop)
        drop_target.connect('enter', self._on_drag_enter)
        drop_target.connect('leave', self._on_drag_leave)
        self._placeholder.add_controller(drop_target)

        # Single click gesture handling both single and double click
        click = Gtk.GestureClick()
        click.set_button(1)
        click.connect('released', self._on_click)
        self.add_controller(click)

        # Motion for showing controls
        motion = Gtk.EventControllerMotion()
        motion.connect('enter', self._on_enter)
        motion.connect('motion', self._on_motion)
        motion.connect('leave', self._on_leave)
        self.add_controller(motion)

        # Scroll for volume
        scroll = Gtk.EventControllerScroll(
            flags=Gtk.EventControllerScrollFlags.VERTICAL
        )
        scroll.connect('scroll', self._on_scroll)
        self.add_controller(scroll)

        # Hide placeholder when playing
        player.connect('state-changed', self._on_state_changed)

    def _on_click(self, gesture, n_press, x, y):
        if n_press == 2:
            # Double-click: fullscreen - cancel pending single click
            if self._click_timer:
                GLib.source_remove(self._click_timer)
                self._click_timer = None
            window = self.get_root()
            if window and hasattr(window, 'toggle_fullscreen'):
                window.toggle_fullscreen()
        elif n_press == 1:
            # Single-click: schedule play/pause
            if self._click_timer:
                GLib.source_remove(self._click_timer)
            self._click_timer = GLib.timeout_add(300, self._do_play_pause)

    def _do_play_pause(self):
        self._click_timer = None
        self.player.toggle_play_pause()
        return False

    def _on_enter(self, controller, x, y):
        window = self.get_root()
        if window and hasattr(window, 'show_controls'):
            if not window._controls_visible:
                window.show_controls()

    def _on_motion(self, controller, x, y):
        window = self.get_root()
        if window and hasattr(window, 'show_controls'):
            if not window._controls_visible:
                window.show_controls()

    def _on_leave(self, controller):
        pass

    def _on_scroll(self, controller, dx, dy):
        """Scroll to adjust volume."""
        current = self.player.get_volume()
        new_vol = max(0.0, min(1.5, current - dy * 0.05))
        self.player.set_volume(new_vol)
        return True

    def _on_state_changed(self, player, state):
        from orion.core.player import PlaybackState
        if state == PlaybackState.PLAYING:
            self._placeholder.set_visible(False)
        elif state == PlaybackState.STOPPED:
            self._placeholder.set_visible(True)

    def _on_url_play(self, widget):
        """Play URL from entry."""
        url = self._url_entry.get_text().strip()
        if url:
            window = self.get_root()
            if window:
                window.play_uri(url)

    def _on_open_file(self, button):
        """Open file dialog."""
        window = self.get_root()
        if window:
            window.open_file_dialog()

    def _on_open_browse(self, button):
        """Open browse popup."""
        window = self.get_root()
        if window:
            window.open_browse()

    def _on_drop(self, target, value, x, y):
        """Handle file drop on home screen."""
        if isinstance(value, Gio.File):
            path = value.get_path()
            if path:
                window = self.get_root()
                if window:
                    window.play_file(path)
                return True
        return False

    def _on_drag_enter(self, target, x, y):
        """Visual feedback when dragging over."""
        self._placeholder.add_css_class('drag-hover')
        return Gdk.DragAction.COPY

    def _on_drag_leave(self, target):
        """Remove visual feedback."""
        self._placeholder.remove_css_class('drag-hover')

    def cycle_aspect_ratio(self):
        """Cycle through aspect ratio modes. Returns the current mode name."""
        self._current_aspect = (self._current_aspect + 1) % len(self._aspect_modes)
        name, fit_mode = self._aspect_modes[self._current_aspect]
        self._video_widget.set_content_fit(fit_mode)
        return name

    def get_aspect_ratio_name(self):
        """Get current aspect ratio mode name."""
        return self._aspect_modes[self._current_aspect][0]
