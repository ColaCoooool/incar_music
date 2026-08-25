"""Playlists API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.database import get_db
from models.playlist import Playlist, PlaylistSong
from models.song import Song

router = APIRouter(prefix="/api/playlists", tags=["playlists"])


# ─── Schemas ─────────────────────────────────────────────────────────

class PlaylistCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""


class PlaylistUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None


class AddSongRequest(BaseModel):
    song_id: int


class PlaylistResponse(BaseModel):
    id: int
    name: str
    description: str
    song_count: int = 0


class PlaylistSongResponse(BaseModel):
    id: int
    title: str
    artist_name: str = ""
    duration: Optional[float] = None


class PlaylistDetailResponse(PlaylistResponse):
    songs: list[PlaylistSongResponse] = []


# ─── Helpers ─────────────────────────────────────────────────────────

async def _get_playlist(db: AsyncSession, playlist_id: int) -> Playlist:
    result = await db.execute(
        select(Playlist)
        .options(
            selectinload(Playlist.songs)
            .selectinload(PlaylistSong.song)
            .selectinload(Song.artist)
        )
        .where(Playlist.id == playlist_id)
    )
    playlist = result.scalar_one_or_none()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return playlist


def _song_payload(song: Song) -> PlaylistSongResponse:
    return PlaylistSongResponse(
        id=song.id,
        title=song.title,
        artist_name=song.artist.name if song.artist else "",
        duration=song.duration,
    )


# ─── Routes ──────────────────────────────────────────────────────────

@router.get("", response_model=list[PlaylistResponse])
async def list_playlists(db: AsyncSession = Depends(get_db)):
    """List all playlists with song counts."""
    result = await db.execute(
        select(Playlist).options(selectinload(Playlist.songs))
    )
    playlists = result.scalars().all()
    return [
        PlaylistResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            song_count=len(p.songs),
        )
        for p in playlists
    ]


@router.post("", response_model=PlaylistResponse)
async def create_playlist(
    request: PlaylistCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new playlist."""
    playlist = Playlist(name=request.name, description=request.description)
    db.add(playlist)
    await db.commit()
    await db.refresh(playlist)
    return PlaylistResponse(
        id=playlist.id, name=playlist.name, description=playlist.description
    )


@router.get("/{playlist_id}", response_model=PlaylistDetailResponse)
async def get_playlist(playlist_id: int, db: AsyncSession = Depends(get_db)):
    """Get playlist details with its songs (ordered by position)."""
    playlist = await _get_playlist(db, playlist_id)
    songs = [_song_payload(ps.song) for ps in playlist.songs]
    return PlaylistDetailResponse(
        id=playlist.id,
        name=playlist.name,
        description=playlist.description,
        song_count=len(songs),
        songs=songs,
    )


@router.put("/{playlist_id}", response_model=PlaylistResponse)
async def update_playlist(
    playlist_id: int,
    request: PlaylistUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Rename a playlist or change its description."""
    playlist = await _get_playlist(db, playlist_id)
    if request.name is not None:
        playlist.name = request.name
    if request.description is not None:
        playlist.description = request.description
    await db.commit()
    await db.refresh(playlist)
    return PlaylistResponse(
        id=playlist.id,
        name=playlist.name,
        description=playlist.description,
        song_count=len(playlist.songs),
    )


@router.delete("/{playlist_id}")
async def delete_playlist(playlist_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a playlist and its song entries."""
    playlist = await _get_playlist(db, playlist_id)
    for ps in list(playlist.songs):
        await db.delete(ps)
    await db.delete(playlist)
    await db.commit()
    return {"message": "Playlist deleted"}


@router.post("/{playlist_id}/songs", response_model=PlaylistDetailResponse)
async def add_song_to_playlist(
    playlist_id: int,
    request: AddSongRequest,
    db: AsyncSession = Depends(get_db),
):
    """Add a song to a playlist (idempotent, appended at the end)."""
    playlist = await _get_playlist(db, playlist_id)

    song = (
        await db.execute(select(Song).where(Song.id == request.song_id))
    ).scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    existing = (
        await db.execute(
            select(PlaylistSong).where(
                PlaylistSong.playlist_id == playlist_id,
                PlaylistSong.song_id == request.song_id,
            )
        )
    ).scalar_one_or_none()
    if not existing:
        max_pos = (
            await db.execute(
                select(func.max(PlaylistSong.position)).where(
                    PlaylistSong.playlist_id == playlist_id
                )
            )
        ).scalar() or 0
        db.add(
            PlaylistSong(
                playlist_id=playlist_id,
                song_id=request.song_id,
                position=max_pos + 1,
            )
        )
        await db.commit()

    return await get_playlist(playlist_id, db)


@router.delete("/{playlist_id}/songs/{song_id}")
async def remove_song_from_playlist(
    playlist_id: int,
    song_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Remove a song from a playlist."""
    await _get_playlist(db, playlist_id)
    ps = (
        await db.execute(
            select(PlaylistSong).where(
                PlaylistSong.playlist_id == playlist_id,
                PlaylistSong.song_id == song_id,
            )
        )
    ).scalar_one_or_none()
    if not ps:
        raise HTTPException(status_code=404, detail="Song not in playlist")
    await db.delete(ps)
    await db.commit()
    return {"message": "Song removed from playlist"}
