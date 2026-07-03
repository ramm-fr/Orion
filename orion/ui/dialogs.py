"""Dialog windows for Orion player."""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, GLib, Gdk
from pathlib import Path


class EqualizerDialog(Adw.Window):
    """10-band equalizer with presets."""

    def __init__(self, parent):
        super().__init__(
            transient_for=parent,
            title="Equalizer",
            default_width=600,
            default_height=400,
            modal=True,
        )
        self.parent_window = parent
        self.player = parent.player
        self._sliders = []

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_content(content)

        # Header
        header = Adw.HeaderBar()
        header.add_css_class('flat')
        content.append(header)

        # Main content
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main_box.set_margin_start(24)
        main_box.set_margin_end(24)
        main_box.set_margin_top(16)
        main_box.set_margin_bottom(24)
        content.append(main_box)

        # Preset selector
        preset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        preset_box.set_halign(Gtk.Align.CENTER)
        main_box.append(preset_box)

        preset_label = Gtk.Label(label="Preset:")
        preset_box.append(preset_label)

        self._preset_dropdown = Gtk.DropDown.new_from_strings([
            'Flat', 'Rock', 'Pop', 'Jazz', 'Classical',
            'Bass Boost', 'Treble Boost', 'Vocal', 'Loudness'
        ])
        self._preset_dropdown.connect('notify::selected', self._on_preset_changed)
        preset_box.append(self._preset_dropdown)

        # Reset button
        reset_btn = Gtk.Button(label="Reset")
        reset_btn.add_css_class('flat')
        reset_btn.connect('clicked', self._on_reset)
        preset_box.append(reset_btn)

        # Equalizer sliders
        eq_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        eq_box.set_halign(Gtk.Align.CENTER)
        eq_box.set_vexpand(True)
        main_box.append(eq_box)

        bands = ['29', '59', '119', '237', '474', '947', '1.9k', '3.8k', '7.5k', '15k']
        for i, freq in enumerate(bands):
            band_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            band_box.set_halign(Gtk.Align.CENTER)

            slider = Gtk.Scale(
                orientation=Gtk.Orientation.VERTICAL,
                adjustment=Gtk.Adjustment(value=0, lower=-24, upper=12, step_increment=1)
            )
            slider.set_inverted(True)
            slider.set_size_request(40, 200)
            slider.set_draw_value(False)
            slider.connect('value-changed', self._on_band_changed, i)
            self._sliders.append(slider)
            band_box.append(slider)

            label = Gtk.Label(label=freq)
            label.add_css_class('caption')
            band_box.append(label)

            eq_box.append(band_box)

    def _on_preset_changed(self, dropdown, param):
        presets = ['flat', 'rock', 'pop', 'jazz', 'classical',
                   'bass_boost', 'treble_boost', 'vocal', 'loudness']
        idx = dropdown.get_selected()
        if 0 <= idx < len(presets):
            self.player.set_equalizer_preset(presets[idx])

    def _on_band_changed(self, slider, band):
        gain = slider.get_value()
        self.player.set_equalizer_band(band, gain)

    def _on_reset(self, button):
        self.player.set_equalizer_preset('flat')
        for slider in self._sliders:
            slider.set_value(0)
        self._preset_dropdown.set_selected(0)


class VideoAdjustDialog(Adw.Window):
    """Video brightness, contrast, saturation, hue controls."""

    def __init__(self, parent):
        super().__init__(
            transient_for=parent,
            title="Video Adjustments",
            default_width=400,
            default_height=450,
            modal=True,
        )
        self.parent_window = parent
        self.player = parent.player

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_content(content)

        header = Adw.HeaderBar()
        header.add_css_class('flat')
        content.append(header)

        # Preferences group
        prefs = Adw.PreferencesPage()
        content.append(prefs)

        group = Adw.PreferencesGroup(title="Video Settings")
        prefs.add(group)

        # Brightness
        self._brightness_row = self._create_slider_row(
            "Brightness", -100, 100, 0,
            lambda v: self.player.set_brightness(v / 100.0)
        )
        group.add(self._brightness_row)

        # Contrast
        self._contrast_row = self._create_slider_row(
            "Contrast", 0, 200, 100,
            lambda v: self.player.set_contrast(v / 100.0)
        )
        group.add(self._contrast_row)

        # Saturation
        self._saturation_row = self._create_slider_row(
            "Saturation", 0, 200, 100,
            lambda v: self.player.set_saturation(v / 100.0)
        )
        group.add(self._saturation_row)

        # Hue
        self._hue_row = self._create_slider_row(
            "Hue", -100, 100, 0,
            lambda v: self.player.set_hue(v / 100.0)
        )
        group.add(self._hue_row)

        # Filters group
        filters_group = Adw.PreferencesGroup(title="Video Filters")
        prefs.add(filters_group)

        # Filter presets
        filter_names = ['None', 'Black & White', 'Vintage', 'Sepia', 'Warm', 'Cool', 'Cinematic']
        for name in filter_names:
            row = Adw.ActionRow(title=name)
            row.set_activatable(True)
            row.connect('activated', self._on_filter_selected, name)
            filters_group.add(row)

        # Reset button
        reset_btn = Gtk.Button(label="Reset All")
        reset_btn.add_css_class('destructive-action')
        reset_btn.set_halign(Gtk.Align.CENTER)
        reset_btn.set_margin_top(16)
        reset_btn.set_margin_bottom(16)
        reset_btn.connect('clicked', self._on_reset)
        content.append(reset_btn)

    def _create_slider_row(self, title, lower, upper, default, callback):
        row = Adw.ActionRow(title=title)
        slider = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL,
            adjustment=Gtk.Adjustment(value=default, lower=lower, upper=upper, step_increment=1)
        )
        slider.set_size_request(200, -1)
        slider.set_draw_value(True)
        slider.set_valign(Gtk.Align.CENTER)
        slider.connect('value-changed', lambda s: callback(s.get_value()))
        row.add_suffix(slider)
        row._slider = slider
        return row

    def _on_filter_selected(self, row, name):
        if name == 'Black & White':
            self.player.set_saturation(0.0)
        elif name == 'Warm':
            self.player.set_hue(0.1)
            self.player.set_saturation(1.2)
        elif name == 'Cool':
            self.player.set_hue(-0.1)
            self.player.set_saturation(0.9)
        elif name == 'Cinematic':
            self.player.set_contrast(1.2)
            self.player.set_saturation(0.85)
            self.player.set_brightness(-0.05)
        elif name == 'Sepia':
            self.player.set_saturation(0.3)
            self.player.set_hue(0.2)
        elif name == 'Vintage':
            self.player.set_saturation(0.7)
            self.player.set_contrast(1.1)
            self.player.set_brightness(-0.1)
        else:
            self.player.set_brightness(0)
            self.player.set_contrast(1.0)
            self.player.set_saturation(1.0)
            self.player.set_hue(0)

    def _on_reset(self, button):
        self.player.set_brightness(0)
        self.player.set_contrast(1.0)
        self.player.set_saturation(1.0)
        self.player.set_hue(0)


class SubtitleDialog(Adw.Window):
    """Subtitle configuration dialog."""

    def __init__(self, parent):
        super().__init__(
            transient_for=parent,
            title="Subtitle Settings",
            default_width=450,
            default_height=600,
            modal=True,
        )
        self.parent_window = parent
        self.player = parent.player
        self.settings = parent.settings

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_content(content)

        header = Adw.HeaderBar()
        header.add_css_class('flat')
        content.append(header)

        prefs = Adw.PreferencesPage()
        content.append(prefs)

        # Subtitle controls
        group = Adw.PreferencesGroup(title="Subtitle")
        prefs.add(group)

        # Enable/disable
        enable_row = Adw.SwitchRow(title="Show Subtitles")
        enable_row.set_active(self.settings.get('subtitle_enabled', True))
        enable_row.connect('notify::active', self._on_subtitle_toggled)
        group.add(enable_row)

        # Load subtitle file
        load_row = Adw.ActionRow(title="Load Subtitle File", subtitle="Load .srt, .ass, .vtt files")
        load_row.set_activatable(True)
        load_row.add_suffix(Gtk.Image.new_from_icon_name('document-open-symbolic'))
        load_row.connect('activated', self._on_load_subtitle)
        group.add(load_row)

        # Online subtitle search
        online_group = Adw.PreferencesGroup(title="Search Online")
        prefs.add(online_group)

        # Search entry
        self._search_entry = Adw.EntryRow(title="Movie / TV Show Name")
        online_group.add(self._search_entry)

        # Language selector
        self._lang_row = Adw.ComboRow(title="Language")
        self._lang_row.set_model(Gtk.StringList.new([
            'English', 'Spanish', 'French', 'German', 'Portuguese',
            'Italian', 'Dutch', 'Russian', 'Arabic', 'Hindi',
            'Japanese', 'Korean', 'Chinese', 'Turkish', 'Telugu'
        ]))
        online_group.add(self._lang_row)

        # Search button - wrapped in a box added to the prefs page directly
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        search_box.set_halign(Gtk.Align.CENTER)
        search_box.set_margin_top(8)
        search_box.set_margin_bottom(8)
        search_btn = Gtk.Button(label="Search Subtitles")
        search_btn.add_css_class('suggested-action')
        search_btn.add_css_class('pill')
        search_btn.connect('clicked', self._on_search_online)
        search_box.append(search_btn)

        # Add search button after online_group using a separate group
        search_group = Adw.PreferencesGroup()
        search_group.set_header_suffix(search_box)
        prefs.add(search_group)

        # Results list
        self._results_group = Adw.PreferencesGroup(title="Results")
        self._results_group.set_visible(False)
        prefs.add(self._results_group)

        # Delay
        delay_group = Adw.PreferencesGroup(title="Timing")
        prefs.add(delay_group)

        delay_row = Adw.SpinRow(
            title="Subtitle Delay (ms)",
            adjustment=Gtk.Adjustment(value=0, lower=-5000, upper=5000, step_increment=100)
        )
        delay_row.connect('notify::value', self._on_delay_changed)
        delay_group.add(delay_row)

        # Appearance group
        appear_group = Adw.PreferencesGroup(title="Appearance")
        prefs.add(appear_group)

        # Font size
        self._size_row = Adw.SpinRow(
            title="Font Size",
            adjustment=Gtk.Adjustment(value=self.settings.get('subtitle_size', 24), lower=8, upper=72, step_increment=1)
        )
        appear_group.add(self._size_row)

        # Font
        self._font_row = Adw.ActionRow(title="Font", subtitle=self.settings.get('subtitle_font', 'Sans'))
        self._font_row.set_activatable(True)
        appear_group.add(self._font_row)

        # Color
        color_row = Adw.ActionRow(title="Text Color")
        self._color_btn = Gtk.ColorButton()
        self._color_btn.set_valign(Gtk.Align.CENTER)
        color_row.add_suffix(self._color_btn)
        appear_group.add(color_row)

        # Background
        bg_row = Adw.ActionRow(title="Background Color")
        self._bg_btn = Gtk.ColorButton()
        self._bg_btn.set_valign(Gtk.Align.CENTER)
        bg_row.add_suffix(self._bg_btn)
        appear_group.add(bg_row)

        # Outline
        self._outline_row = Adw.SwitchRow(title="Text Outline")
        self._outline_row.set_active(self.settings.get('subtitle_outline', True))
        appear_group.add(self._outline_row)

        # Position
        self._pos_row = Adw.ComboRow(title="Position")
        self._pos_row.set_model(Gtk.StringList.new(['Bottom', 'Top', 'Center']))
        pos_saved = self.settings.get('subtitle_position', 0)
        if pos_saved is not None and isinstance(pos_saved, int):
            self._pos_row.set_selected(pos_saved)
        appear_group.add(self._pos_row)

        # Save button
        save_btn = Gtk.Button(label="Save Settings")
        save_btn.add_css_class('suggested-action')
        save_btn.add_css_class('pill')
        save_btn.set_halign(Gtk.Align.CENTER)
        save_btn.set_margin_top(16)
        save_btn.set_margin_bottom(16)
        save_btn.connect('clicked', self._on_save_settings)
        content.append(save_btn)

    def _on_subtitle_toggled(self, row, param):
        self.player.set_subtitle_visible(row.get_active())
        self.settings.set('subtitle_enabled', row.get_active())

    def _on_save_settings(self, button):
        """Save all subtitle settings."""
        self.settings.set('subtitle_size', int(self._size_row.get_value()))
        self.settings.set('subtitle_outline', self._outline_row.get_active())
        self.settings.set('subtitle_position', self._pos_row.get_selected())
        self.settings.save()
        self.parent_window.show_toast("Subtitle settings saved")

    def _on_load_subtitle(self, row):
        dialog = Gtk.FileDialog()
        dialog.set_title("Load Subtitle File")

        filter_model = Gio.ListStore.new(Gtk.FileFilter)
        sub_filter = Gtk.FileFilter()
        sub_filter.set_name("Subtitle Files")
        for ext in ['*.srt', '*.ass', '*.ssa', '*.vtt', '*.sub', '*.idx']:
            sub_filter.add_pattern(ext)
        filter_model.append(sub_filter)
        dialog.set_filters(filter_model)

        dialog.open(self.parent_window, None, self._on_subtitle_file_chosen)

    def _on_subtitle_file_chosen(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                path = file.get_path()
                uri = f'file://{path}'
                self.player.set_subtitle_uri(uri)
                self.parent_window.show_toast(f"Loaded subtitles: {Path(path).name}")
        except GLib.Error:
            pass

    def _on_delay_changed(self, row, param):
        delay_ms = row.get_value()
        self.player.set_subtitle_delay(int(delay_ms * 1000000))  # Convert to ns

    def _on_search_online(self, button):
        """Search for subtitles online."""
        query = self._search_entry.get_text().strip()
        if not query:
            self.parent_window.show_toast("Enter a movie or show name to search")
            return

        # Get language code
        lang_codes = ['eng', 'spa', 'fre', 'ger', 'por', 'ita', 'dut', 'rus',
                      'ara', 'hin', 'jpn', 'kor', 'chi', 'tur', 'tel']
        lang_idx = self._lang_row.get_selected()
        lang = lang_codes[lang_idx] if lang_idx < len(lang_codes) else 'eng'

        # Search in background
        import threading
        self.parent_window.show_toast("Searching subtitles...")

        def do_search():
            from orion.core.subtitles import search_subtitles
            results = search_subtitles(query, lang)
            GLib.idle_add(self._show_results, results)

        thread = threading.Thread(target=do_search, daemon=True)
        thread.start()

    def _show_results(self, results):
        """Show search results in the dialog."""
        # Clear old results
        child = self._results_group.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            # Skip the group header
            if hasattr(child, 'get_title'):
                self._results_group.remove(child)
            child = next_child

        if not results:
            self._results_group.set_visible(True)
            no_result = Adw.ActionRow(title="No subtitles found")
            no_result.add_prefix(Gtk.Image.new_from_icon_name('dialog-warning-symbolic'))
            self._results_group.add(no_result)
            return

        self._results_group.set_visible(True)

        for item in results[:10]:
            title = item.get('filename', '') or item.get('title', '')
            subtitle_text = f"{item.get('language', '')} • Rating: {item.get('rating', '0')}"
            if item.get('year'):
                subtitle_text = f"{item['year']} • {subtitle_text}"

            row = Adw.ActionRow(title=title, subtitle=subtitle_text)
            row.set_activatable(True)
            row.add_suffix(Gtk.Image.new_from_icon_name('folder-download-symbolic'))
            row.connect('activated', self._on_download_subtitle, item)
            self._results_group.add(row)

    def _on_download_subtitle(self, row, item):
        """Download and apply a subtitle."""
        import threading

        self.parent_window.show_toast("Downloading subtitle...")

        def do_download():
            from orion.core.subtitles import download_subtitle
            path = download_subtitle(item.get('download_url', ''), item.get('filename', 'subtitle.srt'))
            GLib.idle_add(self._apply_subtitle, path)

        thread = threading.Thread(target=do_download, daemon=True)
        thread.start()

    def _apply_subtitle(self, path):
        """Apply downloaded subtitle."""
        if path:
            uri = f'file://{path}'
            self.player.set_subtitle_uri(uri)
            self.parent_window.show_toast(f"Subtitles loaded: {Path(path).name}")
        else:
            self.parent_window.show_toast("Failed to download subtitle")


class StreamDialog(Adw.Window):
    """Network stream dialog."""

    def __init__(self, parent):
        super().__init__(
            transient_for=parent,
            title="Open Network Stream",
            default_width=550,
            default_height=550,
            modal=True,
        )
        self.parent_window = parent

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_content(content)

        header = Adw.HeaderBar()
        header.add_css_class('flat')
        content.append(header)

        prefs = Adw.PreferencesPage()
        content.append(prefs)

        group = Adw.PreferencesGroup(
            title="Network Stream",
            description="Enter URL to play (HTTP, HTTPS, RTSP, HLS, FTP)"
        )
        prefs.add(group)

        # URL entry
        self._url_entry = Adw.EntryRow(title="Stream URL")
        self._url_entry.set_text("")
        group.add(self._url_entry)

        # Protocol info
        info_group = Adw.PreferencesGroup(title="Supported Protocols")
        prefs.add(info_group)

        protocols = [
            ('HTTP/HTTPS', 'http://, https://'),
            ('RTSP', 'rtsp://'),
            ('HLS', '.m3u8 playlists'),
            ('FTP', 'ftp://'),
            ('IPTV', 'M3U playlist URLs'),
        ]
        for name, desc in protocols:
            row = Adw.ActionRow(title=name, subtitle=desc)
            info_group.add(row)

        # Example streams
        examples_group = Adw.PreferencesGroup(title="Example Streams")
        prefs.add(examples_group)

        example_streams = [
            ('Big Buck Bunny (HLS)', 'https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8'),
        ]

        for name, url in example_streams:
            row = Adw.ActionRow(title=name, subtitle=url)
            row.set_activatable(True)
            row.add_suffix(Gtk.Image.new_from_icon_name('media-playback-start-symbolic'))
            row.connect('activated', self._on_example_clicked, url)
            examples_group.add(row)

        # Play button
        play_btn = Gtk.Button(label="Play Stream")
        play_btn.add_css_class('suggested-action')
        play_btn.set_halign(Gtk.Align.CENTER)
        play_btn.set_margin_top(16)
        play_btn.set_margin_bottom(16)
        play_btn.connect('clicked', self._on_play)
        content.append(play_btn)

    def _on_play(self, button):
        url = self._url_entry.get_text().strip()
        if url:
            self.parent_window.play_uri(url)
            self.close()
        else:
            self.parent_window.show_toast("Please enter a URL")

    def _on_example_clicked(self, row, url):
        """Play an example stream URL."""
        self.parent_window.play_uri(url)
        self.close()


class SettingsDialog(Adw.PreferencesWindow):
    """Application settings dialog."""

    def __init__(self, parent):
        super().__init__(
            transient_for=parent,
            title="Preferences",
            default_width=700,
            default_height=600,
        )
        self.parent_window = parent
        self.settings = parent.settings

        self._build_general_page()
        self._build_playback_page()
        self._build_interface_page()
        self._build_shortcuts_page()
        self._build_privacy_page()

    def _build_general_page(self):
        page = Adw.PreferencesPage(title="General", icon_name="preferences-system-symbolic")
        self.add(page)

        # Language
        lang_group = Adw.PreferencesGroup(title="Language")
        page.add(lang_group)

        lang_row = Adw.ComboRow(title="Interface Language")
        lang_row.set_model(Gtk.StringList.new([
            'English', 'Spanish', 'French', 'German', 'Japanese', 'Chinese', 'Korean'
        ]))
        lang_group.add(lang_row)

        # Startup
        startup_group = Adw.PreferencesGroup(title="Startup")
        page.add(startup_group)

        startup_row = Adw.ComboRow(title="On Startup")
        startup_row.set_model(Gtk.StringList.new(['Restore Last State', 'Empty', 'Show Library']))
        startup_group.add(startup_row)

        # Cache
        cache_group = Adw.PreferencesGroup(title="Cache & Buffer")
        page.add(cache_group)

        cache_row = Adw.SpinRow(
            title="Cache Size (MB)",
            adjustment=Gtk.Adjustment(value=512, lower=64, upper=4096, step_increment=64)
        )
        cache_group.add(cache_row)

        buffer_row = Adw.SpinRow(
            title="Playback Buffer (ms)",
            adjustment=Gtk.Adjustment(value=3000, lower=500, upper=10000, step_increment=500)
        )
        cache_group.add(buffer_row)

        # Updates
        update_group = Adw.PreferencesGroup(title="Updates")
        page.add(update_group)
        auto_update = Adw.SwitchRow(title="Check for Updates Automatically")
        auto_update.set_active(True)
        update_group.add(auto_update)

    def _build_playback_page(self):
        page = Adw.PreferencesPage(title="Playback", icon_name="media-playback-start-symbolic")
        self.add(page)

        # General playback
        group = Adw.PreferencesGroup(title="Playback")
        page.add(group)

        resume_row = Adw.SwitchRow(title="Resume Playback")
        resume_row.set_active(self.settings.get('resume_playback', True))
        group.add(resume_row)

        hw_row = Adw.SwitchRow(title="Hardware Acceleration")
        hw_row.set_active(self.settings.get('hardware_acceleration', True))
        group.add(hw_row)

        # Audio
        audio_group = Adw.PreferencesGroup(title="Audio")
        page.add(audio_group)

        normalize_row = Adw.SwitchRow(title="Normalize Volume")
        normalize_row.set_active(self.settings.get('normalize_volume', False))
        audio_group.add(normalize_row)

        surround_row = Adw.SwitchRow(title="Surround Sound")
        surround_row.set_active(self.settings.get('surround_sound', False))
        audio_group.add(surround_row)

        # Skip controls
        skip_group = Adw.PreferencesGroup(title="Skip Controls")
        page.add(skip_group)

        intro_row = Adw.SpinRow(
            title="Skip Intro Duration (seconds)",
            adjustment=Gtk.Adjustment(value=30, lower=5, upper=120, step_increment=5)
        )
        skip_group.add(intro_row)

        credits_row = Adw.SpinRow(
            title="Skip Credits Duration (seconds)",
            adjustment=Gtk.Adjustment(value=120, lower=30, upper=300, step_increment=10)
        )
        skip_group.add(credits_row)

    def _build_interface_page(self):
        page = Adw.PreferencesPage(title="Interface", icon_name="preferences-desktop-appearance-symbolic")
        self.add(page)

        group = Adw.PreferencesGroup(title="Appearance")
        page.add(group)

        theme_row = Adw.ComboRow(title="Theme")
        theme_row.set_model(Gtk.StringList.new(['System', 'Light', 'Dark']))
        group.add(theme_row)

        cursor_row = Adw.SwitchRow(title="Hide Cursor in Fullscreen")
        cursor_row.set_active(self.settings.get('fullscreen_hide_cursor', True))
        group.add(cursor_row)

        # Screenshot
        ss_group = Adw.PreferencesGroup(title="Screenshots")
        page.add(ss_group)

        folder_row = Adw.ActionRow(
            title="Screenshot Folder",
            subtitle=self.settings.get('screenshot_folder', '~/Pictures/Orion Screenshots')
        )
        folder_row.set_activatable(True)
        ss_group.add(folder_row)

        format_row = Adw.ComboRow(title="Format")
        format_row.set_model(Gtk.StringList.new(['PNG', 'JPEG', 'WebP']))
        ss_group.add(format_row)

    def _build_shortcuts_page(self):
        page = Adw.PreferencesPage(title="Shortcuts", icon_name="preferences-desktop-keyboard-shortcuts-symbolic")
        self.add(page)

        group = Adw.PreferencesGroup(title="Keyboard Shortcuts")
        page.add(group)

        shortcuts = [
            ('Play/Pause', 'Space'),
            ('Stop', 'S'),
            ('Next', 'N'),
            ('Previous', 'P'),
            ('Fullscreen', 'F'),
            ('Mute', 'M'),
            ('Volume Up', '↑'),
            ('Volume Down', '↓'),
            ('Seek Forward', '→'),
            ('Seek Backward', '←'),
            ('Fast Forward', ']'),
            ('Rewind', '['),
            ('Screenshot', 'Print Screen'),
            ('Frame Step', '.'),
        ]

        for action, key in shortcuts:
            row = Adw.ActionRow(title=action)
            label = Gtk.Label(label=key)
            label.add_css_class('dim-label')
            label.set_valign(Gtk.Align.CENTER)
            row.add_suffix(label)
            group.add(row)

    def _build_privacy_page(self):
        page = Adw.PreferencesPage(title="Privacy", icon_name="preferences-system-privacy-symbolic")
        self.add(page)

        group = Adw.PreferencesGroup(title="History & Data")
        page.add(group)

        history_row = Adw.SwitchRow(title="Save Play History")
        history_row.set_active(self.settings.get('save_history', True))
        group.add(history_row)

        position_row = Adw.SwitchRow(title="Save Watch Position")
        position_row.set_active(self.settings.get('save_watch_position', True))
        group.add(position_row)

        clear_row = Adw.ActionRow(title="Clear History", subtitle="Remove all play history")
        clear_row.set_activatable(True)
        clear_row.add_suffix(Gtk.Image.new_from_icon_name('user-trash-symbolic'))
        group.add(clear_row)

        clear_all_row = Adw.ActionRow(title="Clear All Data", subtitle="Reset all settings and data")
        clear_all_row.set_activatable(True)
        clear_all_row.add_css_class('error')
        group.add(clear_all_row)


class StatisticsDialog(Adw.Window):
    """Statistics dashboard with graphs and real-time data."""

    def __init__(self, parent):
        super().__init__(
            transient_for=parent,
            title="Statistics",
            default_width=650,
            default_height=600,
            modal=True,
        )
        self.parent_window = parent
        self.stats = parent.statistics

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_content(content)

        header = Adw.HeaderBar()
        header.add_css_class('flat')

        # Clear history button
        clear_btn = Gtk.Button(icon_name='user-trash-symbolic', tooltip_text='Clear History')
        clear_btn.connect('clicked', self._on_clear)
        header.pack_end(clear_btn)
        content.append(header)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        content.append(scrolled)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main_box.set_margin_start(24)
        main_box.set_margin_end(24)
        main_box.set_margin_top(16)
        main_box.set_margin_bottom(24)
        scrolled.set_child(main_box)

        # Overview cards
        cards_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        cards_box.set_homogeneous(True)
        main_box.append(cards_box)

        watch_time = self.stats.total_watch_time
        listen_time = self.stats.total_listen_time
        total_plays = len(self.stats.history)
        today_stats = self.stats.get_daily_stats()

        cards_box.append(self._create_stat_card("Watch Time", self._format_duration(watch_time), "video-display-symbolic"))
        cards_box.append(self._create_stat_card("Listen Time", self._format_duration(listen_time), "audio-speakers-symbolic"))
        cards_box.append(self._create_stat_card("Total Plays", str(total_plays), "media-playback-start-symbolic"))
        cards_box.append(self._create_stat_card("Today", f"{today_stats['plays']} plays", "document-open-recent-symbolic"))

        # Weekly activity graph
        graph_label = Gtk.Label(label="Weekly Activity")
        graph_label.set_halign(Gtk.Align.START)
        graph_label.add_css_class('heading')
        main_box.append(graph_label)

        self._graph_area = Gtk.DrawingArea()
        self._graph_area.set_size_request(-1, 200)
        self._graph_area.set_draw_func(self._draw_weekly_graph)
        self._graph_area.add_css_class('graph-area')
        main_box.append(self._graph_area)

        # Daily watch time graph
        daily_label = Gtk.Label(label="Daily Watch Time (last 14 days)")
        daily_label.set_halign(Gtk.Align.START)
        daily_label.add_css_class('heading')
        daily_label.set_margin_top(8)
        main_box.append(daily_label)

        self._daily_graph = Gtk.DrawingArea()
        self._daily_graph.set_size_request(-1, 180)
        self._daily_graph.set_draw_func(self._draw_daily_graph)
        self._daily_graph.add_css_class('graph-area')
        main_box.append(self._daily_graph)

        # Most played
        most_played = self.stats.get_most_played(5)
        if most_played:
            mp_label = Gtk.Label(label="Most Played")
            mp_label.set_halign(Gtk.Align.START)
            mp_label.add_css_class('heading')
            mp_label.set_margin_top(8)
            main_box.append(mp_label)

            mp_list = Gtk.ListBox()
            mp_list.set_selection_mode(Gtk.SelectionMode.NONE)
            mp_list.add_css_class('boxed-list')
            main_box.append(mp_list)

            max_count = most_played[0]['count'] if most_played else 1
            for i, item in enumerate(most_played):
                row = Gtk.ListBoxRow()
                row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                row_box.set_margin_top(8)
                row_box.set_margin_bottom(8)
                row_box.set_margin_start(12)
                row_box.set_margin_end(12)

                # Rank
                rank_label = Gtk.Label(label=f"#{i+1}")
                rank_label.set_width_chars(3)
                rank_label.add_css_class('dim-label')
                row_box.append(rank_label)

                # Title and bar
                info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                info_box.set_hexpand(True)

                title_label = Gtk.Label(label=item['title'])
                title_label.set_halign(Gtk.Align.START)
                title_label.set_ellipsize(2)  # END
                info_box.append(title_label)

                # Progress bar showing relative play count
                bar = Gtk.ProgressBar()
                bar.set_fraction(item['count'] / max_count)
                info_box.append(bar)

                row_box.append(info_box)

                # Count
                count_label = Gtk.Label(label=f"{item['count']}×")
                count_label.add_css_class('dim-label')
                row_box.append(count_label)

                row.set_child(row_box)
                mp_list.append(row)

        # Recent history
        history = self.stats.history[:10]
        if history:
            hist_label = Gtk.Label(label="Recent History")
            hist_label.set_halign(Gtk.Align.START)
            hist_label.add_css_class('heading')
            hist_label.set_margin_top(8)
            main_box.append(hist_label)

            hist_list = Gtk.ListBox()
            hist_list.set_selection_mode(Gtk.SelectionMode.NONE)
            hist_list.add_css_class('boxed-list')
            main_box.append(hist_list)

            for entry in history:
                row = Gtk.ListBoxRow()
                row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                row_box.set_margin_top(6)
                row_box.set_margin_bottom(6)
                row_box.set_margin_start(12)
                row_box.set_margin_end(12)

                icon = Gtk.Image.new_from_icon_name(
                    'video-display-symbolic' if entry.get('media_type') == 'video' else 'audio-speakers-symbolic'
                )
                icon.set_opacity(0.6)
                row_box.append(icon)

                title_l = Gtk.Label(label=entry.get('title', 'Unknown'))
                title_l.set_halign(Gtk.Align.START)
                title_l.set_hexpand(True)
                title_l.set_ellipsize(2)
                row_box.append(title_l)

                date_l = Gtk.Label(label=entry.get('date', ''))
                date_l.add_css_class('dim-label')
                date_l.add_css_class('caption')
                row_box.append(date_l)

                row.set_child(row_box)
                hist_list.append(row)

    def _create_stat_card(self, title, value, icon_name):
        """Create a statistics card widget."""
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        card.add_css_class('stat-card')
        card.set_margin_top(8)
        card.set_margin_bottom(8)

        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(24)
        icon.set_opacity(0.6)
        card.append(icon)

        value_label = Gtk.Label(label=value)
        value_label.add_css_class('title-3')
        card.append(value_label)

        title_label = Gtk.Label(label=title)
        title_label.add_css_class('dim-label')
        title_label.add_css_class('caption')
        card.append(title_label)

        return card

    def _draw_weekly_graph(self, area, cr, width, height):
        """Draw weekly activity bar chart."""
        import time as time_mod
        from datetime import datetime, timedelta

        # Get data for last 7 days
        days = []
        values = []
        today = datetime.now()
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            date_str = day.strftime('%Y-%m-%d')
            day_stats = self.stats.get_daily_stats(date_str)
            days.append(day.strftime('%a'))
            values.append(day_stats['plays'])

        max_val = max(values) if values and max(values) > 0 else 1

        # Background
        cr.set_source_rgba(0.15, 0.15, 0.15, 1.0)
        self._rounded_rect(cr, 0, 0, width, height, 12)
        cr.fill()

        # Draw bars
        padding = 40
        bar_width = (width - padding * 2) / len(days) - 8
        bar_spacing = (width - padding * 2) / len(days)

        for i, (day, val) in enumerate(zip(days, values)):
            x = padding + i * bar_spacing + 4
            bar_height = (val / max_val) * (height - 60) if max_val > 0 else 0
            y = height - 30 - bar_height

            # Bar
            cr.set_source_rgba(0.35, 0.55, 0.95, 0.8)
            self._rounded_rect(cr, x, y, bar_width, bar_height, 4)
            cr.fill()

            # Day label
            cr.set_source_rgba(0.7, 0.7, 0.7, 1.0)
            cr.set_font_size(11)
            text_ext = cr.text_extents(day)
            cr.move_to(x + bar_width / 2 - text_ext.width / 2, height - 10)
            cr.show_text(day)

            # Value on top
            if val > 0:
                val_str = str(val)
                cr.set_source_rgba(0.9, 0.9, 0.9, 1.0)
                cr.set_font_size(10)
                text_ext = cr.text_extents(val_str)
                cr.move_to(x + bar_width / 2 - text_ext.width / 2, y - 5)
                cr.show_text(val_str)

    def _draw_daily_graph(self, area, cr, width, height):
        """Draw daily watch time line graph for last 14 days."""
        from datetime import datetime, timedelta

        # Get data for last 14 days
        values = []
        labels = []
        today = datetime.now()
        for i in range(13, -1, -1):
            day = today - timedelta(days=i)
            date_str = day.strftime('%Y-%m-%d')
            day_stats = self.stats.get_daily_stats(date_str)
            values.append(day_stats['watch_time'] / 60.0)  # Convert to minutes
            labels.append(day.strftime('%d'))

        max_val = max(values) if values and max(values) > 0 else 1

        # Background
        cr.set_source_rgba(0.15, 0.15, 0.15, 1.0)
        self._rounded_rect(cr, 0, 0, width, height, 12)
        cr.fill()

        # Draw grid lines
        padding_x = 40
        padding_y = 30
        graph_w = width - padding_x * 2
        graph_h = height - padding_y * 2

        cr.set_source_rgba(0.3, 0.3, 0.3, 0.5)
        cr.set_line_width(0.5)
        for i in range(5):
            y = padding_y + (graph_h / 4) * i
            cr.move_to(padding_x, y)
            cr.line_to(width - padding_x, y)
            cr.stroke()

        # Draw line
        if len(values) > 1:
            cr.set_source_rgba(0.3, 0.8, 0.5, 0.9)
            cr.set_line_width(2.5)

            points = []
            for i, val in enumerate(values):
                x = padding_x + (graph_w / (len(values) - 1)) * i
                y = padding_y + graph_h - (val / max_val * graph_h)
                points.append((x, y))

            cr.move_to(points[0][0], points[0][1])
            for x, y in points[1:]:
                cr.line_to(x, y)
            cr.stroke()

            # Draw dots
            cr.set_source_rgba(0.3, 0.8, 0.5, 1.0)
            for x, y in points:
                cr.arc(x, y, 3, 0, 3.14159 * 2)
                cr.fill()

        # X-axis labels
        cr.set_source_rgba(0.6, 0.6, 0.6, 1.0)
        cr.set_font_size(9)
        for i, label in enumerate(labels):
            if i % 2 == 0:  # Show every other label
                x = padding_x + (graph_w / (len(labels) - 1)) * i
                text_ext = cr.text_extents(label)
                cr.move_to(x - text_ext.width / 2, height - 8)
                cr.show_text(label)

        # Y-axis label
        cr.set_source_rgba(0.5, 0.5, 0.5, 1.0)
        cr.set_font_size(9)
        cr.move_to(5, padding_y + 4)
        cr.show_text(f"{max_val:.0f}m")
        cr.move_to(5, height - padding_y)
        cr.show_text("0m")

    def _rounded_rect(self, cr, x, y, w, h, r):
        """Draw a rounded rectangle path."""
        import math
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()

    def _format_duration(self, seconds):
        hours = int(seconds) // 3600
        minutes = (int(seconds) % 3600) // 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    def _format_size(self, bytes_size):
        if bytes_size > 1024 ** 3:
            return f"{bytes_size / 1024**3:.1f} GB"
        elif bytes_size > 1024 ** 2:
            return f"{bytes_size / 1024**2:.1f} MB"
        elif bytes_size > 1024:
            return f"{bytes_size / 1024:.1f} KB"
        return f"{bytes_size} B"

    def _on_clear(self, button):
        """Clear all history."""
        self.stats.clear_history()
        self.parent_window.show_toast("History cleared")
        self.close()


def AboutDialog(parent):
    """Create and return a custom landscape About dialog."""
    dialog = Adw.Window(
        transient_for=parent,
        title="About Orion",
        default_width=850,
        default_height=500,
        modal=True,
    )

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    dialog.set_content(content)

    header = Adw.HeaderBar()
    header.add_css_class('flat')
    content.append(header)

    # Main horizontal layout
    main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    main_box.set_vexpand(True)
    content.append(main_box)

    # Left side - App info
    left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
    left_box.set_size_request(300, -1)
    left_box.set_halign(Gtk.Align.CENTER)
    left_box.set_valign(Gtk.Align.CENTER)
    left_box.set_margin_start(40)
    left_box.set_margin_end(40)
    main_box.append(left_box)

    # App icon
    icon = Gtk.Image.new_from_icon_name('orion')
    icon.set_pixel_size(96)
    left_box.append(icon)

    # App name
    name_label = Gtk.Label(label="Orion")
    name_label.add_css_class('title-1')
    left_box.append(name_label)

    # Version
    ver_label = Gtk.Label(label="Version 2.0.0")
    ver_label.add_css_class('dim-label')
    left_box.append(ver_label)

    # Description
    desc_label = Gtk.Label(label="A powerful, modern video player\nfor Linux")
    desc_label.set_justify(Gtk.Justification.CENTER)
    desc_label.set_opacity(0.7)
    left_box.append(desc_label)

    # Developer
    dev_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    dev_box.set_margin_top(12)

    dev_label = Gtk.Label(label="Developed by")
    dev_label.add_css_class('dim-label')
    dev_label.add_css_class('caption')
    dev_box.append(dev_label)

    dev_name = Gtk.Label(label="Ram")
    dev_name.add_css_class('heading')
    dev_box.append(dev_name)

    left_box.append(dev_box)

    # Copyright
    copy_label = Gtk.Label(label="© 2025 Ram. All rights reserved.")
    copy_label.add_css_class('dim-label')
    copy_label.add_css_class('caption')
    copy_label.set_margin_top(8)
    left_box.append(copy_label)

    # Separator
    main_box.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

    # Right side - Details (scrollable)
    right_scroll = Gtk.ScrolledWindow()
    right_scroll.set_hexpand(True)
    right_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    main_box.append(right_scroll)

    right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
    right_box.set_margin_start(24)
    right_box.set_margin_end(24)
    right_box.set_margin_top(16)
    right_box.set_margin_bottom(24)
    right_scroll.set_child(right_box)

    # Features section
    features_label = Gtk.Label(label="Features")
    features_label.set_halign(Gtk.Align.START)
    features_label.add_css_class('title-3')
    right_box.append(features_label)

    features = [
        "80+ video format support (MP4, MKV, AVI, MOV, WebM, FLV...)",
        "Stream playback — HLS (.m3u8), RTSP, HTTP/HTTPS",
        "Multi-audio track selection with language detection",
        "Embedded subtitle track switching",
        "Online subtitle search and download",
        "10-band audio equalizer with 9 presets",
        "Video adjustments — brightness, contrast, saturation, hue",
        "Video filters — B&W, Vintage, Sepia, Cinematic, Warm, Cool",
        "Aspect ratio control — Default, Fill, Stretch, Fit",
        "Playback speed — 0.25x to 4.0x",
        "Browse section with custom folders",
        "Drag and drop file support",
        "Statistics dashboard with real-time graphs",
        "Screenshot capture",
        "AB repeat, frame stepping",
        "Hardware acceleration",
        "Keyboard shortcuts",
        "Mini player mode",
    ]

    features_text = Gtk.Label()
    features_text.set_markup("\n".join([f"• {f}" for f in features]))
    features_text.set_halign(Gtk.Align.START)
    features_text.set_wrap(True)
    features_text.set_opacity(0.8)
    right_box.append(features_text)

    # Tech section
    tech_label = Gtk.Label(label="Built With")
    tech_label.set_halign(Gtk.Align.START)
    tech_label.add_css_class('title-3')
    right_box.append(tech_label)

    tech_grid = Gtk.FlowBox()
    tech_grid.set_selection_mode(Gtk.SelectionMode.NONE)
    tech_grid.set_max_children_per_line(4)
    tech_grid.set_min_children_per_line(2)
    tech_grid.set_column_spacing(8)
    tech_grid.set_row_spacing(8)
    right_box.append(tech_grid)

    techs = ["GTK4", "Libadwaita", "GStreamer", "Python", "Cairo"]
    for tech in techs:
        chip = Gtk.Label(label=tech)
        chip.add_css_class('caption')
        chip.set_margin_start(12)
        chip.set_margin_end(12)
        chip.set_margin_top(6)
        chip.set_margin_bottom(6)
        tech_grid.append(chip)

    # Formats section
    formats_label = Gtk.Label(label="Supported Formats")
    formats_label.set_halign(Gtk.Align.START)
    formats_label.add_css_class('title-3')
    right_box.append(formats_label)

    formats_text = Gtk.Label(
        label="MP4, MKV, AVI, MOV, WMV, FLV, WebM, M4V, MPG, MPEG, 3GP, 3G2, "
              "ASF, DIVX, F4V, H264, H265, HEVC, M2TS, MTS, OGV, QT, RM, RMVB, "
              "TS, VOB, AMV, DV, EVO, GIFV, IVF, MJPEG, VP8, VP9, XVID, and more."
    )
    formats_text.set_halign(Gtk.Align.START)
    formats_text.set_wrap(True)
    formats_text.set_opacity(0.7)
    right_box.append(formats_text)

    # License
    license_label = Gtk.Label(label="License")
    license_label.set_halign(Gtk.Align.START)
    license_label.add_css_class('title-3')
    right_box.append(license_label)

    lic_text = Gtk.Label(label="GNU General Public License v3.0")
    lic_text.set_halign(Gtk.Align.START)
    lic_text.set_opacity(0.7)
    right_box.append(lic_text)

    return dialog
