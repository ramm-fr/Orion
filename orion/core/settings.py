"""Application settings and configuration manager."""

import json
from pathlib import Path
from gi.repository import GObject


DEFAULT_SETTINGS = {
    # General
    'language': 'en',
    'theme': 'system',  # system, light, dark
    'startup_mode': 'last_state',  # last_state, empty, library

    # Playback
    'default_volume': 1.0,
    'resume_playback': True,
    'skip_intro_duration': 30,
    'skip_credits_duration': 120,
    'playback_speed': 1.0,
    'hardware_acceleration': True,

    # Video
    'default_aspect_ratio': 'auto',
    'deinterlace': False,
    'brightness': 0.0,
    'contrast': 1.0,
    'saturation': 1.0,
    'hue': 0.0,

    # Audio
    'audio_output': 'auto',
    'normalize_volume': False,
    'equalizer_preset': 'flat',
    'bass_boost': False,
    'surround_sound': False,

    # Subtitles
    'subtitle_enabled': True,
    'subtitle_language': 'en',
    'subtitle_size': 24,
    'subtitle_font': 'Sans',
    'subtitle_color': '#FFFFFF',
    'subtitle_bg_color': '#00000080',
    'subtitle_outline': True,
    'subtitle_position': 'bottom',

    # Interface
    'show_on_top': False,
    'mini_player': False,
    'theatre_mode': False,
    'fullscreen_hide_cursor': True,

    # Cache
    'cache_size_mb': 512,
    'playback_buffer_ms': 3000,

    # Keyboard shortcuts
    'shortcuts': {
        'play_pause': 'space',
        'stop': 's',
        'next': 'n',
        'previous': 'p',
        'fullscreen': 'f',
        'mute': 'm',
        'volume_up': 'Up',
        'volume_down': 'Down',
        'seek_forward': 'Right',
        'seek_backward': 'Left',
        'screenshot': 'Print',
        'fast_forward': 'bracketright',
        'rewind': 'bracketleft',
        'frame_step': 'period',
    },

    # Screenshots
    'screenshot_folder': str(Path.home() / 'Pictures' / 'Orion Screenshots'),
    'screenshot_format': 'png',

    # Privacy
    'save_history': True,
    'save_watch_position': True,

    # Streaming
    'network_buffer_size': 4096,

    # Notifications
    'notifications_enabled': True,
    'notify_on_complete': True,
}


class Settings(GObject.Object):
    """Persistent settings manager."""

    __gsignals__ = {
        'setting-changed': (GObject.SignalFlags.RUN_LAST, None, (str, str)),
    }

    def __init__(self):
        super().__init__()
        self._config_dir = Path.home() / '.config' / 'orion'
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._settings_file = self._config_dir / 'settings.json'
        self._settings = dict(DEFAULT_SETTINGS)
        self.load()

    def get(self, key, default=None):
        """Get a setting value."""
        keys = key.split('.')
        value = self._settings
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def set(self, key, value):
        """Set a setting value."""
        keys = key.split('.')
        target = self._settings
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        self.emit('setting-changed', key, str(value))
        self.save()

    def reset(self, key=None):
        """Reset setting(s) to default."""
        if key:
            keys = key.split('.')
            value = DEFAULT_SETTINGS
            for k in keys:
                value = value.get(k)
            self.set(key, value)
        else:
            self._settings = dict(DEFAULT_SETTINGS)
            self.save()

    def get_shortcut(self, action):
        """Get keyboard shortcut for action."""
        return self._settings.get('shortcuts', {}).get(action, '')

    def set_shortcut(self, action, shortcut):
        """Set keyboard shortcut for action."""
        if 'shortcuts' not in self._settings:
            self._settings['shortcuts'] = {}
        self._settings['shortcuts'][action] = shortcut
        self.save()

    def save(self):
        try:
            with open(self._settings_file, 'w') as f:
                json.dump(self._settings, f, indent=2)
        except Exception:
            pass

    def load(self):
        if self._settings_file.exists():
            try:
                with open(self._settings_file, 'r') as f:
                    loaded = json.load(f)
                self._settings.update(loaded)
            except Exception:
                pass

    @property
    def all_settings(self):
        return dict(self._settings)
