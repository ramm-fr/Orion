"""Playlist manager with full CRUD operations."""

import json
import os
import random
from pathlib import Path
from gi.repository import GObject, GLib


class PlaylistItem:
    """A single item in a playlist."""

    def __init__(self, uri, title=None, artist=None, album=None, duration=0, favorite=False):
        self.uri = uri
        self.title = title or Path(uri).stem if uri else "Unknown"
        self.artist = artist or "Unknown Artist"
        self.album = album or "Unknown Album"
        self.duration = duration
        self.favorite = favorite
        self.play_count = 0
        self.last_played = None

    def to_dict(self):
        return {
            'uri': self.uri,
            'title': self.title,
            'artist': self.artist,
            'album': self.album,
            'duration': self.duration,
            'favorite': self.favorite,
            'play_count': self.play_count,
            'last_played': self.last_played,
        }

    @classmethod
    def from_dict(cls, data):
        item = cls(
            uri=data.get('uri', ''),
            title=data.get('title'),
            artist=data.get('artist'),
            album=data.get('album'),
            duration=data.get('duration', 0),
            favorite=data.get('favorite', False),
        )
        item.play_count = data.get('play_count', 0)
        item.last_played = data.get('last_played')
        return item


class Playlist(GObject.Object):
    """A managed playlist."""

    __gsignals__ = {
        'items-changed': (GObject.SignalFlags.RUN_LAST, None, ()),
        'current-changed': (GObject.SignalFlags.RUN_LAST, None, (int,)),
    }

    def __init__(self, name="Untitled Playlist", items=None):
        super().__init__()
        self.name = name
        self.items = items or []
        self._current_index = -1
        self._shuffle_order = []

    @property
    def current_index(self):
        return self._current_index

    @current_index.setter
    def current_index(self, value):
        if 0 <= value < len(self.items):
            self._current_index = value
            self.emit('current-changed', value)

    def add_item(self, item):
        self.items.append(item)
        self.emit('items-changed')

    def remove_item(self, index):
        if 0 <= index < len(self.items):
            self.items.pop(index)
            if self._current_index >= len(self.items):
                self._current_index = len(self.items) - 1
            self.emit('items-changed')

    def move_item(self, from_index, to_index):
        if 0 <= from_index < len(self.items) and 0 <= to_index < len(self.items):
            item = self.items.pop(from_index)
            self.items.insert(to_index, item)
            self.emit('items-changed')

    def get_current(self):
        if 0 <= self._current_index < len(self.items):
            return self.items[self._current_index]
        return None

    def next(self, shuffle=False, repeat_mode=0):
        if not self.items:
            return None

        if shuffle:
            if not self._shuffle_order:
                self._shuffle_order = list(range(len(self.items)))
                random.shuffle(self._shuffle_order)
            idx = self._shuffle_order.pop(0)
            self._current_index = idx
        else:
            self._current_index += 1
            if self._current_index >= len(self.items):
                if repeat_mode == 2:  # REPEAT_ALL
                    self._current_index = 0
                else:
                    self._current_index = len(self.items) - 1
                    return None

        self.emit('current-changed', self._current_index)
        return self.get_current()

    def previous(self):
        if not self.items:
            return None
        self._current_index = max(0, self._current_index - 1)
        self.emit('current-changed', self._current_index)
        return self.get_current()

    def sort_by(self, key='title', reverse=False):
        self.items.sort(key=lambda x: getattr(x, key, ''), reverse=reverse)
        self.emit('items-changed')

    def search(self, query):
        query = query.lower()
        return [
            (i, item) for i, item in enumerate(self.items)
            if query in item.title.lower()
            or query in item.artist.lower()
            or query in item.album.lower()
        ]

    def clear(self):
        self.items.clear()
        self._current_index = -1
        self.emit('items-changed')

    def to_dict(self):
        return {
            'name': self.name,
            'items': [item.to_dict() for item in self.items],
            'current_index': self._current_index,
        }

    @classmethod
    def from_dict(cls, data):
        items = [PlaylistItem.from_dict(d) for d in data.get('items', [])]
        playlist = cls(name=data.get('name', 'Untitled'), items=items)
        playlist._current_index = data.get('current_index', -1)
        return playlist


class PlaylistManager(GObject.Object):
    """Manages multiple playlists and persistence."""

    __gsignals__ = {
        'playlist-added': (GObject.SignalFlags.RUN_LAST, None, (str,)),
        'playlist-removed': (GObject.SignalFlags.RUN_LAST, None, (str,)),
        'playlist-changed': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self):
        super().__init__()
        self._data_dir = Path.home() / '.local' / 'share' / 'orion'
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._playlists_file = self._data_dir / 'playlists.json'

        self.playlists = {}
        self.active_playlist_name = None
        self._queue = Playlist(name="Queue")
        self._recently_played = Playlist(name="Recently Played")
        self._favorites = Playlist(name="Favorites")

        self.load()

    @property
    def active_playlist(self):
        if self.active_playlist_name and self.active_playlist_name in self.playlists:
            return self.playlists[self.active_playlist_name]
        return None

    def create_playlist(self, name):
        if name not in self.playlists:
            self.playlists[name] = Playlist(name=name)
            self.emit('playlist-added', name)
            self.save()
            return self.playlists[name]
        return self.playlists[name]

    def delete_playlist(self, name):
        if name in self.playlists:
            del self.playlists[name]
            if self.active_playlist_name == name:
                self.active_playlist_name = None
            self.emit('playlist-removed', name)
            self.save()

    def rename_playlist(self, old_name, new_name):
        if old_name in self.playlists and new_name not in self.playlists:
            playlist = self.playlists.pop(old_name)
            playlist.name = new_name
            self.playlists[new_name] = playlist
            if self.active_playlist_name == old_name:
                self.active_playlist_name = new_name
            self.save()

    def add_to_favorites(self, item):
        item.favorite = True
        self._favorites.add_item(item)
        self.save()

    def add_to_recently_played(self, item):
        # Keep only last 50
        if len(self._recently_played.items) >= 50:
            self._recently_played.items.pop(0)
        self._recently_played.add_item(item)

    def add_to_queue(self, item):
        self._queue.add_item(item)

    @property
    def queue(self):
        return self._queue

    @property
    def recently_played(self):
        return self._recently_played

    @property
    def favorites(self):
        return self._favorites

    def save(self):
        data = {
            'playlists': {name: pl.to_dict() for name, pl in self.playlists.items()},
            'active': self.active_playlist_name,
            'favorites': self._favorites.to_dict(),
            'recently_played': self._recently_played.to_dict(),
        }
        try:
            with open(self._playlists_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def load(self):
        if self._playlists_file.exists():
            try:
                with open(self._playlists_file, 'r') as f:
                    data = json.load(f)
                for name, pl_data in data.get('playlists', {}).items():
                    self.playlists[name] = Playlist.from_dict(pl_data)
                self.active_playlist_name = data.get('active')
                if 'favorites' in data:
                    self._favorites = Playlist.from_dict(data['favorites'])
                if 'recently_played' in data:
                    self._recently_played = Playlist.from_dict(data['recently_played'])
            except Exception:
                pass
