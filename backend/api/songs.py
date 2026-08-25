"""Songs API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.database import get_db
from models.song import Song
from models.artist import Artist
from models.album import Album
from models.genre import Genre
from models.lyrics import Lyrics
from models.cover import CoverArt

router = APIRouter(prefix="/api/songs", tags=["songs"])

# Columns that may be used for sorting (validated to avoid SQL errors/abuse)
SORTABLE_COLUMNS = {
    "title",
    "play_count",
    "duration",
    "date_added",
    "year",
    "bitrate",
    "file_size",
    "sample_rate",
}


# ─── Schemas ─────────────────────────────────────────────────────────

class SongResponse(BaseModel):
    id: int
    title: str
    artist_name: str = ""
    album_title: str = ""
    genre_name: str = ""
    duration: Optional[float] = None
    format: Optional[str] = None
    bitrate: Optional[int] = None
    sample_rate: Optional[int] = None
    has_lyrics: bool = False
    has_cover: bool = False
    play_count: int = 0
    file_path: str
    cover_url: str = ""

    class Config:
        from_attributes = True


class SongDetailResponse(SongResponse):
    year: Optional[int] = None
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    channels: Optional[int] = None
    file_size: Optional[int] = None
    lyrics_content: str = ""
    lyrics_synced: bool = False
    cover_path: str = ""


class SongUpdateRequest(BaseModel):
    title: Optional[str] = None
    artist_name: Optional[str] = None
    album_title: Optional[str] = None
    genre_name: Optional[str] = None
    year: Optional[int] = None


# ─── Helpers ─────────────────────────────────────────────────────────

def _song_to_response(song: Song) -> SongResponse:
    return SongResponse(
        id=song.id,
        title=song.title,
        artist_name=song.artist.name if song.artist else "",
        album_title=song.album.title if song.album else "",
        genre_name=song.genre.name if song.genre else "",
        duration=song.duration,
        format=song.format,
        bitrate=song.bitrate,
        sample_rate=song.sample_rate,
        has_lyrics=song.has_lyrics,
        has_cover=song.has_cover,
        play_count=song.play_count,
        file_path=song.file_path,
        cover_url=f"/api/covers/{song.id}" if song.has_cover else "",
    )


# ─── Routes ──────────────────────────────────────────────────────────

@router.get("/", response_model=list[SongResponse])
async def list_songs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    artist: Optional[str] = None,
    album: Optional[str] = None,
    genre: Optional[str] = None,
    sort_by: str = "title",
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_db),
):
    """List songs with pagination and filtering."""
    query = select(Song).options(
        selectinload(Song.artist),
        selectinload(Song.album),
        selectinload(Song.genre),
    )

    # Filters (each branch joins at most once to avoid cartesian products)
    if search:
        search_pattern = f"%{search}%"
        query = query.outerjoin(Song.artist).where(
            or_(
                Song.title.ilike(search_pattern),
                Artist.name.ilike(search_pattern),
            )
        )
    elif artist:
        query = query.join(Song.artist).where(Artist.name.ilike(f"%{artist}%"))
    elif album:
        query = query.join(Song.album).where(Album.title.ilike(f"%{album}%"))
    elif genre:
        query = query.join(Song.genre).where(Genre.name == genre)

    # Sorting (validated)
    if sort_by not in SORTABLE_COLUMNS:
        raise HTTPException(status_code=400, detail=f"Invalid sort_by: {sort_by}")
    sort_column = getattr(Song, sort_by, Song.title)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    songs = result.scalars().all()
    return [_song_to_response(s) for s in songs]


@router.get("/count")
async def get_song_count(
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get total song count."""
    query = select(func.count(Song.id))
    if search:
        query = query.join(Artist, isouter=True).where(
            or_(
                Song.title.ilike(f"%{search}%"),
                Artist.name.ilike(f"%{search}%"),
            )
        )
    result = await db.execute(query)
    count = result.scalar()
    return {"count": count}


@router.get("/{song_id}", response_model=SongDetailResponse)
async def get_song(song_id: int, db: AsyncSession = Depends(get_db)):
    """Get detailed song information."""
    result = await db.execute(
        select(Song)
        .options(
            selectinload(Song.artist),
            selectinload(Song.album),
            selectinload(Song.genre),
            selectinload(Song.lyrics),
            selectinload(Song.cover),
        )
        .where(Song.id == song_id)
    )
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    return SongDetailResponse(
        id=song.id,
        title=song.title,
        artist_name=song.artist.name if song.artist else "",
        album_title=song.album.title if song.album else "",
        genre_name=song.genre.name if song.genre else "",
        duration=song.duration,
        format=song.format,
        bitrate=song.bitrate,
        sample_rate=song.sample_rate,
        has_lyrics=song.has_lyrics,
        has_cover=song.has_cover,
        play_count=song.play_count,
        file_path=song.file_path,
        year=song.year,
        track_number=song.track_number,
        disc_number=song.disc_number,
        channels=song.channels,
        file_size=song.file_size,
        lyrics_content=song.lyrics.content if song.lyrics else "",
        lyrics_synced=song.lyrics.is_synced if song.lyrics else False,
        cover_path=song.cover.file_path if song.cover else "",
        cover_url=f"/api/covers/{song.id}" if song.has_cover else "",
    )


@router.put("/{song_id}", response_model=SongResponse)
async def update_song(
    song_id: int,
    request: SongUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update song metadata (title, artist, album, genre, year)."""
    result = await db.execute(
        select(Song)
        .options(selectinload(Song.artist), selectinload(Song.album), selectinload(Song.genre))
        .where(Song.id == song_id)
    )
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    if request.title is not None:
        song.title = request.title
    if request.year is not None:
        song.year = request.year

    if request.artist_name is not None:
        if request.artist_name:
            artist = (
                await db.execute(select(Artist).where(Artist.name == request.artist_name))
            ).scalar_one_or_none()
            if not artist:
                artist = Artist(name=request.artist_name)
                db.add(artist)
                await db.flush()
            song.artist_id = artist.id
        else:
            song.artist_id = None

    if request.album_title is not None:
        if request.album_title:
            album = (
                await db.execute(
                    select(Album).where(
                        Album.title == request.album_title,
                        Album.artist_id == (song.artist_id or 0),
                    )
                )
            ).scalar_one_or_none()
            if not album:
                album = Album(
                    title=request.album_title,
                    artist_id=song.artist_id or 0,
                    year=request.year or song.year or 0,
                )
                db.add(album)
                await db.flush()
            song.album_id = album.id
        else:
            song.album_id = None

    if request.genre_name is not None:
        if request.genre_name:
            genre = (
                await db.execute(select(Genre).where(Genre.name == request.genre_name))
            ).scalar_one_or_none()
            if not genre:
                genre = Genre(name=request.genre_name)
                db.add(genre)
                await db.flush()
            song.genre_id = genre.id
        else:
            song.genre_id = None

    song.metadata_complete = bool(song.artist_id and song.album_id)
    await db.commit()
    await db.refresh(song)
    return _song_to_response(song)


@router.delete("/{song_id}")
async def delete_song(song_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a song from the database (not from disk), cascading related rows."""
    result = await db.execute(select(Song).where(Song.id == song_id))
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    # Explicitly delete related rows (lyrics, cover, playlist entries)
    from models.cover import CoverArt
    from models.lyrics import Lyrics
    from models.playlist import PlaylistSong

    for model in (Lyrics, CoverArt, PlaylistSong):
        related = await db.execute(select(model).where(model.song_id == song_id))
        for row in related.scalars().all():
            await db.delete(row)

    await db.delete(song)
    await db.commit()
    return {"message": "Song deleted"}


@router.post("/{song_id}/play")
async def record_play(song_id: int, db: AsyncSession = Depends(get_db)):
    """Record a play for a song."""
    result = await db.execute(select(Song).where(Song.id == song_id))
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    song.play_count += 1
    song.last_played = func.now()
    await db.commit()
    return {"play_count": song.play_count}
