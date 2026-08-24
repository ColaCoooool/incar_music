"""Lyrics API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db
from models.lyrics import Lyrics
from models.song import Song
from services.metadata_fetcher import MetadataFetcher

router = APIRouter(prefix="/api/lyrics", tags=["lyrics"])


class LyricsResponse(BaseModel):
    song_id: int
    content: str
    format: str
    language: str
    is_synced: bool
    source: str


class LyricsUpdateRequest(BaseModel):
    content: str
    format: str = "lrc"
    language: str = "zh"
    is_synced: bool = False


@router.get("/{song_id}", response_model=LyricsResponse)
async def get_lyrics(song_id: int, db: AsyncSession = Depends(get_db)):
    """Get lyrics for a song."""
    result = await db.execute(
        select(Lyrics).where(Lyrics.song_id == song_id)
    )
    lyrics = result.scalar_one_or_none()

    if not lyrics:
        raise HTTPException(status_code=404, detail="Lyrics not found")

    return LyricsResponse(
        song_id=lyrics.song_id,
        content=lyrics.content,
        format=lyrics.format,
        language=lyrics.language,
        is_synced=lyrics.is_synced,
        source=lyrics.source,
    )


@router.put("/{song_id}", response_model=LyricsResponse)
async def update_lyrics(
    song_id: int,
    request: LyricsUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update lyrics for a song."""
    result = await db.execute(
        select(Lyrics).where(Lyrics.song_id == song_id)
    )
    lyrics = result.scalar_one_or_none()

    if lyrics:
        lyrics.content = request.content
        lyrics.format = request.format
        lyrics.language = request.language
        lyrics.is_synced = request.is_synced
    else:
        lyrics = Lyrics(
            song_id=song_id,
            content=request.content,
            format=request.format,
            language=request.language,
            is_synced=request.is_synced,
            source="manual",
        )
        db.add(lyrics)

    # Update song flag
    song_result = await db.execute(select(Song).where(Song.id == song_id))
    song = song_result.scalar_one_or_none()
    if song:
        song.has_lyrics = True

    await db.commit()

    return LyricsResponse(
        song_id=lyrics.song_id,
        content=lyrics.content,
        format=lyrics.format,
        language=lyrics.language,
        is_synced=lyrics.is_synced,
        source=lyrics.source,
    )


@router.post("/{song_id}/fetch")
async def fetch_lyrics(song_id: int, db: AsyncSession = Depends(get_db)):
    """Fetch lyrics from online sources."""
    result = await db.execute(select(Song).where(Song.id == song_id))
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    fetcher = MetadataFetcher(db)
    try:
        lrc = await fetcher.fetch_lyrics(song)
        if lrc:
            await db.commit()
            return {"message": "Lyrics fetched", "content": lrc}
        return {"message": "No lyrics found"}
    finally:
        await fetcher.close()


@router.delete("/{song_id}")
async def delete_lyrics(song_id: int, db: AsyncSession = Depends(get_db)):
    """Delete lyrics for a song."""
    result = await db.execute(
        select(Lyrics).where(Lyrics.song_id == song_id)
    )
    lyrics = result.scalar_one_or_none()
    if not lyrics:
        raise HTTPException(status_code=404, detail="Lyrics not found")

    await db.delete(lyrics)

    # Update song flag
    song_result = await db.execute(select(Song).where(Song.id == song_id))
    song = song_result.scalar_one_or_none()
    if song:
        song.has_lyrics = False

    await db.commit()
    return {"message": "Lyrics deleted"}
