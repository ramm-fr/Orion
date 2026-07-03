"""Library manager for organizing media collections."""

import json
import os
from pathlib import Path
from gi.repository import GObject, GLib
import time


MEDIA_EXTENSIONS = {
    'video': {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v',
              '.mpg', '.mpeg', '.3gp', '.ogv', '.ts', '.vob', '.3g2', '.asf',
              '.avci', '.avchd', '.bik', '.dat', '.divx', '.drc', '.f4v',
              '.gxf', '.h261', '.h263', '.h264', '.h265', '.hevc', '.ifo',
              '.m2p', '.m2ts', '.m2v', '.mts', '.mxf', '.nsv', '.ogm', '.qt',
              '.rm', '.rmvb', '.roq', '.svi', '.tod', '.tp', '.mpe', '.mpv',
              '.amv', '.dv', '.evo', '.fli', '.flc', '.gifv', '.ivf', '.lrv',
              '.mjpeg', '.mjpg', '.mod', '.nut', '.ogx', '.pva', '.r3d',
              '.rpl', '.smk', '.vc1', '.viv', '.vp6', '.vp7', '.vp8', '.vp9',
              '.wtv', '.xesc', '.xvid', '.yuv', '.nut'},
    'audio': {'.mp3', '.flac', '.ogg', '.wav', '.aac', '.wma', '.m4a', '.opus',
              '.ape', '.alac'},
    'image': {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.tiff'},
}


class MediaItem:
    """Represents a media file in the library."""

    def __init__(self, path, media_type='video'):
        self.path = path
        self.uri = f'file://{path}'
        self.filename = os.path.basename(path)
        self.title = Path(path).stem
        self.media_type = media_type
        self.size = 0
        self.duration = 0
        self.artist = ''
        self.album = ''
        self.genre = ''
        self.year = ''
        self.play_count = 0
        self.last_played = None
        self.last_position = 0
        self.date_added = time.time()
        self.favorite = False
        self.collection = ''
        self.rating = 0

        try:
            self.size = os.path.getsize(path)
        except OSError:
            pass

    def to_dict(self):
        return {
            'path': self.path,
            'media_type': self.media_type,
            'title': self.title,
            'duration': self.duration,
            'artist': self.artist,
            'album': self.album,
            'genre': self.genre,
            'year': self.year,
            'play_count': self.play_count,
            'last_played': self.last_played,
            'last_position': self.last_position,
            'date_added': self.date_added,
            'favorite': self.favorite,
            'collection': self.collection,
            'rating': self.rating,
        }

    @classmethod
    def from_dict(cls, data):
        item = cls(data['path'], data.get('media_type', 'video'))
        item.title = data.get('title', item.title)
        item.duration = data.get('duration', 0)
        item.artist = data.get('artist', '')
        item.album = data.get('album', '')
        item.genre = data.get('genre', '')
        item.year = data.get('year', '')
        item.play_count = data.get('play_count', 0)
        item.last_played = data.get('last_played')
        item.last_position = data.get('last_position', 0)
        item.date_added = data.get('date_added', time.time())
        item.favorite = data.get('favorite', False)
        item.collection = data.get('collection', '')
        item.rating = data.get('rating', 0)
        return item


class Library(GObject.Object):
    """Media library with scanning, categorization, and smart views."""

    __gsignals__ = {
        'scan-started': (GObject.SignalFlags.RUN_LAST, None, ()),
        'scan-progress': (GObject.SignalFlags.RUN_LAST, None, (int, int)),
        'scan-complete': (GObject.SignalFlags.RUN_LAST, None, ()),
        'items-changed': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self):
        super().__init__()
        self._data_dir = Path.home() / '.local' / 'share' / 'orion'
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._library_file = self._data_dir / 'library.json'

        self.items = []
        self.folders = []
        self.collections = {}
        self._scan_folders = [
            str(Path.home() / 'Videos'),
            str(Path.home() / 'Downloads'),
            str(Path.home() / 'Documents'),
            str(Path.home() / 'Desktop'),
            str(Path.home() / 'Music'),
        ]
        self.load()

    def add_folder(self, folder_path):
        """Add a folder to scan."""
        if folder_path not in self._scan_folders:
            self._scan_folders.append(folder_path)
            self.scan_folder(folder_path)

    def remove_folder(self, folder_path):
        """Remove a folder from library."""
        if folder_path in self._scan_folders:
            self._scan_folders.remove(folder_path)
            self.items = [i for i in self.items if not i.path.startswith(folder_path)]
            self.emit('items-changed')

    def scan_all(self):
        """Scan all registered folders."""
        self.emit('scan-started')
        for folder in self._scan_folders:
            self.scan_folder(folder)
        self.emit('scan-complete')
        self.save()

    def scan_folder(self, folder_path):
        """Scan a folder for media files."""
        if not os.path.isdir(folder_path):
            return

        existing_paths = {item.path for item in self.items}
        all_extensions = set()
        for exts in MEDIA_EXTENSIONS.values():
            all_extensions.update(exts)

        new_items = []
        for root, dirs, files in os.walk(folder_path):
            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                if ext in all_extensions:
                    filepath = os.path.join(root, filename)
                    if filepath not in existing_paths:
                        media_type = 'video'
                        for mt, exts in MEDIA_EXTENSIONS.items():
                            if ext in exts:
                                media_type = mt
                                break
                        item = MediaItem(filepath, media_type)
                        new_items.append(item)

        self.items.extend(new_items)
        self.emit('items-changed')

    # Filtered views
    def get_movies(self):
        return [i for i in self.items if i.media_type == 'video']

    def get_music(self):
        return [i for i in self.items if i.media_type == 'audio']

    def get_photos(self):
        return [i for i in self.items if i.media_type == 'image']

    def get_recently_added(self, count=20):
        return sorted(self.items, key=lambda x: x.date_added, reverse=True)[:count]

    def get_most_played(self, count=20):
        return sorted(self.items, key=lambda x: x.play_count, reverse=True)[:count]

    def get_continue_watching(self):
        """Items with saved position but not completed."""
        return [i for i in self.items if i.last_position > 0 and i.media_type == 'video']

    def get_favorites(self):
        return [i for i in self.items if i.favorite]

    def get_by_genre(self, genre):
        return [i for i in self.items if i.genre.lower() == genre.lower()]

    def get_by_artist(self, artist):
        return [i for i in self.items if i.artist.lower() == artist.lower()]

    def get_by_year(self, year):
        return [i for i in self.items if i.year == year]

    def get_collections(self):
        collections = {}
        for item in self.items:
            if item.collection:
                if item.collection not in collections:
                    collections[item.collection] = []
                collections[item.collection].append(item)
        return collections

    # Search
    def search(self, query):
        """Search library by title, artist, album, genre."""
        query = query.lower()
        return [
            item for item in self.items
            if query in item.title.lower()
            or query in item.artist.lower()
            or query in item.album.lower()
            or query in item.genre.lower()
            or query in item.filename.lower()
        ]

    # Item operations
    def update_play_info(self, path, position=0):
        """Update play count and position for an item."""
        for item in self.items:
            if item.path == path:
                item.play_count += 1
                item.last_played = time.time()
                item.last_position = position
                break
        self.save()

    def set_favorite(self, path, favorite=True):
        for item in self.items:
            if item.path == path:
                item.favorite = favorite
                break
        self.save()

    def delete_item(self, path):
        self.items = [i for i in self.items if i.path != path]
        self.emit('items-changed')
        self.save()

    def get_storage_usage(self):
        """Get total storage used by library items."""
        total = sum(item.size for item in self.items)
        return total

    def get_statistics(self):
        """Get library statistics."""
        return {
            'total_items': len(self.items),
            'videos': len(self.get_movies()),
            'audio': len(self.get_music()),
            'photos': len(self.get_photos()),
            'total_size': self.get_storage_usage(),
            'total_play_count': sum(i.play_count for i in self.items),
        }

    # Persistence
    def save(self):
        data = {
            'items': [item.to_dict() for item in self.items],
            'folders': self._scan_folders,
        }
        try:
            with open(self._library_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def load(self):
        if self._library_file.exists():
            try:
                with open(self._library_file, 'r') as f:
                    data = json.load(f)
                self.items = [MediaItem.from_dict(d) for d in data.get('items', [])]
                self._scan_folders = data.get('folders', self._scan_folders)
            except Exception:
                pass
