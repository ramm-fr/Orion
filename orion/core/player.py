"""Core GStreamer-based media player engine."""

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
gi.require_version('GstAudio', '1.0')
gi.require_version('GstPbutils', '1.0')

from gi.repository import Gst, GstVideo, GstAudio, GstPbutils, GLib, GObject
import os
import json
from enum import IntEnum
from pathlib import Path


class RepeatMode(IntEnum):
    NONE = 0
    ONE = 1
    ALL = 2


class PlaybackState(IntEnum):
    STOPPED = 0
    PLAYING = 1
    PAUSED = 2


class Player(GObject.Object):
    """GStreamer playbin-based media player with full control."""

    __gsignals__ = {
        'state-changed': (GObject.SignalFlags.RUN_LAST, None, (int,)),
        'position-changed': (GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_INT64, GObject.TYPE_INT64)),
        'media-info-updated': (GObject.SignalFlags.RUN_LAST, None, ()),
        'eos': (GObject.SignalFlags.RUN_LAST, None, ()),
        'error': (GObject.SignalFlags.RUN_LAST, None, (str,)),
        'volume-changed': (GObject.SignalFlags.RUN_LAST, None, (float,)),
        'audio-tags-changed': (GObject.SignalFlags.RUN_LAST, None, ()),
        'video-tags-changed': (GObject.SignalFlags.RUN_LAST, None, ()),
        'buffering': (GObject.SignalFlags.RUN_LAST, None, (int,)),
    }

    def __init__(self):
        super().__init__()
        Gst.init(None)

        # Use playbin (not playbin3) for full audio/subtitle track support
        self._playbin = Gst.ElementFactory.make('playbin', 'playbin')
        if not self._playbin:
            self._playbin = Gst.ElementFactory.make('playbin3', 'playbin')

        # Audio filters pipeline
        self._audio_bin = self._create_audio_bin()
        self._playbin.set_property('audio-sink', self._audio_bin)

        # Video filters pipeline
        self._video_bin = self._create_video_bin()
        self._playbin.set_property('video-sink', self._video_bin)

        # State
        self._state = PlaybackState.STOPPED
        self._repeat_mode = RepeatMode.NONE
        self._shuffle = False
        self._playback_speed = 1.0
        self._volume = 1.0
        self._muted = False
        self._uri = None
        self._duration = 0
        self._position = 0
        self._subtitle_uri = None
        self._audio_delay = 0
        self._subtitle_delay = 0

        # Video adjustments
        self._brightness = 0.0
        self._contrast = 1.0
        self._saturation = 1.0
        self._hue = 0.0

        # AB repeat
        self._ab_repeat_a = -1
        self._ab_repeat_b = -1

        # Hardware acceleration
        self._hw_accel = True

        # Position update timer
        self._position_timer = None

        # Bus watch
        bus = self._playbin.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self._on_bus_message)

    def _create_audio_bin(self):
        """Create audio processing bin with equalizer."""
        audio_bin = Gst.Bin.new('audio-bin')

        # Elements
        self._equalizer = Gst.ElementFactory.make('equalizer-10bands', 'equalizer')
        self._audio_convert = Gst.ElementFactory.make('audioconvert', 'audio-convert')
        self._audio_resample = Gst.ElementFactory.make('audioresample', 'audio-resample')
        audio_sink = Gst.ElementFactory.make('autoaudiosink', 'audio-sink')

        if not all([self._equalizer, self._audio_convert, self._audio_resample, audio_sink]):
            # Fallback: simple audio sink
            audio_sink = Gst.ElementFactory.make('autoaudiosink', 'audio-sink')
            return audio_sink

        audio_bin.add(self._audio_convert)
        audio_bin.add(self._equalizer)
        audio_bin.add(self._audio_resample)
        audio_bin.add(audio_sink)

        self._audio_convert.link(self._equalizer)
        self._equalizer.link(self._audio_resample)
        self._audio_resample.link(audio_sink)

        # Ghost pad
        pad = self._audio_convert.get_static_pad('sink')
        ghost_pad = Gst.GhostPad.new('sink', pad)
        audio_bin.add_pad(ghost_pad)

        return audio_bin

    def _create_video_bin(self):
        """Create video processing bin with filters."""
        video_bin = Gst.Bin.new('video-bin')

        self._video_convert = Gst.ElementFactory.make('videoconvert', 'video-convert')
        self._video_balance = Gst.ElementFactory.make('videobalance', 'video-balance')
        self._video_convert2 = Gst.ElementFactory.make('videoconvert', 'video-convert2')

        # Try GTK4 paintable sink first, then fallback
        video_sink = Gst.ElementFactory.make('gtk4paintablesink', 'video-sink')
        if not video_sink:
            video_sink = Gst.ElementFactory.make('gtksink', 'video-sink')
        if not video_sink:
            video_sink = Gst.ElementFactory.make('autovideosink', 'video-sink')

        self._video_sink = video_sink

        if not all([self._video_convert, self._video_balance, self._video_convert2, video_sink]):
            video_sink = Gst.ElementFactory.make('autovideosink', 'video-sink')
            self._video_sink = video_sink
            return video_sink

        video_bin.add(self._video_convert)
        video_bin.add(self._video_balance)
        video_bin.add(self._video_convert2)
        video_bin.add(video_sink)

        self._video_convert.link(self._video_balance)
        self._video_balance.link(self._video_convert2)
        self._video_convert2.link(video_sink)

        pad = self._video_convert.get_static_pad('sink')
        ghost_pad = Gst.GhostPad.new('sink', pad)
        video_bin.add_pad(ghost_pad)

        return video_bin

    def get_video_sink(self):
        """Return the video sink element for embedding."""
        return self._video_sink

    def set_uri(self, uri):
        """Set media URI."""
        self._uri = uri
        self._playbin.set_state(Gst.State.NULL)
        self._playbin.set_property('uri', uri)

    def play(self):
        """Start playback."""
        if self._uri:
            self._playbin.set_state(Gst.State.PLAYING)
            self._state = PlaybackState.PLAYING
            self._start_position_timer()
            self.emit('state-changed', int(self._state))

    def pause(self):
        """Pause playback."""
        self._playbin.set_state(Gst.State.PAUSED)
        self._state = PlaybackState.PAUSED
        self._stop_position_timer()
        self.emit('state-changed', int(self._state))

    def stop(self):
        """Stop playback."""
        self._playbin.set_state(Gst.State.NULL)
        self._state = PlaybackState.STOPPED
        self._position = 0
        self._stop_position_timer()
        self.emit('state-changed', int(self._state))
        self.emit('position-changed', 0, self._duration)

    def toggle_play_pause(self):
        """Toggle between play and pause."""
        if self._state == PlaybackState.PLAYING:
            self.pause()
        else:
            self.play()

    def seek(self, position_ns):
        """Seek to position in nanoseconds."""
        self._playbin.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            position_ns
        )

    def seek_relative(self, offset_ns):
        """Seek relative to current position."""
        pos = self.get_position()
        new_pos = max(0, min(pos + offset_ns, self._duration))
        self.seek(new_pos)

    def fast_forward(self, seconds=10):
        """Fast forward by seconds."""
        self.seek_relative(seconds * Gst.SECOND)

    def rewind(self, seconds=10):
        """Rewind by seconds."""
        self.seek_relative(-seconds * Gst.SECOND)

    def set_playback_speed(self, speed):
        """Set playback speed (0.25 to 4.0)."""
        self._playback_speed = max(0.25, min(4.0, speed))
        pos = self.get_position()
        if self._playback_speed > 0:
            self._playbin.seek(
                self._playback_speed,
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
                Gst.SeekType.SET, pos,
                Gst.SeekType.NONE, 0
            )

    def get_position(self):
        """Get current position in nanoseconds."""
        success, position = self._playbin.query_position(Gst.Format.TIME)
        if success:
            self._position = position
        return self._position

    def get_duration(self):
        """Get duration in nanoseconds."""
        success, duration = self._playbin.query_duration(Gst.Format.TIME)
        if success:
            self._duration = duration
        return self._duration

    # Volume controls
    def set_volume(self, volume):
        """Set volume (0.0 to 1.5)."""
        self._volume = max(0.0, min(1.5, volume))
        self._playbin.set_property('volume', self._volume)
        self.emit('volume-changed', self._volume)

    def get_volume(self):
        return self._volume

    def set_mute(self, muted):
        self._muted = muted
        self._playbin.set_property('mute', muted)

    def get_mute(self):
        return self._muted

    def toggle_mute(self):
        self.set_mute(not self._muted)

    # Video adjustments
    def set_brightness(self, value):
        """Set brightness (-1.0 to 1.0)."""
        self._brightness = max(-1.0, min(1.0, value))
        if self._video_balance:
            self._video_balance.set_property('brightness', self._brightness)

    def set_contrast(self, value):
        """Set contrast (0.0 to 2.0)."""
        self._contrast = max(0.0, min(2.0, value))
        if self._video_balance:
            self._video_balance.set_property('contrast', self._contrast)

    def set_saturation(self, value):
        """Set saturation (0.0 to 2.0)."""
        self._saturation = max(0.0, min(2.0, value))
        if self._video_balance:
            self._video_balance.set_property('saturation', self._saturation)

    def set_hue(self, value):
        """Set hue (-1.0 to 1.0)."""
        self._hue = max(-1.0, min(1.0, value))
        if self._video_balance:
            self._video_balance.set_property('hue', self._hue)

    # Equalizer
    def set_equalizer_band(self, band, gain):
        """Set equalizer band gain (-24.0 to 12.0 dB)."""
        if self._equalizer and 0 <= band <= 9:
            self._equalizer.set_property(f'band{band}', max(-24.0, min(12.0, gain)))

    def set_equalizer_preset(self, preset_name):
        """Apply equalizer preset."""
        presets = {
            'flat': [0] * 10,
            'rock': [5, 4, 3, 1, -1, -1, 0, 2, 3, 4],
            'pop': [-1, 2, 4, 5, 4, 1, -1, -2, -1, 0],
            'jazz': [3, 2, 1, 2, -1, -1, 0, 1, 2, 3],
            'classical': [4, 3, 2, 1, -1, -1, 0, 2, 3, 4],
            'bass_boost': [7, 6, 5, 3, 1, 0, 0, 0, 0, 0],
            'treble_boost': [0, 0, 0, 0, 0, 1, 3, 5, 6, 7],
            'vocal': [-2, -1, 0, 3, 5, 5, 3, 0, -1, -2],
            'loudness': [5, 4, 2, 0, -2, -2, 0, 2, 4, 5],
        }
        if preset_name in presets:
            for i, gain in enumerate(presets[preset_name]):
                self.set_equalizer_band(i, gain)

    # Subtitle controls
    def set_subtitle_uri(self, uri):
        """Load external subtitle file."""
        self._subtitle_uri = uri
        self._playbin.set_property('suburi', uri)

    def set_subtitle_visible(self, visible):
        """Show or hide subtitles."""
        flags = self._playbin.get_property('flags')
        if visible:
            flags |= 0x00000004  # GST_PLAY_FLAG_TEXT
        else:
            flags &= ~0x00000004
        self._playbin.set_property('flags', flags)

    def set_subtitle_delay(self, delay_ns):
        """Set subtitle delay in nanoseconds."""
        self._subtitle_delay = delay_ns
        # Subtitle offset not directly available on playbin, handle via pad offset

    def set_audio_delay(self, delay_ns):
        """Set audio delay in nanoseconds."""
        self._audio_delay = delay_ns

    # Audio track selection
    def get_audio_track_count(self):
        return self._playbin.get_property('n-audio')

    def set_audio_track(self, index):
        self._playbin.set_property('current-audio', index)

    def get_audio_track_info(self, index):
        """Get language and title info for an audio track."""
        try:
            tag_list = self._playbin.emit('get-audio-tags', index)
            if tag_list:
                success_lang, lang = tag_list.get_string('language-code')
                success_title, title = tag_list.get_string('title')
                lang_name = self._lang_code_to_name(lang) if success_lang else ''
                return {
                    'language': lang_name,
                    'code': lang if success_lang else '',
                    'title': title if success_title else '',
                }
        except Exception:
            pass
        return {'language': '', 'code': '', 'title': ''}

    def _lang_code_to_name(self, code):
        """Convert language code to readable name."""
        lang_map = {
            'hi': 'Hindi', 'te': 'Telugu', 'ta': 'Tamil', 'kn': 'Kannada',
            'ml': 'Malayalam', 'en': 'English', 'es': 'Spanish', 'fr': 'French',
            'de': 'German', 'it': 'Italian', 'pt': 'Portuguese', 'ru': 'Russian',
            'ja': 'Japanese', 'ko': 'Korean', 'zh': 'Chinese', 'ar': 'Arabic',
            'tr': 'Turkish', 'nl': 'Dutch', 'pl': 'Polish', 'sv': 'Swedish',
            'bn': 'Bengali', 'mr': 'Marathi', 'gu': 'Gujarati', 'pa': 'Punjabi',
            'ur': 'Urdu', 'th': 'Thai', 'vi': 'Vietnamese', 'id': 'Indonesian',
        }
        return lang_map.get(code, code.upper() if code else 'Unknown')

    def get_subtitle_track_count(self):
        return self._playbin.get_property('n-text')

    def get_subtitle_track_info(self, index):
        """Get language and title info for a subtitle track."""
        try:
            tag_list = self._playbin.emit('get-text-tags', index)
            if tag_list:
                success_lang, lang = tag_list.get_string('language-code')
                success_title, title = tag_list.get_string('title')
                lang_name = self._lang_code_to_name(lang) if success_lang else ''
                return {
                    'language': lang_name,
                    'code': lang if success_lang else '',
                    'title': title if success_title else '',
                }
        except Exception:
            pass
        return {'language': '', 'code': '', 'title': ''}

    def set_subtitle_track(self, index):
        self._playbin.set_property('current-text', index)

    # Repeat and shuffle
    @property
    def repeat_mode(self):
        return self._repeat_mode

    @repeat_mode.setter
    def repeat_mode(self, mode):
        self._repeat_mode = RepeatMode(mode)

    @property
    def shuffle(self):
        return self._shuffle

    @shuffle.setter
    def shuffle(self, enabled):
        self._shuffle = enabled

    @property
    def playback_speed(self):
        return self._playback_speed

    @property
    def state(self):
        return self._state

    # AB Repeat
    def set_ab_repeat_a(self):
        self._ab_repeat_a = self.get_position()

    def set_ab_repeat_b(self):
        self._ab_repeat_b = self.get_position()

    def clear_ab_repeat(self):
        self._ab_repeat_a = -1
        self._ab_repeat_b = -1

    # Frame stepping
    def step_frame(self):
        """Advance one frame."""
        event = Gst.Event.new_step(Gst.Format.BUFFERS, 1, 1.0, True, False)
        self._playbin.send_event(event)

    # Screenshot
    def take_screenshot(self, filepath=None):
        """Take a screenshot of current frame."""
        if filepath is None:
            screenshots_dir = Path.home() / 'Pictures' / 'Orion Screenshots'
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            import time
            filepath = str(screenshots_dir / f'screenshot_{int(time.time())}.png')

        sample = self._playbin.get_property('sample')
        if sample:
            buf = sample.get_buffer()
            caps = sample.get_caps()
            structure = caps.get_structure(0)
            width = structure.get_value('width')
            height = structure.get_value('height')

            success, mapinfo = buf.map(Gst.MapFlags.READ)
            if success:
                try:
                    from PIL import Image
                    img = Image.frombytes('RGBA', (width, height), mapinfo.data)
                    img.save(filepath)
                    return filepath
                except ImportError:
                    pass
                finally:
                    buf.unmap(mapinfo)
        return None

    # Internal
    def _start_position_timer(self):
        if self._position_timer is None:
            self._position_timer = GLib.timeout_add(500, self._update_position)

    def _stop_position_timer(self):
        if self._position_timer:
            GLib.source_remove(self._position_timer)
            self._position_timer = None

    def _update_position(self):
        if self._state == PlaybackState.PLAYING:
            pos = self.get_position()
            dur = self.get_duration()
            self.emit('position-changed', pos, dur)

            # AB repeat check
            if self._ab_repeat_a >= 0 and self._ab_repeat_b > self._ab_repeat_a:
                if pos >= self._ab_repeat_b:
                    self.seek(self._ab_repeat_a)
            return True
        return False

    def _on_bus_message(self, bus, message):
        msg_type = message.type

        if msg_type == Gst.MessageType.EOS:
            if self._repeat_mode == RepeatMode.ONE:
                self.seek(0)
                self.play()
            else:
                self.emit('eos')

        elif msg_type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            self.emit('error', f'{err.message}')

        elif msg_type == Gst.MessageType.STATE_CHANGED:
            if message.src == self._playbin:
                old, new, pending = message.parse_state_changed()
                if new == Gst.State.PLAYING:
                    self.get_duration()

        elif msg_type == Gst.MessageType.BUFFERING:
            percent = message.parse_buffering()
            self.emit('buffering', percent)

        elif msg_type == Gst.MessageType.TAG:
            self.emit('audio-tags-changed')

    def cleanup(self):
        """Clean up resources."""
        self._stop_position_timer()
        self._playbin.set_state(Gst.State.NULL)
