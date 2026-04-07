import sys

def check_dependencies():
    """Check if required dependencies are installed and provide installation help if not."""
    missing = []
    try:
        import mutagen
    except ImportError:
        missing.append('mutagen')
    try:
        import tqdm
    except ImportError:
        missing.append('tqdm')
    
    if missing:
        print(f"Error: Missing required dependencies: {', '.join(missing)}")
        print("Install them with: pip install " + ' '.join(missing))
        sys.exit(1)


check_dependencies()

import argparse
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from mutagen import File
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.id3 import ID3NoHeaderError
from mutagen.mp4 import MP4
import tqdm

SUPPORTED_EXTENSIONS = ['.mp3', '.flac', '.wav', '.m4a', '.ogg']

def sanitize_filename(name):
    """Normalize text so it can safely be used in filenames."""
    if not name:
        return 'Unknown'

    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, ' ', str(name))
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    return sanitized if sanitized else 'Unknown'


def normalize_track_raw(track_raw):
    """Convert track metadata into a zero-padded track number."""
    if track_raw is None:
        return '00'
    if isinstance(track_raw, (list, tuple)):
        track_raw = track_raw[0] if track_raw else None
    track_text = str(track_raw or '').strip()
    if '/' in track_text:
        track_text = track_text.split('/')[0].strip()
    match = re.search(r'\d+', track_text)
    return match.group(0).zfill(2) if match else '00'


def _get_first_tag(tags, keys, default='Unknown'):
    if not tags:
        return default
    for key in keys:
        value = tags.get(key)
        if not value:
            continue
        if isinstance(value, (list, tuple)):
            value = value[0]
        if isinstance(value, bytes):
            try:
                value = value.decode('utf-8')
            except UnicodeDecodeError:
                value = value.decode('latin-1', errors='ignore')
        value = str(value).strip()
        if value:
            return value
    return default


def extract_audio_tags(filepath):
    """Read metadata from common music file formats."""
    try:
        lower = filepath.lower()

        if lower.endswith(('.m4a', '.mp4')):
            audio = MP4(filepath)
            return {
                'artist': _get_first_tag(audio.tags, ['\xa9ART', 'aART', 'artist', '©ART']),
                'album': _get_first_tag(audio.tags, ['\xa9alb', '©alb', 'album', 'ALBUM']),
                'title': _get_first_tag(audio.tags, ['\xa9nam', '©nam', 'title', 'TITLE']),
                'tracknumber': _get_first_tag(audio.tags, ['trkn', 'tracknumber', 'TRCK'], '0')
            }

        if lower.endswith('.flac'):
            audio = FLAC(filepath)
            return {
                'artist': _get_first_tag(audio.tags, ['artist', 'ARTIST']),
                'album': _get_first_tag(audio.tags, ['album', 'ALBUM']),
                'title': _get_first_tag(audio.tags, ['title', 'TITLE']),
                'tracknumber': _get_first_tag(audio.tags, ['tracknumber', 'TRACKNUMBER'], '0')
            }

        if lower.endswith('.mp3'):
            try:
                audio = EasyID3(filepath)
                return {
                    'artist': _get_first_tag(audio, ['artist', 'ARTIST', '©ART', 'aART', 'TPE1', 'TPE2']),
                    'album': _get_first_tag(audio, ['album', 'ALBUM', '©alb', '\xa9alb', 'TALB']),
                    'title': _get_first_tag(audio, ['title', 'TITLE', '©nam', '\xa9nam', 'TIT2']),
                    'tracknumber': _get_first_tag(audio, ['tracknumber', 'TRACKNUMBER', 'trkn', 'TRCK'], '0')
                }
            except ID3NoHeaderError:
                audio = File(filepath)
        else:
            audio = File(filepath)

        if audio is None or audio.tags is None:
            return None

        tags = audio.tags
        return {
            'artist': _get_first_tag(tags, ['artist', 'ARTIST', '©ART', 'aART', 'TPE1', 'TPE2']),
            'album': _get_first_tag(tags, ['album', 'ALBUM', '©alb', '\xa9alb', 'TALB']),
            'title': _get_first_tag(tags, ['title', 'TITLE', '©nam', '\xa9nam', 'TIT2']),
            'tracknumber': _get_first_tag(tags, ['tracknumber', 'TRACKNUMBER', 'trkn', 'TRCK'], '0')
        }
    except Exception as exc:
        print(f"Error reading tags for {filepath}: {exc}")
        return None


def infer_missing_metadata(file_path, artist, album, title):
    """Infer missing metadata values from the file path."""
    if not title or title == 'Unknown':
        title = sanitize_filename(file_path.stem)

    if not album or album == 'Unknown':
        album = sanitize_filename(file_path.parent.name)
        if album == 'Unknown' and file_path.parent.parent:
            album = sanitize_filename(file_path.parent.parent.name)

    if not artist or artist == 'Unknown':
        if file_path.parent and file_path.parent.parent:
            artist = sanitize_filename(file_path.parent.parent.name)
        if not artist or artist == 'Unknown':
            artist = 'Unknown Artist'

    return artist or 'Unknown Artist', album or 'Unknown Album', title or 'Unknown'


def make_unique_path(dest_path):
    """Return a non-conflicting destination path by appending a suffix."""
    if not dest_path.exists():
        return dest_path

    folder = dest_path.parent
    stem = dest_path.stem
    suffix = dest_path.suffix
    counter = 1

    while True:
        candidate = folder / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def preserve_timestamps(src_path, dst_path):
    """Keep the original file timestamps after moving."""
    try:
        stat = src_path.stat()
        os.utime(dst_path, (stat.st_atime, stat.st_mtime))
    except Exception:
        pass


def write_normalized_tags(filepath, artist, album, title, tracknumber):
    """Optionally normalize metadata tags inside the audio file."""
    try:
        lower = filepath.lower()
        if lower.endswith('.mp3'):
            try:
                audio = EasyID3(filepath)
            except ID3NoHeaderError:
                audio = File(filepath, easy=True)
                if audio is None:
                    return
                audio.add_tags()
                audio = EasyID3(filepath)
            audio['artist'] = artist
            audio['album'] = album
            audio['title'] = title
            audio['tracknumber'] = tracknumber
            audio.save()

        elif lower.endswith('.flac'):
            audio = FLAC(filepath)
            audio['artist'] = [artist]
            audio['album'] = [album]
            audio['title'] = [title]
            audio['tracknumber'] = [tracknumber]
            audio.save()

        elif lower.endswith(('.m4a', '.mp4')):
            audio = MP4(filepath)
            audio['\xa9ART'] = [artist]
            audio['\xa9alb'] = [album]
            audio['\xa9nam'] = [title]
            try:
                audio['trkn'] = [(int(tracknumber), 0)]
            except ValueError:
                audio['trkn'] = [(0, 0)]
            audio.save()
    except Exception as exc:
        print(f"Warning: could not write tags for {filepath}: {exc}")


def log_message(log_file, message):
    try:
        with open(log_file, 'a', encoding='utf-8') as log_handle:
            log_handle.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} - {message}\n")
    except Exception:
        pass


def organize_music(source_folder, recursive=False, dry_run=True, log_file=None, preserve_time=True, normalize_tags=False):
    source_path = Path(source_folder).expanduser().resolve()

    if not source_path.exists() or not source_path.is_dir():
        print(f"Error: folder '{source_folder}' does not exist or is not a directory.")
        return

    if recursive:
        files_to_process = [f for f in source_path.rglob('*') if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS]
    else:
        files_to_process = [f for f in source_path.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS]

    files_to_process.sort()
    print(f"Found {len(files_to_process)} audio file(s) to process.")
    if dry_run and files_to_process:
        print("Files found:")
        for file_path in files_to_process:
            print(f"  - {file_path.name}")
        print()

    if log_file:
        log_path = Path(log_file).expanduser().resolve()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_message(log_path, f"Starting organize_music on {source_path} (recursive={recursive}, dry_run={dry_run})")
    else:
        log_path = None

    processed_count = 0
    skipped_count = 0
    conflicts_count = 0
    planned_moves = []

    for file_path in tqdm.tqdm(files_to_process, desc="Scanning files"):
        tags = extract_audio_tags(str(file_path))
        if tags:
            artist = sanitize_filename(tags.get('artist'))
            album = sanitize_filename(tags.get('album'))
            title = sanitize_filename(tags.get('title'))
            track = normalize_track_raw(tags.get('tracknumber'))
        else:
            artist, album, title = infer_missing_metadata(file_path, '', '', '')
            track = '00'
            print(f"⚠️  No tags found for {file_path.name}; using filename/path inference.")
            if log_path:
                log_message(log_path, f"No tags for {file_path}; inferred artist={artist}, album={album}, title={title}")

        dest_dir = source_path / artist / album
        desired_name = f"{track} - {title}{file_path.suffix}"
        dest_path = dest_dir / desired_name
        final_dest = make_unique_path(dest_path)

        if final_dest != dest_path:
            conflicts_count += 1
            print(f"⚠️  Name conflict for '{dest_path.name}'. Using '{final_dest.name}' instead.")
            if log_path:
                log_message(log_path, f"Conflict: {dest_path} exists; using {final_dest}")

        planned_moves.append((file_path, final_dest, artist, album, title, track))

    print(f"Planning {len(planned_moves)} move(s) with {conflicts_count} conflict(s).\n")

    for source_path_value, dest_path, artist, album, title, track in tqdm.tqdm(planned_moves, desc="Moving files" if not dry_run else "Planning moves"):
        if dry_run:
            print(f"📂 WOULD MOVE: {source_path_value.name}")
            print(f"   TAGS: artist={artist}, album={album}, title={title}, track={track}")
            print(f"   TO:   {dest_path}\n")
            processed_count += 1
            continue

        try:
            if normalize_tags:
                write_normalized_tags(str(source_path_value), artist, album, title, track)

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source_path_value), str(dest_path))
            if preserve_time:
                preserve_timestamps(source_path_value, dest_path)
            print(f"✅ Moved: {source_path_value.name} -> {dest_path}")
            if log_path:
                log_message(log_path, f"Moved: {source_path_value} -> {dest_path}")
            processed_count += 1
        except Exception as exc:
            print(f"❌ Failed to move {source_path_value.name}: {exc}")
            skipped_count += 1
            if log_path:
                log_message(log_path, f"Failed: {source_path_value} -> {dest_path}: {exc}")

    print("\n" + "=" * 40)
    if dry_run:
        print("DRY RUN COMPLETE. No files were moved.")
        print(f"Prepared to move {processed_count} file(s). Skipped {skipped_count} actual operations.")
        print("Use --no-dry-run to execute the moves.")
    else:
        print(f"COMPLETE! Moved {processed_count} files. Skipped {skipped_count} errors.")
        if log_path:
            log_message(log_path, f"Complete: moved {processed_count}, skipped {skipped_count}")


def parse_args():
    parser = argparse.ArgumentParser(description='Organize music files by artist and album.')
    parser.add_argument('source', nargs='?', default='.', help='Folder containing audio files')
    parser.add_argument('--recursive', action='store_true', help='Search subfolders recursively')
    parser.add_argument('--dry-run', '--dry_run', dest='dry_run', action='store_true', default=True, help='Preview moves without moving files')
    parser.add_argument('--no-dry-run', '--no_dry_run', dest='dry_run', action='store_false', help='Actually move files instead of previewing')
    parser.add_argument('--wait', action='store_true', help='Wait for Enter before exiting')
    parser.add_argument('--log-file', default='organize_music.log', help='Path to a log file')
    parser.add_argument('--no-preserve-time', dest='preserve_time', action='store_false', help='Do not preserve original timestamps')
    parser.add_argument('--normalize-tags', action='store_true', help='Normalize and rewrite metadata tags in supported formats')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    organize_music(
        args.source,
        recursive=args.recursive,
        dry_run=args.dry_run,
        log_file=args.log_file,
        preserve_time=args.preserve_time,
        normalize_tags=args.normalize_tags
    )

    if args.wait and sys.stdin.isatty():
        input('Press Enter to exit...')
