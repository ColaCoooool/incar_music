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


def extract_metadata(file_path: Path) -> dict:
    """Extract metadata from an audio file using mutagen."""
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
            return meta

        # Duration and audio properties
        if hasattr(audio.info, "length"):
            meta["duration"] = audio.info.length
        if hasattr(audio.info, "bitrate"):
            meta["bitrate"] = audio.info.bitrate // 1000 if audio.info.bitrate else None
        if hasattr(audio.info, "sample_rate"):
            meta["sample_rate"] = audio.info.sample_rate
        if hasattr(audio.info, "channels"):
            meta["channels"] = audio.info.channels

        # Tags
        meta["title"] = audio.get("title", [file_path.stem])[0]
        meta["artist"] = audio.get("artist", [""])[0]
        meta["album"] = audio.get("album", [""])[0]
        meta["genre"] = audio.get("genre", [""])[0]
        meta["comment"] = audio.get("comment", [""])[0]

        # Year
        date_str = audio.get("date", [""])[0]
        if date_str:
            try:
                meta["year"] = int(date_str[:4])
            except (ValueError, IndexError):
                pass

        # Track number
        track_str = audio.get("tracknumber", [""])[0]
        if track_str:
            try:
                meta["track_number"] = int(track_str.split("/")[0])
            except (ValueError, IndexError):
                pass

        # Disc number
        disc_str = audio.get("discnumber", [""])[0]
        if disc_str:
            try:
                meta["disc_number"] = int(disc_str.split("/")[0])
            except (ValueError, IndexError):
                pass

    except Exception as e:
        logger.warning(f"Failed to extract metadata from {file_path}: {e}")

    return meta


def file_hash(file_path: Path) -> str:
    """Generate a stable hash for a file path (relative to music library)."""
    try:
        rel = file_path.relative_to(settings.MUSIC_LIBRARY_PATH)
    except ValueError:
        rel = file_path
    return hashlib.md5(str(rel).encode()).hexdigest()


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
                # Check if already in database
                if file_path_str in existing_paths and not force:
                    stats["skipped"] += 1
                    continue

                # Extract metadata
                meta = extract_metadata(file_path)

                # Get or create artist
                artist_id = None
                if meta["artist"]:
                    artist_result = await db.execute(
                        select(Artist).where(Artist.name == meta["artist"])
                    )
                    artist = artist_result.scalar_one_or_none()
                    if not artist:
                        artist = Artist(name=meta["artist"])
                        db.add(artist)
                        await db.flush()
                    artist_id = artist.id

                # Get or create album
                album_id = None
                if meta["album"]:
                    album_result = await db.execute(
                        select(Album).where(Album.title == meta["album"])
                    )
                    album = album_result.scalar_one_or_none()
                    if not album:
                        album = Album(
                            title=meta["album"],
                            artist_id=artist_id or 0,
                            year=meta["year"] or 0,
                        )
                        db.add(album)
                        await db.flush()
                    album_id = album.id

                # Get or create genre
                genre_id = None
                if meta["genre"]:
                    genre_result = await db.execute(
                        select(Genre).where(Genre.name == meta["genre"])
                    )
                    genre = genre_result.scalar_one_or_none()
                    if not genre:
                        genre = Genre(name=meta["genre"])
                        db.add(genre)
                        await db.flush()
                    genre_id = genre.id

                # Create song
                song = Song(
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
                    has_lyrics=False,
                    has_cover=False,
                    metadata_complete=bool(meta["artist"] and meta["album"]),
                )
                db.add(song)
                stats["added"] += 1

                if stats["added"] % 100 == 0:
                    await db.flush()
                    logger.info(f"Scan progress: {stats['added']} songs added")

            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                stats["errors"] += 1

    await db.commit()
    logger.info(f"Scan complete: {stats}")
    return stats
