"""Browse popup - shows video folders with ability to create custom folders."""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Pango
import os
import json
from pathlib import Path


DATA_DIR = Path.home() / '.local' / 'share' / 'orion'
FOLDERS_FILE = DATA_DIR / 'video_folders.json'


def _load_folders_data():
    """Load saved folders data."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if FOLDERS_FILE.exists():
        try:
            with open(FOLDERS_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    # Default folders
    return {'Favourites': [], 'Downloads': []}


def _get_downloads_videos():
    """Get video files from ~/Downloads (top level only)."""
    video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm',
                       '.m4v', '.mpg', '.mpeg', '.3gp', '.ogv', '.ts', '.vob',
                       '.3g2', '.asf', '.avci', '.avchd', '.bik', '.dat', '.divx',
                       '.drc', '.f4v', '.gxf', '.h261', '.h263', '.h264', '.h265',
                       '.hevc', '.ifo', '.m2p', '.m2ts', '.m2v', '.mts', '.mxf',
                       '.nsv', '.ogm', '.qt', '.rm', '.rmvb', '.roq', '.svi', '.tod',
                       '.tp', '.mpe', '.mpv', '.amv', '.dv', '.evo', '.fli', '.flc',
                       '.gifv', '.ivf', '.lrv', '.mjpeg', '.mjpg', '.mod', '.nut',
                       '.ogx', '.pva', '.r3d', '.rpl', '.smk', '.vc1', '.viv',
                       '.vp6', '.vp7', '.vp8', '.vp9', '.wtv', '.xesc', '.xvid', '.yuv'}
    downloads_dir = Path.home() / 'Downloads'
    videos = []
    if downloads_dir.exists():
        for entry in os.scandir(str(downloads_dir)):
            if entry.is_file():
                ext = os.path.splitext(entry.name)[1].lower()
                if ext in video_extensions:
                    videos.append(entry.path)
    return videos


def _save_folders_data(data):
    """Save folders data."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(FOLDERS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


class BrowsePopup(Adw.Window):
    """Popup window showing video folders and their contents."""

    def __init__(self, window):
        super().__init__(
            transient_for=window,
            modal=True,
            title="Browse",
            default_width=800,
            default_height=550,
        )
        self.window = window
        self.add_css_class('browse-popup')
        self._folders_data = _load_folders_data()
        self._current_folder = None

        # Main box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_content(main_box)

        # Header bar
        self._header = Adw.HeaderBar()
        self._header.add_css_class('flat')
        main_box.append(self._header)

        # Create folder button
        create_btn = Gtk.Button(icon_name='folder-new-symbolic', tooltip_text='Create Folder')
        create_btn.connect('clicked', self._on_create_folder)
        self._header.pack_end(create_btn)

        # Content stack
        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self._stack.set_vexpand(True)
        main_box.append(self._stack)

        # Page 1: Folder list
        self._build_folders_page()

        # Page 2: Folder contents (videos inside a folder)
        self._build_folder_content_page()

        # Show folders
        self._show_folders()

    def _build_folders_page(self):
        """Build the page showing all folders."""
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._folders_flowbox = Gtk.FlowBox()
        self._folders_flowbox.set_valign(Gtk.Align.START)
        self._folders_flowbox.set_max_children_per_line(4)
        self._folders_flowbox.set_min_children_per_line(2)
        self._folders_flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._folders_flowbox.set_column_spacing(16)
        self._folders_flowbox.set_row_spacing(16)
        self._folders_flowbox.set_margin_start(24)
        self._folders_flowbox.set_margin_end(24)
        self._folders_flowbox.set_margin_top(16)
        self._folders_flowbox.set_margin_bottom(24)
        self._folders_flowbox.set_homogeneous(True)
        scrolled.set_child(self._folders_flowbox)

        self._stack.add_named(scrolled, 'folders')

    def _build_folder_content_page(self):
        """Build the page showing videos inside a folder."""
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Back button row
        back_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        back_box.set_margin_start(16)
        back_box.set_margin_top(8)
        back_box.set_margin_bottom(4)

        back_btn = Gtk.Button(icon_name='go-previous-symbolic', tooltip_text='Back')
        back_btn.add_css_class('flat')
        back_btn.connect('clicked', lambda b: self._show_folders())
        back_box.append(back_btn)

        self._folder_title = Gtk.Label(label="")
        self._folder_title.add_css_class('title-3')
        back_box.append(self._folder_title)

        back_box.append(Gtk.Box(hexpand=True))

        # Add video to folder button
        add_video_btn = Gtk.Button(icon_name='list-add-symbolic', tooltip_text='Add Video')
        add_video_btn.add_css_class('flat')
        add_video_btn.connect('clicked', self._on_add_video_to_folder)
        back_box.append(add_video_btn)

        content_box.append(back_box)
        content_box.append(Gtk.Separator())

        # Videos grid
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._videos_flowbox = Gtk.FlowBox()
        self._videos_flowbox.set_valign(Gtk.Align.START)
        self._videos_flowbox.set_max_children_per_line(5)
        self._videos_flowbox.set_min_children_per_line(2)
        self._videos_flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._videos_flowbox.set_column_spacing(12)
        self._videos_flowbox.set_row_spacing(12)
        self._videos_flowbox.set_margin_start(16)
        self._videos_flowbox.set_margin_end(16)
        self._videos_flowbox.set_margin_top(12)
        self._videos_flowbox.set_margin_bottom(16)
        self._videos_flowbox.set_homogeneous(True)
        scrolled.set_child(self._videos_flowbox)

        content_box.append(scrolled)

        # Empty state
        self._empty_label = Gtk.Label(label="No videos in this folder")
        self._empty_label.set_opacity(0.5)
        self._empty_label.set_vexpand(True)
        self._empty_label.set_valign(Gtk.Align.CENTER)
        self._empty_label.set_visible(False)
        content_box.append(self._empty_label)

        self._stack.add_named(content_box, 'content')

    def _show_folders(self):
        """Show the folders list page."""
        self._current_folder = None
        self.set_title("Browse")
        self._stack.set_visible_child_name('folders')
        self._populate_folders()

    def _populate_folders(self):
        """Populate folders grid."""
        # Clear
        child = self._folders_flowbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self._folders_flowbox.remove(child)
            child = next_child

        # Auto-update Downloads folder with actual downloaded videos
        self._folders_data['Downloads'] = _get_downloads_videos()

        for folder_name in self._folders_data:
            card = self._create_folder_card(folder_name)
            self._folders_flowbox.append(card)

    def _create_folder_card(self, folder_name):
        """Create a folder card matching popover style."""
        card = Gtk.Button()
        card.add_css_class('flat')
        card.add_css_class('folder-card')
        card.connect('clicked', self._on_folder_clicked, folder_name)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_size_request(200, -1)

        # Icon area - rounded rectangle with icon on the left
        icon_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        icon_box.set_size_request(200, 120)
        icon_box.add_css_class('folder-icon-box')

        # Choose icon based on folder name
        if folder_name == 'Downloads':
            icon_name = 'folder-download-symbolic'
        elif folder_name == 'Favourites':
            icon_name = 'starred-symbolic'
        else:
            icon_name = 'folder-videos-symbolic'

        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(48)
        icon.set_margin_start(20)
        icon.set_halign(Gtk.Align.START)
        icon.set_valign(Gtk.Align.CENTER)
        icon.set_vexpand(True)
        icon_box.append(icon)

        box.append(icon_box)

        # Folder name
        name_label = Gtk.Label(label=folder_name)
        name_label.set_halign(Gtk.Align.START)
        name_label.set_margin_start(4)
        name_label.set_ellipsize(Pango.EllipsizeMode.END)
        name_label.set_max_width_chars(20)
        box.append(name_label)

        # Video count
        count = len(self._folders_data.get(folder_name, []))
        count_label = Gtk.Label(label=f"{count} videos")
        count_label.set_halign(Gtk.Align.START)
        count_label.set_margin_start(4)
        count_label.add_css_class('dim-label')
        count_label.add_css_class('caption')
        box.append(count_label)

        card.set_child(box)
        return card

    def _on_folder_clicked(self, button, folder_name):
        """Open a folder to show its videos."""
        self._current_folder = folder_name
        self._folder_title.set_label(folder_name)
        self.set_title(folder_name)
        self._stack.set_visible_child_name('content')
        self._populate_videos(folder_name)

    def _populate_videos(self, folder_name):
        """Populate videos inside a folder."""
        # Clear
        child = self._videos_flowbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self._videos_flowbox.remove(child)
            child = next_child

        videos = self._folders_data.get(folder_name, [])
        # Filter to only existing files
        videos = [v for v in videos if os.path.isfile(v)]

        if not videos:
            self._empty_label.set_visible(True)
            self._videos_flowbox.get_parent().set_visible(False)
            return

        self._empty_label.set_visible(False)
        self._videos_flowbox.get_parent().set_visible(True)

        for video_path in videos:
            card = self._create_video_card(video_path)
            self._videos_flowbox.append(card)

    def _create_video_card(self, video_path):
        """Create a video card."""
        title = Path(video_path).stem
        try:
            size = os.path.getsize(video_path)
        except OSError:
            size = 0

        card = Gtk.Button()
        card.add_css_class('flat')
        card.add_css_class('video-card')
        card.connect('clicked', self._on_video_clicked, video_path)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_size_request(150, -1)

        # Thumbnail
        thumb = Gtk.Box()
        thumb.set_size_request(150, 85)
        thumb.add_css_class('video-thumbnail')

        play_icon = Gtk.Image.new_from_icon_name('media-playback-start-symbolic')
        play_icon.set_pixel_size(28)
        play_icon.set_halign(Gtk.Align.CENTER)
        play_icon.set_valign(Gtk.Align.CENTER)
        play_icon.set_vexpand(True)
        play_icon.set_opacity(0.6)
        thumb.append(play_icon)
        box.append(thumb)

        # Title
        title_label = Gtk.Label(label=title)
        title_label.set_halign(Gtk.Align.START)
        title_label.set_ellipsize(Pango.EllipsizeMode.END)
        title_label.set_max_width_chars(18)
        box.append(title_label)

        # Size
        size_str = self._format_size(size)
        if size_str:
            info_label = Gtk.Label(label=size_str)
            info_label.set_halign(Gtk.Align.START)
            info_label.add_css_class('dim-label')
            info_label.add_css_class('caption')
            box.append(info_label)

        card.set_child(box)
        return card

    def _format_size(self, size_bytes):
        """Format file size."""
        if size_bytes == 0:
            return ""
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        idx = 0
        size = float(size_bytes)
        while size >= 1024 and idx < len(units) - 1:
            size /= 1024
            idx += 1
        return f"{size:.1f} {units[idx]}"

    def _on_video_clicked(self, button, path):
        """Play video and close."""
        self.close()
        self.window.play_file(path)

    def _on_create_folder(self, button):
        """Create a new folder."""
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="New Folder",
            body="Enter a name for the new folder:",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("create", "Create")
        dialog.set_response_appearance("create", Adw.ResponseAppearance.SUGGESTED)

        entry = Gtk.Entry()
        entry.set_placeholder_text("Folder name")
        entry.set_margin_start(24)
        entry.set_margin_end(24)
        dialog.set_extra_child(entry)

        dialog.connect('response', self._on_create_folder_response, entry)
        dialog.present()

    def _on_create_folder_response(self, dialog, response, entry):
        if response == "create":
            name = entry.get_text().strip()
            if name and name not in self._folders_data:
                self._folders_data[name] = []
                _save_folders_data(self._folders_data)
                self._populate_folders()
        dialog.close()

    def _on_add_video_to_folder(self, button):
        """Add a video file to the current folder."""
        if not self._current_folder:
            return

        dialog = Gtk.FileDialog()
        dialog.set_title("Add Video to Folder")

        filters = Gtk.FileFilter()
        filters.set_name("Video Files")
        for ext in ['*.mp4', '*.mkv', '*.avi', '*.mov', '*.wmv', '*.flv', '*.webm', '*.m4v']:
            filters.add_pattern(ext)

        filter_list = Gtk.gio.ListStore.new(Gtk.FileFilter) if hasattr(Gtk, 'gio') else None
        dialog.open(self, None, self._on_add_video_response)

    def _on_add_video_response(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file and self._current_folder:
                path = file.get_path()
                if path and path not in self._folders_data[self._current_folder]:
                    self._folders_data[self._current_folder].append(path)
                    _save_folders_data(self._folders_data)
                    self._populate_videos(self._current_folder)
        except GLib.Error:
            pass

    def add_to_favourites(self, video_path):
        """Add a video to the Favourites folder."""
        if 'Favourites' not in self._folders_data:
            self._folders_data['Favourites'] = []
        if video_path not in self._folders_data['Favourites']:
            self._folders_data['Favourites'].append(video_path)
            _save_folders_data(self._folders_data)
