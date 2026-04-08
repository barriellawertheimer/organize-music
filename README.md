# Music Organizer

`organize_music.py` is a Python utility for organizing audio files into a folder structure by artist and album.

## Features

- Reads metadata from MP3, FLAC, M4A/MP4, OGG, WAV, and AAC files
- Organizes files into `Artist/Album/` directories
- Renames files using a normalized track number and title format
- Supports preview mode for reviewing planned file moves
- Shows comprehensive summary before moving files (total files, missing tags, conflicts, destination layout)
- Interactive confirmation required before executing moves (unless skipped with --yes)
- Preserves original file timestamps by default
- Optionally rewrites normalized metadata tags for supported file formats
- Generates an operation log file (unless disabled with --no-log-file)

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
- `--preview`
  - Preview the planned moves without actually moving files
- `--yes`, `--confirm`
  - Skip interactive confirmation and proceed with moves
- `--wait`
  - Wait for Enter before exiting when running interactively
- `--log-file <path>`
  - Write a plain-text log of operations to the specified file
  - Default: `organize_music.log`
- `--no-log-file`
  - Disable logging to file
- `--no-preserve-time`
  - Do not preserve original file timestamps after moving
- `--normalize-tags`
  - Rewrite metadata tags in supported formats after organizing

## How it works

1. The script scans the source directory for supported audio files.
2. For each file, it attempts to read metadata tags for `artist`, `album`, `title`, and `track number`.
3. If tags are missing, the script infers metadata from the file name and folder path.
4. Files are analyzed and a comprehensive summary is displayed showing:
   - Total number of files to process
   - Number of files with missing tags
   - Number of naming conflicts detected
   - Destination folder structure preview
5. In preview mode, the script shows what moves would be made without executing them.
6. In execution mode, the script asks for confirmation before proceeding (unless --yes is used).
7. Files are moved into `Artist/Album/` subfolders and renamed to:
   - `XX - Title.ext`
   - where `XX` is a zero-padded track number.
8. If a destination file name already exists, the script appends a numeric suffix to avoid conflicts.

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
python organize_music.py "D:\Music" --recursive --preview
```

Actually move files after reviewing the preview:

```bash
python organize_music.py "D:\Music" --recursive --preview
# Review the summary, then execute:
python organize_music.py "D:\Music" --recursive --yes
```

Move files directly without confirmation:

```bash
python organize_music.py "D:\Music" --recursive --yes
```

Normalize metadata tags while moving:

```bash
python organize_music.py "D:\Music" --recursive --yes --normalize-tags
```

Write operations to a specific log file:

```bash
python organize_music.py "D:\Music" --recursive --yes --log-file "D:\Music\organize_music.log"
```

Disable logging entirely:

```bash
python organize_music.py "D:\Music" --recursive --yes --no-log-file
```

## Notes

- The default behavior requires confirmation before moving files to prevent accidental operations.
- Use `--preview` to review planned changes before executing them.
- Use `--yes` to skip confirmation when you're confident in the operation.
- Use `--no-log-file` to disable logging if you don't need operation records.
- Back up your music library before running the script on a large collection.

## License

This script is provided as-is without warranty. Use at your own risk.
