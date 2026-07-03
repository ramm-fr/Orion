# Publishing Orion to Flathub

## Prerequisites

1. Install Flatpak and flatpak-builder:
```bash
sudo apt install flatpak flatpak-builder
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
```

2. Install the GNOME SDK:
```bash
flatpak install flathub org.gnome.Platform//46 org.gnome.Sdk//46
```

## Build locally (test)

```bash
cd ~/Documents/Orion
flatpak-builder --force-clean build-dir flatpak/com.orion.player.yml
```

## Install locally for testing

```bash
flatpak-builder --user --install --force-clean build-dir flatpak/com.orion.player.yml
flatpak run com.orion.player
```

## Publish to Flathub

### Step 1: Push to GitHub

```bash
cd ~/Documents/Orion
git init
git add .
git commit -m "Orion Video Player v2.0.0"
git remote add origin https://github.com/YOUR_USERNAME/orion.git
git push -u origin main
```

### Step 2: Add screenshots

Create a `screenshots/` folder in your repo and add:
- `player.png` — app playing a video
- `home.png` — home screen
- `browse.png` — browse popup
- `stats.png` — statistics window

### Step 3: Fork Flathub repo

1. Go to https://github.com/flathub/flathub
2. Click "New App" or create a new repository named `com.orion.player`
3. Fork it

### Step 4: Create the Flathub manifest

In your fork, create `com.orion.player.yml` with the content from `flatpak/com.orion.player.yml`, 
but change the source to point to your GitHub release:

```yaml
sources:
  - type: archive
    url: https://github.com/YOUR_USERNAME/orion/archive/refs/tags/v2.0.0.tar.gz
    sha256: YOUR_SHA256_HASH
```

### Step 5: Submit PR

1. Push to your fork
2. Open a Pull Request to https://github.com/flathub/flathub
3. Flathub team will review and merge

## Requirements for Flathub acceptance

- ✅ Valid AppStream metainfo (com.orion.player.metainfo.xml)
- ✅ Desktop file with proper categories
- ✅ SVG icon at proper path
- ✅ GPL-3.0 license
- ⬜ Screenshots (need to add real screenshots to GitHub)
- ⬜ GitHub repository (need to push code)

## Quick local test without Flatpak

```bash
cd ~/Documents/Orion
python3 main.py
```
