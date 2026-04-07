# Music Organizer

`organize_music.py` is a Python utility for organizing audio files into a folder structure by artist and album.

## Features

- Reads metadata from MP3, FLAC, M4A/MP4, OGG, WAV, and AAC files
- Organizes files into `Artist/Album/` directories
- Renames files using a normalized track number and title format
- Supports dry-run mode for previewing file moves
- Preserves original file timestamps by default
- Optionally rewrites normalized metadata tags for supported file formats
- Generates an operation log file

## Requirements

- Python 3.7+ (recommended)
- `mutagen` library

Install the dependency with:

```bash
pip install mutagen
```

## Usage

From the script directory, run:

```bash
python organize_music.py [source_folder] [options]
```

If `source_folder` is omitted, the current working directory is used.

### Options

- `--recursive`
  - Search subfolders recursively for audio files
- `--dry-run`
  - Preview the planned moves without actually moving files (default)
- `--no-dry-run`
  - Execute the file moves
- `--wait`
  - Wait for Enter before exiting when running interactively
- `--log-file <path>`
  - Write a plain-text log of operations to the specified file
  - Default: `organize_music.log`
- `--no-preserve-time`
  - Do not preserve original file timestamps after moving
- `--normalize-tags`
  - Rewrite metadata tags in supported formats after organizing

## How it works

1. The script scans the source directory for supported audio files.
2. For each file, it attempts to read metadata tags for `artist`, `album`, `title`, and `track number`.
3. If tags are missing, the script infers metadata from the file name and folder path.
4. Files are moved into `Artist/Album/` subfolders and renamed to:
   - `XX - Title.ext`
   - where `XX` is a zero-padded track number.
5. If a destination file name already exists, the script appends a numeric suffix to avoid conflicts.

## Supported file formats

- `.mp3`
- `.flac`
- `.m4a`
- `.mp4`
- `.ogg`
- `.wav`
- `.aac`

## Metadata handling

- Tag extraction works for common metadata keys and multiple audio container formats.
- If a file has no readable metadata, the script uses:
  - filename stem for title
  - parent folder name for album
  - parent-of-parent folder name for artist
- Invalid filename characters are sanitized and replaced with spaces.

## Examples

Preview changes without moving anything:

```bash
python organize_music.py "d:\Music\jewish_music" --recursive
```

Actually move files and preserve timestamps:

```bash
python organize_music.py "d:\Music\jewish_music" --recursive --no-dry-run
```

Normalize metadata tags while moving:

```bash
python organize_music.py "d:\Music\jewish_music" --recursive --no-dry-run --normalize-tags
```

Write operations to a specific log file:

```bash
python organize_music.py "d:\Music\jewish_music" --recursive --no-dry-run --log-file "d:\Music\jewish_music\organize_music.log"
```

## Notes

- The default behavior is safe because `--dry-run` is enabled by default.
- Use `--no-dry-run` only after verifying the planned changes.
- Back up your music library before running the script on a large collection.

## License

This script is provided as-is without warranty. Use at your own risk.
