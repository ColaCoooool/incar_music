"""Music library scanner.

Scans the NAS music directory, extracts metadata from audio files,
and stores it in the database.
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional

from mutagen import File as MutagenFile
from mutagen.id3 import ID3, ID3NoHeaderError
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.album import Album
from models.artist import Artist
from models.genre import Genre
from models.song import Song

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {".mp3", ".flac", ".wav", ".aac", ".ogg", ".wma", ".m4a", ".ape", ".opus"}

# Formats whose easy-tag keys differ from the mutagen easy names.
# Easy formats (mp3/flac/ogg/...) expose "title"/"artist"/...;
# WAVE exposes ID3 frame names (TIT2/TPE1/...).
_TAG_KEY_CANDIDATES = {
    "title": ("title", "TIT2"),
    "artist": ("artist", "TPE1"),
    "album": ("album", "TALB"),
    "genre": ("genre", "TCON"),
    "date": ("date", "TDRC"),
    "tracknumber": ("tracknumber", "TRCK"),
    "discnumber": ("discnumber", "TPOS"),
    "comment": ("comment", "COMM"),
}


def _get_tag(audio, candidates) -> str:
    """Read a tag by any of the candidate keys, handling easy tags and ID3 frames."""
    for key in candidates:
        try:
            v = audio[key]
        except (KeyError, TypeError):
            continue
        if hasattr(v, "text") and v.text:  # ID3 frame object
            return str(v.text[0])
        if isinstance(v, (list, tuple)) and v:
            return str(v[0])
        if isinstance(v, str) and v:
            return v
    return ""


def extract_metadata(file_path: Path) -> Optional[dict]:
    """Extract metadata from an audio file using mutagen.

    Returns None when the file is not a parseable audio file.
    """
    meta = {
        "title": file_path.stem,
        "artist": "",
        "album": "",
        "genre": "",
        "year": None,
        "track_number": None,
        "disc_number": None,
        "duration": None,
        "bitrate": None,
        "sample_rate": None,
        "channels": None,
        "file_size": file_path.stat().st_size,
        "format": file_path.suffix.lower().lstrip("."),
        "comment": "",
    }

    try:
        audio = MutagenFile(str(file_path), easy=True)
        if audio is None:
            return None

        # Duration and audio properties
        if hasattr(audio.info, "length"):
            meta["duration"] = audio.info.length
        if hasattr(audio.info, "bitrate"):
            meta["bitrate"] = audio.info.bitrate // 1000 if audio.info.bitrate else None
        if hasattr(audio.info, "sample_rate"):
            meta["sample_rate"] = audio.info.sample_rate
        if hasattr(audio.info, "channels"):
            meta["channels"] = audio.info.channels

        # Tags (works for both easy-tag formats and WAVE's ID3 frames)
        meta["title"] = _get_tag(audio, _TAG_KEY_CANDIDATES["title"]) or file_path.stem
        meta["artist"] = _get_tag(audio, _TAG_KEY_CANDIDATES["artist"])
        meta["album"] = _get_tag(audio, _TAG_KEY_CANDIDATES["album"])
        meta["genre"] = _get_tag(audio, _TAG_KEY_CANDIDATES["genre"])
        meta["comment"] = _get_tag(audio, _TAG_KEY_CANDIDATES["comment"])

        # Year
        date_str = _get_tag(audio, _TAG_KEY_CANDIDATES["date"])
        if date_str:
            try:
                meta["year"] = int(date_str[:4])
            except (ValueError, IndexError):
                pass

        # Track number
        track_str = _get_tag(audio, _TAG_KEY_CANDIDATES["tracknumber"])
        if track_str:
            try:
                meta["track_number"] = int(track_str.split("/")[0])
            except (ValueError, IndexError):
                pass

        # Disc number
        disc_str = _get_tag(audio, _TAG_KEY_CANDIDATES["discnumber"])
        if disc_str:
            try:
                meta["disc_number"] = int(disc_str.split("/")[0])
            except (ValueError, IndexError):
                pass

    except Exception as e:
        logger.warning(f"Failed to extract metadata from {file_path}: {e}")
        return None

    return meta


def file_hash(file_path: Path) -> str:
    """Generate a stable hash for a file path (relative to music library)."""
    try:
        rel = file_path.relative_to(settings.MUSIC_LIBRARY_PATH)
    except ValueError:
        rel = file_path
    return hashlib.md5(str(rel).encode()).hexdigest()


async def _get_or_create_artist(db: AsyncSession, name: str) -> Optional[int]:
    result = await db.execute(select(Artist).where(Artist.name == name))
    artist = result.scalar_one_or_none()
    if not artist:
        artist = Artist(name=name)
        db.add(artist)
        await db.flush()
    return artist.id


async def _get_or_create_album(
    db: AsyncSession, title: str, artist_id: Optional[int], year: Optional[int]
) -> Optional[int]:
    # Albums are scoped by (title, artist) so same-named albums by different
    # artists are kept apart.
    result = await db.execute(
        select(Album).where(
            Album.title == title, Album.artist_id == (artist_id or 0)
        )
    )
    album = result.scalar_one_or_none()
    if not album:
        album = Album(
            title=title,
            artist_id=artist_id or 0,
            year=year or 0,
        )
        db.add(album)
        await db.flush()
    return album.id


async def _get_or_create_genre(db: AsyncSession, name: str) -> Optional[int]:
    result = await db.execute(select(Genre).where(Genre.name == name))
    genre = result.scalar_one_or_none()
    if not genre:
        genre = Genre(name=name)
        db.add(genre)
        await db.flush()
    return genre.id


async def scan_library(db: AsyncSession, force: bool = False) -> dict:
    """Scan the music library directory and update the database.

    Returns statistics about the scan.
    """
    library_path = Path(settings.MUSIC_LIBRARY_PATH)
    if not library_path.exists():
        logger.error(f"Music library path does not exist: {library_path}")
        return {"error": "Library path not found", "added": 0, "updated": 0, "skipped": 0}

    stats = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}

    # Get existing file paths
    result = await db.execute(select(Song.file_path))
    existing_paths = {row[0] for row in result.all()}

    # Walk through all audio files
    for root, _, files in library_path.walk():
        for filename in files:
            file_path = Path(root) / filename
            if file_path.suffix.lower() not in SUPPORTED_FORMATS:
                continue

            file_path_str = str(file_path)

            try:
                if file_path_str in existing_paths and not force:
                    stats["skipped"] += 1
                    continue

                # Extract metadata (None => unparseable file, skip it)
                meta = extract_metadata(file_path)
                if meta is None:
                    stats["skipped"] += 1
                    continue

                # Get or create artist / album / genre
                artist_id = await _get_or_create_artist(db, meta["artist"]) if meta["artist"] else None
                album_id = await _get_or_create_album(db, meta["album"], artist_id, meta["year"]) if meta["album"] else None
                genre_id = await _get_or_create_genre(db, meta["genre"]) if meta["genre"] else None

                song_data = dict(
                    title=meta["title"],
                    file_path=file_path_str,
                    relative_path=str(file_path.relative_to(library_path)),
                    duration=meta["duration"],
                    format=meta["format"],
                    bitrate=meta["bitrate"],
                    sample_rate=meta["sample_rate"],
                    channels=meta["channels"],
                    file_size=meta["file_size"],
                    year=meta["year"],
                    track_number=meta["track_number"],
                    disc_number=meta["disc_number"],
                    comment=meta["comment"],
                    artist_id=artist_id,
                    album_id=album_id,
                    genre_id=genre_id,
                    metadata_complete=bool(meta["artist"] and meta["album"]),
                )

                if file_path_str in existing_paths:
                    # force: update the existing song in place
                    song = (
                        await db.execute(select(Song).where(Song.file_path == file_path_str))
                    ).scalar_one()
                    for field, value in song_data.items():
                        setattr(song, field, value)
                    stats["updated"] += 1
                else:
                    song = Song(**song_data)
                    db.add(song)
                    stats["added"] += 1

                if stats["added"] % 100 == 0 and stats["added"] > 0:
                    await db.flush()
                    logger.info(f"Scan progress: {stats['added']} songs added")

            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                stats["errors"] += 1

    await db.commit()
    logger.info(f"Scan complete: {stats}")
    return stats
