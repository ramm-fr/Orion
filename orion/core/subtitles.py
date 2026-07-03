"""Online subtitle search and download using OpenSubtitles."""

import os
import json
import urllib.request
import urllib.parse
import zipfile
import gzip
import tempfile
from pathlib import Path


SUBTITLE_CACHE_DIR = Path.home() / '.local' / 'share' / 'orion' / 'subtitles'


def search_subtitles(query, language='en'):
    """Search for subtitles online using OpenSubtitles REST API."""
    SUBTITLE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Use subdl API (no auth required, simple REST)
    url = f"https://rest.opensubtitles.org/search/query-{urllib.parse.quote(query)}/sublanguageid-{language}"
    headers = {
        'User-Agent': 'Orion Video Player v1.0',
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            results = []
            for item in data[:20]:  # Limit to 20 results
                results.append({
                    'title': item.get('MovieName', ''),
                    'filename': item.get('SubFileName', ''),
                    'language': item.get('LanguageName', ''),
                    'download_url': item.get('SubDownloadLink', ''),
                    'rating': item.get('SubRating', '0'),
                    'year': item.get('MovieYear', ''),
                })
            return results
    except Exception:
        pass

    # Fallback: try subdl.com API
    try:
        url = f"https://api.subdl.com/auto?query={urllib.parse.quote(query)}&language={language}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Orion/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            results = []
            for item in data.get('subtitles', [])[:20]:
                results.append({
                    'title': item.get('release_name', ''),
                    'filename': item.get('name', ''),
                    'language': language,
                    'download_url': item.get('url', ''),
                    'rating': '0',
                    'year': '',
                })
            return results
    except Exception:
        return []


def download_subtitle(download_url, filename=None):
    """Download a subtitle file and return the local path."""
    SUBTITLE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if not download_url:
        return None

    try:
        headers = {'User-Agent': 'Orion Video Player v1.0'}
        req = urllib.request.Request(download_url, headers=headers)

        with urllib.request.urlopen(req, timeout=15) as response:
            content = response.read()
            content_type = response.headers.get('Content-Type', '')

            # Determine filename
            if not filename:
                filename = 'subtitle.srt'

            filepath = SUBTITLE_CACHE_DIR / filename

            # Handle gzipped content
            if download_url.endswith('.gz') or 'gzip' in content_type:
                try:
                    content = gzip.decompress(content)
                except Exception:
                    pass

            # Write subtitle file
            with open(filepath, 'wb') as f:
                f.write(content)

            return str(filepath)
    except Exception:
        return None
