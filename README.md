# 🎬 Orion Video Player

A powerful, modern video player for Linux with GNOME/Adwaita-style design.

## Features

### Playback Controls
- Play, Pause, Stop, Next, Previous
- Fast Forward / Rewind (10s / 30s)
- Seek bar with time display
- Playback speed (0.25x - 4.0x)
- Repeat (None / One / All) and Shuffle
- AB Repeat, Frame-by-frame stepping
- Skip Intro / Credits, Auto Resume

### Audio Controls
- Volume slider with mute toggle
- 10-band Equalizer with presets (Rock, Pop, Jazz, Classical, etc.)
- Bass Boost, Treble, Loudness
- Surround Sound, Normalize Volume
- Audio delay, Playback speed, Multiple audio track selection

### Video Controls
- Brightness, Contrast, Saturation, Hue adjustment
- Video filters (B&W, Vintage, Sepia, Cinematic, Warm, Cool)
- Deinterlace, Aspect ratio control
- Rotate, Flip, Zoom, Crop, Pan

### Subtitles
- Load external subtitle files (.srt, .ass, .vtt)
- Subtitle delay adjustment
- Customizable font, size, color, background
- Outline, shadow, position controls

### Library & Playlists
- Automatic media scanning (Videos, Music, Downloads)
- Categories: Movies, Music, Photos
- Smart views: Recently Added, Most Played, Continue Watching
- Create, edit, delete, rename playlists
- Favorites, Queue, Recently Played

### Streaming
- HTTP/HTTPS, RTSP, HLS, FTP streams
- IPTV M3U playlist support
- Network buffering controls

### Interface
- GNOME/Adwaita native design
- Fullscreen with auto-hiding controls
- Mini Player mode
- Keyboard shortcuts for all actions
- Drag & drop file support
- Dark/Light/System theme

### Screenshots
- Take high-resolution screenshots
- Configurable save folder and format
- Clipboard copy support

### Statistics
- Watch time and listen time tracking
- Most played items
- Play history
- Storage usage

## Requirements

- Python 3.10+
- GTK 4
- libadwaita 1.x
- GStreamer 1.20+ with plugins (base, good, bad, ugly, libav)

## Installation

```bash
# Install dependencies (Debian/Ubuntu)
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 \
    gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav gstreamer1.0-gtk4

# Run
python3 main.py
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Space | Play/Pause |
| S | Stop |
| F | Fullscreen |
| M | Mute |
| ↑/↓ | Volume |
| ←/→ | Seek ±10s |
| [/] | Seek ±30s |
| N | Next |
| P | Previous |
| . | Frame step |
| Ctrl+O | Open file |
| Ctrl+L | Open stream |
| Escape | Exit fullscreen |

## License

GPL-3.0
