"""Statistics and history tracking."""

import json
import time
from pathlib import Path
from gi.repository import GObject


class Statistics(GObject.Object):
    """Tracks watch time, history, and usage statistics."""

    __gsignals__ = {
        'history-updated': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self):
        super().__init__()
        self._data_dir = Path.home() / '.local' / 'share' / 'orion'
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._stats_file = self._data_dir / 'statistics.json'

        self._data = {
            'total_watch_time': 0,
            'total_listen_time': 0,
            'history': [],
            'daily_stats': {},
        }
        self.load()

    def record_play(self, uri, title, duration_watched, media_type='video'):
        """Record a play session."""
        entry = {
            'uri': uri,
            'title': title,
            'duration_watched': duration_watched,
            'media_type': media_type,
            'timestamp': time.time(),
            'date': time.strftime('%Y-%m-%d'),
        }
        self._data['history'].append(entry)

        # Keep last 500 history items
        if len(self._data['history']) > 500:
            self._data['history'] = self._data['history'][-500:]

        # Update totals
        if media_type == 'video':
            self._data['total_watch_time'] += duration_watched
        else:
            self._data['total_listen_time'] += duration_watched

        # Daily stats
        date = entry['date']
        if date not in self._data['daily_stats']:
            self._data['daily_stats'][date] = {'watch_time': 0, 'listen_time': 0, 'plays': 0}
        self._data['daily_stats'][date]['plays'] += 1
        if media_type == 'video':
            self._data['daily_stats'][date]['watch_time'] += duration_watched
        else:
            self._data['daily_stats'][date]['listen_time'] += duration_watched

        self.save()
        self.emit('history-updated')

    @property
    def total_watch_time(self):
        return self._data['total_watch_time']

    @property
    def total_listen_time(self):
        return self._data['total_listen_time']

    @property
    def history(self):
        return list(reversed(self._data['history']))

    def get_most_played(self, limit=20):
        """Get most played items."""
        play_counts = {}
        for entry in self._data['history']:
            uri = entry['uri']
            if uri not in play_counts:
                play_counts[uri] = {'title': entry['title'], 'count': 0, 'uri': uri}
            play_counts[uri]['count'] += 1
        sorted_items = sorted(play_counts.values(), key=lambda x: x['count'], reverse=True)
        return sorted_items[:limit]

    def get_last_played(self):
        """Get last played item."""
        if self._data['history']:
            return self._data['history'][-1]
        return None

    def get_daily_stats(self, date=None):
        """Get stats for a specific date."""
        if date is None:
            date = time.strftime('%Y-%m-%d')
        return self._data['daily_stats'].get(date, {'watch_time': 0, 'listen_time': 0, 'plays': 0})

    def get_storage_usage(self):
        """Get stats file size."""
        if self._stats_file.exists():
            return self._stats_file.stat().st_size
        return 0

    def clear_history(self):
        """Clear all history."""
        self._data['history'] = []
        self.save()
        self.emit('history-updated')

    def save(self):
        try:
            with open(self._stats_file, 'w') as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    def load(self):
        if self._stats_file.exists():
            try:
                with open(self._stats_file, 'r') as f:
                    self._data.update(json.load(f))
            except Exception:
                pass
