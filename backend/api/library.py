"""Library management API routes."""

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.database import get_db
from models.song import Song
from models.artist import Artist
from models.album import Album
from models.genre import Genre
from services.scanner import scan_library
from services.metadata_fetcher import MetadataFetcher

router = APIRouter(prefix="/api/library", tags=["library"])


# ─── Schemas ─────────────────────────────────────────────────────────

class ScanResponse(BaseModel):
    message: str
    stats: dict


class MetadataFillRequest(BaseModel):
    song_ids: Optional[list[int]] = None


class ArtistResponse(BaseModel):
    id: int
    name: str
    song_count: int = 0

    class Config:
        from_attributes = True


class AlbumResponse(BaseModel):
    id: int
    title: str
    artist_name: str = ""
    year: Optional[int] = None
    song_count: int = 0

    class Config:
        from_attributes = True


class GenreResponse(BaseModel):
    id: int
    name: str
    song_count: int = 0

    class Config:
        from_attributes = True


class LibraryStats(BaseModel):
    total_songs: int
    total_artists: int
    total_albums: int
    total_genres: int
    total_duration_hours: float
    missing_lyrics: int
    missing_covers: int
    incomplete_metadata: int


# ─── Routes ──────────────────────────────────────────────────────────

@router.get("/stats", response_model=LibraryStats)
async def get_library_stats(db: AsyncSession = Depends(get_db)):
    """Get library statistics."""
    total_songs = (await db.execute(select(func.count(Song.id)))).scalar() or 0
    total_artists = (await db.execute(select(func.count(Artist.id)))).scalar() or 0
    total_albums = (await db.execute(select(func.count(Album.id)))).scalar() or 0
    total_genres = (await db.execute(select(func.count(Genre.id)))).scalar() or 0

    total_duration = (
        await db.execute(select(func.sum(Song.duration)))
    ).scalar() or 0

    missing_lyrics = (
        await db.execute(
            select(func.count(Song.id)).where(Song.has_lyrics == False)  # noqa: E712
        )
    ).scalar() or 0

    missing_covers = (
        await db.execute(
            select(func.count(Song.id)).where(Song.has_cover == False)  # noqa: E712
        )
    ).scalar() or 0

    incomplete = (
        await db.execute(
            select(func.count(Song.id)).where(Song.metadata_complete == False)  # noqa: E712
        )
    ).scalar() or 0

    return LibraryStats(
        total_songs=total_songs,
        total_artists=total_artists,
        total_albums=total_albums,
        total_genres=total_genres,
        total_duration_hours=round(total_duration / 3600, 1),
        missing_lyrics=missing_lyrics,
        missing_covers=missing_covers,
        incomplete_metadata=incomplete,
    )


@router.post("/scan", response_model=ScanResponse)
async def trigger_scan(
    background_tasks: BackgroundTasks,
    force: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Trigger a library scan in the background."""
    background_tasks.add_task(scan_library, db, force=force)
    return ScanResponse(message="Scan started", stats={})


@router.post("/scan/sync")
async def trigger_scan_sync(
    force: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Trigger a synchronous library scan (for small libraries)."""
    stats = await scan_library(db, force=force)
    return {"message": "Scan complete", "stats": stats}


@router.post("/metadata/fill")
async def fill_metadata(
    request: MetadataFillRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Fill missing metadata (lyrics, covers, etc.) for songs."""

    async def _fill():
        fetcher = MetadataFetcher(db)
        try:
            await fetcher.fill_missing_metadata(request.song_ids)
        finally:
            await fetcher.close()

    background_tasks.add_task(_fill)
    return {"message": "Metadata fill started"}


# ─── Artists ─────────────────────────────────────────────────────────

@router.get("/artists", response_model=list[ArtistResponse])
async def list_artists(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List artists with pagination."""
    query = select(Artist)

    if search:
        query = query.where(Artist.name.ilike(f"%{search}%"))

    query = query.order_by(Artist.name).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    artists = result.scalars().all()

    responses = []
    for artist in artists:
        count = (
            await db.execute(select(func.count(Song.id)).where(Song.artist_id == artist.id))
        ).scalar() or 0
        responses.append(ArtistResponse(id=artist.id, name=artist.name, song_count=count))

    return responses


@router.get("/artists/{artist_id}")
async def get_artist(artist_id: int, db: AsyncSession = Depends(get_db)):
    """Get artist details with their songs."""
    result = await db.execute(
        select(Artist).options(selectinload(Artist.songs)).where(Artist.id == artist_id)
    )
    artist = result.scalar_one_or_none()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    return {
        "id": artist.id,
        "name": artist.name,
        "biography": artist.biography,
        "avatar_url": artist.avatar_url,
        "song_count": len(artist.songs),
    }


# ─── Albums ──────────────────────────────────────────────────────────

@router.get("/albums", response_model=list[AlbumResponse])
async def list_albums(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    artist_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """List albums with pagination."""
    query = select(Album).options(selectinload(Album.songs))

    if search:
        query = query.where(Album.title.ilike(f"%{search}%"))
    if artist_id:
        query = query.where(Album.artist_id == artist_id)

    query = query.order_by(Album.title).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    albums = result.scalars().all()

    responses = []
    for album in albums:
        artist_result = await db.execute(select(Artist).where(Artist.id == album.artist_id))
        artist = artist_result.scalar_one_or_none()
        responses.append(
            AlbumResponse(
                id=album.id,
                title=album.title,
                artist_name=artist.name if artist else "",
                year=album.year,
                song_count=len(album.songs),
            )
        )

    return responses


@router.get("/albums/{album_id}")
async def get_album(album_id: int, db: AsyncSession = Depends(get_db)):
    """Get album details with its songs."""
    result = await db.execute(
        select(Album).options(
            selectinload(Album.songs).selectinload(Song.artist)
        ).where(Album.id == album_id)
    )
    album = result.scalar_one_or_none()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    artist_result = await db.execute(select(Artist).where(Artist.id == album.artist_id))
    artist = artist_result.scalar_one_or_none()

    return {
        "id": album.id,
        "title": album.title,
        "artist_name": artist.name if artist else "",
        "year": album.year,
        "songs": [
            {
                "id": s.id,
                "title": s.title,
                "artist_name": s.artist.name if s.artist else "",
                "duration": s.duration,
                "track_number": s.track_number,
            }
            for s in album.songs
        ],
    }


# ─── Genres ──────────────────────────────────────────────────────────

@router.get("/genres", response_model=list[GenreResponse])
async def list_genres(db: AsyncSession = Depends(get_db)):
    """List all genres."""
    result = await db.execute(select(Genre))
    genres = result.scalars().all()

    responses = []
    for genre in genres:
        count = (
            await db.execute(select(func.count(Song.id)).where(Song.genre_id == genre.id))
        ).scalar() or 0
        responses.append(GenreResponse(id=genre.id, name=genre.name, song_count=count))

    return responses
