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
import unicodedata
from datetime import datetime
from pathlib import Path
from mutagen import File
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.id3 import ID3NoHeaderError
from mutagen.mp4 import MP4
import tqdm

SUPPORTED_EXTENSIONS = ['.mp3', '.flac', '.wav', '.m4a', '.ogg', '.aac', '.opus', '.wma', '.aiff', '.alac']

def sanitize_filename(name):
    """Normalize text so it can safely be used in filenames."""
    if not name:
        return 'Unknown'

    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, ' ', str(name))
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    sanitized = unicodedata.normalize('NFC', sanitized)
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
                'albumartist': _get_first_tag(audio.tags, ['aART', 'albumartist']),
                'album': _get_first_tag(audio.tags, ['\xa9alb', '©alb', 'album', 'ALBUM']),
                'title': _get_first_tag(audio.tags, ['\xa9nam', '©nam', 'title', 'TITLE']),
                'tracknumber': _get_first_tag(audio.tags, ['trkn', 'tracknumber', 'TRCK'], '0'),
                'date': _get_first_tag(audio.tags, ['\xa9day', 'date', 'DATE']),
                'year': _get_first_tag(audio.tags, ['\xa9day', 'date', 'DATE'])
            }

        if lower.endswith('.flac'):
            audio = FLAC(filepath)
            return {
                'artist': _get_first_tag(audio.tags, ['artist', 'ARTIST']),
                'albumartist': _get_first_tag(audio.tags, ['albumartist', 'ALBUMARTIST']),
                'album': _get_first_tag(audio.tags, ['album', 'ALBUM']),
                'title': _get_first_tag(audio.tags, ['title', 'TITLE']),
                'tracknumber': _get_first_tag(audio.tags, ['tracknumber', 'TRACKNUMBER'], '0'),
                'date': _get_first_tag(audio.tags, ['date', 'DATE']),
                'year': _get_first_tag(audio.tags, ['date', 'DATE'])
            }

        if lower.endswith('.mp3'):
            try:
                audio = EasyID3(filepath)
                return {
                    'artist': _get_first_tag(audio, ['artist', 'ARTIST', '©ART', 'aART', 'TPE1', 'TPE2']),
                    'albumartist': _get_first_tag(audio, ['albumartist', 'ALBUMARTIST', 'TPE2']),
                    'album': _get_first_tag(audio, ['album', 'ALBUM', '©alb', '\xa9alb', 'TALB']),
                    'title': _get_first_tag(audio, ['title', 'TITLE', '©nam', '\xa9nam', 'TIT2']),
                    'tracknumber': _get_first_tag(audio, ['tracknumber', 'TRACKNUMBER', 'trkn', 'TRCK'], '0'),
                    'date': _get_first_tag(audio, ['date', 'DATE', 'TDRC']),
                    'year': _get_first_tag(audio, ['date', 'DATE', 'TDRC', 'TYER'])
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
            'albumartist': _get_first_tag(tags, ['albumartist', 'ALBUMARTIST', 'TPE2']),
            'album': _get_first_tag(tags, ['album', 'ALBUM', '©alb', '\xa9alb', 'TALB']),
            'title': _get_first_tag(tags, ['title', 'TITLE', '©nam', '\xa9nam', 'TIT2']),
            'tracknumber': _get_first_tag(tags, ['tracknumber', 'TRACKNUMBER', 'trkn', 'TRCK'], '0'),
            'date': _get_first_tag(tags, ['date', 'DATE', 'TDRC']),
            'year': _get_first_tag(tags, ['date', 'DATE', 'TDRC', 'TYER'])
        }
    except Exception as exc:
        print(f"Error reading tags for {filepath}: {exc}")
        return None


def infer_album_from_path(file_path):
    """Infer album from parent folder name."""
    album = sanitize_filename(file_path.parent.name)
    if album == 'Unknown' and file_path.parent.parent:
        album = sanitize_filename(file_path.parent.parent.name)
    return album or 'Unknown Album'


def infer_title_from_filename(filename):
    """Infer title from filename by removing common patterns like track numbers."""
    title = sanitize_filename(filename)
    # Remove leading track numbers like "01 - ", "1. ", etc.
    title = re.sub(r'^\d+\s*[-.]?\s*', '', title)
    # Remove common separators and artist/album prefixes if present, but keep simple
    return title or 'Unknown'


def infer_missing_metadata(file_path, tags):
    """Infer missing metadata values from tags and file path."""
    artist = tags.get('artist') or tags.get('albumartist') or 'Unknown Artist'
    album = tags.get('album') or infer_album_from_path(file_path)
    title = tags.get('title') or infer_title_from_filename(file_path.stem)
    
    return sanitize_filename(artist), sanitize_filename(album), sanitize_filename(title)


def build_dest_path_from_template(source_path, template, metadata, file_path):
    """Build destination path using the template and metadata."""
    # Available variables
    vars = {
        'artist': metadata.get('artist', 'Unknown Artist'),
        'albumartist': metadata.get('albumartist', 'Unknown Artist'),
        'album': metadata.get('album', 'Unknown Album'),
        'title': metadata.get('title', 'Unknown'),
        'track': metadata.get('track', '00'),
        'date': metadata.get('date', ''),
        'year': metadata.get('year', ''),
        'ext': file_path.suffix
    }
    
    # Split template into path parts
    parts = template.split('/')
    dir_parts = parts[:-1]
    filename_template = parts[-1]
    
    # Format directory parts
    formatted_dirs = [part.format(**vars) for part in dir_parts]
    
    # Format filename
    filename = filename_template.format(**vars)
    
    # Build relative path
    rel_path = Path(*formatted_dirs, filename)
    
    return source_path / rel_path


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


def is_same_file(src_path, dst_path):
    """Compare two files by size and content to detect duplicates."""
    try:
        if src_path.stat().st_size != dst_path.stat().st_size:
            return False
        with open(src_path, 'rb') as src_file, open(dst_path, 'rb') as dst_file:
            while True:
                src_chunk = src_file.read(8192)
                dst_chunk = dst_file.read(8192)
                if src_chunk != dst_chunk:
                    return False
                if not src_chunk:
                    return True
    except Exception:
        return False


def collect_existing_tracks(dest_folder):
    """Collect track numbers already present in the destination folder."""
    existing_tracks = set()
    if not dest_folder.is_dir():
        return existing_tracks

    for existing_file in dest_folder.iterdir():
        if existing_file.is_file() and existing_file.suffix.lower() in SUPPORTED_EXTENSIONS:
            tags = extract_audio_tags(str(existing_file))
            if tags:
                existing_tracks.add(normalize_track_raw(tags.get('tracknumber')))
    return existing_tracks


def preserve_timestamps(src_path, dst_path, src_times=None):
    """Keep the original file timestamps after moving."""
    try:
        if src_times is None:
            stat = src_path.stat()
            src_times = (stat.st_atime, stat.st_mtime)
        os.utime(dst_path, src_times)
    except Exception:
        pass


def perform_file_action(operation, src_path, dst_path, preserve_time):
    """Execute a move or copy operation with simple retry logic."""
    attempts = 0
    src_times = None
    if preserve_time and operation == 'move':
        try:
            stat = src_path.stat()
            src_times = (stat.st_atime, stat.st_mtime)
        except Exception:
            src_times = None

    while attempts < 2:
        try:
            if operation == 'copy':
                if preserve_time:
                    shutil.copy2(str(src_path), str(dst_path))
                else:
                    shutil.copy(str(src_path), str(dst_path))
            else:
                shutil.move(str(src_path), str(dst_path))
                if preserve_time and src_times:
                    preserve_timestamps(src_path, dst_path, src_times)
            return True
        except Exception as exc:
            attempts += 1
            if attempts >= 2:
                raise


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


def organize_music(source_folder, recursive=False, preview=False, log_file=None, preserve_time=True, normalize_tags=False, confirm=True, template="{artist}/{album}/{track} - {title}{ext}", copy_mode=False, move_duplicates=False):
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
    if preview and files_to_process:
        print("Files found:")
        for file_path in files_to_process:
            print(f"  - {file_path.name}")
        print()

    if log_file:
        log_path = Path(log_file).expanduser().resolve()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_message(log_path, f"Starting organize_music on {source_path} (recursive={recursive}, preview={preview})")
    else:
        log_path = None

    processed_count = 0
    skipped_count = 0
    conflicts_count = 0
    missing_tags_count = 0
    duplicate_count = 0
    planned_moves = []
    destination_layout = {}  # Track artist/album structure

    for file_path in tqdm.tqdm(files_to_process, desc="Scanning files"):
        tags = extract_audio_tags(str(file_path))
        if tags:
            artist, album, title = infer_missing_metadata(file_path, tags)
            track = normalize_track_raw(tags.get('tracknumber'))
            date = tags.get('date', '')
            year = tags.get('year', '')
        else:
            inferred_tags = {'artist': '', 'album': '', 'title': '', 'albumartist': '', 'date': '', 'year': ''}
            artist, album, title = infer_missing_metadata(file_path, inferred_tags)
            track = '00'
            date = ''
            year = ''
            missing_tags_count += 1
            print(f"⚠️  No tags found for {file_path.name}; using filename/path inference.")
            if log_path:
                log_message(log_path, f"No tags for {file_path}; inferred artist={artist}, album={album}, title={title}")

        metadata = {
            'artist': artist,
            'albumartist': tags.get('albumartist', '') if tags else '',
            'album': album,
            'title': title,
            'track': track,
            'date': date,
            'year': year
        }

        dest_path = build_dest_path_from_template(source_path, template, metadata, file_path)
        album_dest_folder = dest_path.parent
        track_conflict = False
        if album_dest_folder.exists():
            existing_tracks = collect_existing_tracks(album_dest_folder)
            track_conflict = track != '00' and track in existing_tracks

        if dest_path.exists():
            if is_same_file(file_path, dest_path):
                print(f"⚠️  Duplicate file already exists at destination for '{file_path.name}'; skipping.")
                if log_path:
                    log_message(log_path, f"Duplicate skipped: {file_path} -> {dest_path}")
                skipped_count += 1
                continue

            if move_duplicates:
                duplicate_dest = source_path / 'duplicates' / dest_path.relative_to(source_path)
                dest_path = make_unique_path(duplicate_dest)
                duplicate_count += 1
                print(f"⚠️  Destination file exists for '{file_path.name}'. Moving duplicate into duplicates folder.")
                if log_path:
                    log_message(log_path, f"Duplicate moved: {file_path} -> {dest_path}")

        elif track_conflict:
            duplicate_count += 1
            if move_duplicates:
                duplicate_dest = source_path / 'duplicates' / dest_path.relative_to(source_path)
                dest_path = make_unique_path(duplicate_dest)
                print(f"⚠️  Duplicate track number {track} found in album folder. Moving duplicate into duplicates folder.")
                if log_path:
                    log_message(log_path, f"Duplicate track moved: {file_path} -> {dest_path}")
            else:
                dest_path = make_unique_path(dest_path)
                print(f"⚠️  Duplicate track number {track} found in album folder. Creating unique destination for '{file_path.name}'.")
                if log_path:
                    log_message(log_path, f"Duplicate track conflict: {file_path} -> {dest_path}")

        final_dest = make_unique_path(dest_path)

        if final_dest != dest_path:
            conflicts_count += 1
            print(f"⚠️  Name conflict for '{dest_path.name}'. Using '{final_dest.name}' instead.")
            if log_path:
                log_message(log_path, f"Conflict: {dest_path} exists; using {final_dest}")

        planned_moves.append((file_path, final_dest, artist, album, title, track))
        
        # Track destination layout - simplified, as template may vary
        # For now, keep as is, but it might not match if template doesn't use artist/album
        dest_rel = final_dest.relative_to(source_path)
        artist_key = artist
        album_key = album
        if artist_key not in destination_layout:
            destination_layout[artist_key] = {}
        if album_key not in destination_layout[artist_key]:
            destination_layout[artist_key][album_key] = []
        destination_layout[artist_key][album_key].append(dest_rel.name)

    # Show summary
    print(f"\n{'='*50}")
    print("ORGANIZATION SUMMARY")
    print(f"{'='*50}")
    print(f"Template: {template}")
    print(f"Total files: {len(planned_moves)}")
    print(f"Files with missing tags: {missing_tags_count}")
    print(f"Duplicate track conflicts: {duplicate_count}")
    print(f"Conflicts detected: {conflicts_count}")
    print(f"Destination layout:")
    
    for artist, albums in sorted(destination_layout.items()):
        print(f"  {artist}/")
        for album, files in sorted(albums.items()):
            print(f"    {album}/ ({len(files)} files)")
    
    print(f"{'='*50}")
    
    if preview:
        print("PREVIEW MODE - No files will be moved.")
        print("Use --yes to execute moves without confirmation.")
    else:
        if confirm and not input("\nProceed with moving files? (y/N): ").lower().startswith('y'):
            print("Operation cancelled.")
            return
    
    print()

    operation = 'copy' if copy_mode else 'move'
    for source_path_value, dest_path, artist, album, title, track in tqdm.tqdm(planned_moves, desc="Moving files" if not preview else "Planning moves"):
        if preview:
            print(f"📂 WOULD {'COPY' if copy_mode else 'MOVE'}: {source_path_value.name}")
            print(f"   TAGS: artist={artist}, album={album}, title={title}, track={track}")
            print(f"   TO:   {dest_path.relative_to(source_path)}\n")
            processed_count += 1
            continue

        try:
            if normalize_tags:
                write_normalized_tags(str(source_path_value), artist, album, title, track)

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            perform_file_action(operation, source_path_value, dest_path, preserve_time)
            print(f"✅ {'Copied' if copy_mode else 'Moved'}: {source_path_value.name} -> {dest_path.relative_to(source_path)}")
            if log_path:
                log_message(log_path, f"{'Copied' if copy_mode else 'Moved'}: {source_path_value} -> {dest_path.relative_to(source_path)}")
            processed_count += 1
        except Exception as exc:
            print(f"❌ Failed to {'copy' if copy_mode else 'move'} {source_path_value.name}: {exc}")
            skipped_count += 1
            if log_path:
                log_message(log_path, f"Failed: {source_path_value} -> {dest_path.relative_to(source_path)}: {exc}")

    print("\n" + "=" * 40)
    if preview:
        print("PREVIEW COMPLETE. No files were moved.")
        print(f"Prepared to move {processed_count} file(s). Skipped {skipped_count} actual operations.")
        print("Remove --preview to execute the moves.")
    else:
        print(f"COMPLETE! Moved {processed_count} files. Skipped {skipped_count} errors.")
        if log_path:
            log_message(log_path, f"Complete: moved {processed_count}, skipped {skipped_count}")


def parse_args():
    parser = argparse.ArgumentParser(description='Organize music files by artist and album.')
    parser.add_argument('source', nargs='?', default='.', help='Folder containing audio files')
    parser.add_argument('--recursive', action='store_true', help='Search subfolders recursively')
    parser.add_argument('--preview', action='store_true', help='Preview moves without moving files (dry run)')
    parser.add_argument('--yes', '--confirm', action='store_true', help='Skip interactive confirmation and proceed with moves')
    parser.add_argument('--wait', action='store_true', help='Wait for Enter before exiting')
    parser.add_argument('--log-file', default='organize_music.log', help='Path to a log file')
    parser.add_argument('--no-log-file', action='store_true', help='Disable logging to file')
    parser.add_argument('--no-preserve-time', dest='preserve_time', action='store_false', help='Do not preserve original timestamps')
    parser.add_argument('--normalize-tags', action='store_true', help='Normalize and rewrite metadata tags in supported formats')
    parser.add_argument('--copy', action='store_true', help='Copy files instead of moving them')
    parser.add_argument('--move-duplicates', action='store_true', help='Move duplicate track files into a duplicates subfolder')
    parser.add_argument('--template', default='{artist}/{album}/{track} - {title}{ext}', help='Filename template with placeholders like {artist}, {album}, {title}, {track}, {ext}, {date}, {year}')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    organize_music(
        args.source,
        recursive=args.recursive,
        preview=args.preview,
        log_file=None if args.no_log_file else args.log_file,
        preserve_time=args.preserve_time,
        normalize_tags=args.normalize_tags,
        confirm=not args.yes,
        template=args.template,
        copy_mode=args.copy,
        move_duplicates=args.move_duplicates
    )

    if args.wait and sys.stdin.isatty():
        input('Press Enter to exit...')
