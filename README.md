# Apple Playlist Mixer

A user-friendly desktop app for mixing Apple Music playlists with precision and elegance.

## Features

- 🎧 Mix tracks from multiple playlists using weighted interleaving
- 🖥️ GUI (PySide6 / Tkinter) and CLI support
- 🍎 Exports to Apple Music–compatible TSV playlist format
- 🎯 Set maximum tracks per artist, randomize, and filter duplicates
- 📂 Saves as `.csv`, `.txt`, and Apple `.txt` (TSV) format

## Requirements

- Python 3.10+ (ideally 3.13+)
- `pandas`, `chardet`
- Optional: `PySide6` or `tkinter` for GUI support

## Usage

```bash
python apple_playlist_mixer.py       # auto GUI
python apple_playlist_mixer.py --cli # command-line mode
```

## License

MIT
