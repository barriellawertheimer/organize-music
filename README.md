# Music Organizer

`organize_music.py` is a Python utility for organizing audio files into a folder structure by artist and album.

## Features

- Reads metadata from MP3, FLAC, M4A/MP4, OGG, WAV, AAC, OPUS, WMA, AIFF, and ALAC files
- Organizes files into `Artist/Album/` directories by default
- Renames files using a normalized track number and title format
- Supports preview mode for reviewing planned file moves without changing files
- Shows a summary with counts for total files, missing tags, duplicate/conflict handling, and destination layout
- Interactive confirmation is required before actual moves unless skipped with `--yes`
- Preserves original file timestamps by default
- Optionally rewrites normalized metadata tags for supported formats
- Writes an operation log file by default, or can disable logging entirely
- Supports copying instead of moving and handling duplicate track conflicts with a `duplicates/` folder

## Requirements

- Python 3.7+
- `mutagen`
- `tqdm`

Install dependencies with:

```bash
pip install mutagen tqdm
```

## Usage

From the script directory, run:

```bash
python organize_music.py [source_folder] [options]
```

If `source_folder` is omitted, the current working directory is used.

### Options

- `--recursive`
  - Search subfolders recursively for supported audio files
- `--preview`
  - Preview planned moves without moving files
- `--yes`, `--confirm`
  - Skip interactive confirmation and proceed with moves
- `--wait`
  - Wait for Enter before exiting when running interactively
- `--log-file <path>`
  - Write a plain-text log of operations to the specified file
  - Default: `organize_music.log`
- `--no-log-file`
  - Disable logging to a file
- `--no-preserve-time`
  - Do not preserve original file timestamps after moving
- `--normalize-tags`
  - Rewrite metadata tags in supported formats after organizing
- `--copy`
  - Copy files instead of moving them
- `--move-duplicates`
  - Move duplicate track files into a `duplicates/` subfolder instead of renaming them
- `--template <template>`
  - Customize the destination path and filename format
  - Default: `{artist}/{album}/{track} - {title}{ext}`
  - Supported placeholders: `{artist}`, `{album}`, `{title}`, `{track}`, `{ext}`, `{date}`, `{year}`

## How it works

1. The script scans the source directory for supported audio files.
2. For each file, it reads metadata tags for `artist`, `album`, `title`, and `track number` when available.
3. If tags are missing or unreadable, it infers metadata from the file path and filename:
   - title from the filename stem
   - album from the parent folder name
   - artist from the parent-of-parent folder name
4. Files are analyzed and a summary is displayed with:
   - Total files processed
   - Number of files with missing tags
   - Duplicate track or name conflicts
   - Destination layout by artist and album
5. In preview mode, the script prints planned move operations only.
6. In execution mode, the script asks for confirmation before moving files unless `--yes` is used.
7. Files are moved or copied to the destination path and renamed using the chosen template.
8. If a destination name already exists, a unique suffix is appended to avoid overwriting.

## Supported file formats

- `.mp3`
- `.flac`
- `.m4a`
- `.mp4`
- `.ogg`
- `.wav`
- `.aac`
- `.opus`
- `.wma`
- `.aiff`
- `.alac`

## Metadata handling

- The script supports common metadata keys across multiple file formats.
- When metadata is missing, it uses path and filename inference to avoid leaving files unorganized.
- Invalid filename characters are sanitized and replaced with spaces.

## Examples

Preview changes without moving anything:

```bash
python organize_music.py "D:\Music" --recursive --preview
```

Move files after reviewing the preview:

```bash
python organize_music.py "D:\Music" --recursive --yes
```

Copy files instead of moving them:

```bash
python organize_music.py "D:\Music" --recursive --copy --yes
```

Normalize metadata tags while organizing:

```bash
python organize_music.py "D:\Music" --recursive --yes --normalize-tags
```

Use a custom filename template:

```bash
python organize_music.py "D:\Music" --recursive --yes --template "{artist}/{album}/{track} - {title}{ext}"
```

Write operations to a specific log file:

```bash
python organize_music.py "D:\Music" --recursive --yes --log-file "D:\Music\organize_music.log"
```

Disable logging entirely:

```bash
python organize_music.py "D:\Music" --recursive --yes --no-log-file
```

Move duplicate track files into `duplicates/`:

```bash
python organize_music.py "D:\Music" --recursive --yes --move-duplicates
```

## Notes

- The default behavior preserves original timestamps after moving files.
- Use `--preview` to verify planned changes before executing them.
- Use `--yes` to skip the confirmation prompt when you are confident in the operation.
- Back up your music library before running the script on a large collection.

## License

This script is provided as-is without warranty. Use at your own risk.
