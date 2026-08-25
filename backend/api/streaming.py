"""Streaming API routes."""

import re

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db
from models.song import Song
from services import streamer
from services.smart_cache import smart_cache

router = APIRouter(prefix="/api/stream", tags=["streaming"])

# HLS segments must be plain segment files, never path components
_SEGMENT_NAME_RE = re.compile(r"^segment_\d{4}\.aac$")


@router.get("/{song_id}")
async def stream_song(
    song_id: int,
    bitrate: int = Query(192, ge=32, le=320),
    db: AsyncSession = Depends(get_db),
):
    """Stream a song directly (non-HLS fallback)."""
    result = await db.execute(select(Song).where(Song.id == song_id))
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    # Check cache first
    cached = await smart_cache.get_cached(song_id)
    file_path = cached or song.file_path

    import os
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    # Determine content type
    ext = file_path.lower().rsplit(".", 1)[-1] if "." in file_path else "mp3"
    content_types = {
        "mp3": "audio/mpeg",
        "flac": "audio/flac",
        "wav": "audio/wav",
        "aac": "audio/aac",
        "ogg": "audio/ogg",
        "m4a": "audio/mp4",
        "opus": "audio/opus",
        "wma": "audio/x-ms-wma",
    }
    content_type = content_types.get(ext, "audio/mpeg")

    return FileResponse(
        path=file_path,
        media_type=content_type,
        filename=f"{song.title}.{ext}",
    )


@router.get("/{song_id}/hls/playlist.m3u8")
async def get_hls_playlist(
    song_id: int,
    bitrate: int = Query(192, ge=32, le=320),
    db: AsyncSession = Depends(get_db),
):
    """Get HLS playlist for adaptive streaming."""
    result = await db.execute(select(Song).where(Song.id == song_id))
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    playlist_path = await streamer.create_hls_stream(
        song.file_path, song_id, bitrate
    )

    if not playlist_path:
        raise HTTPException(status_code=500, detail="Failed to create HLS stream")

    from fastapi.responses import FileResponse
    return FileResponse(
        path=playlist_path,
        media_type="application/vnd.apple.mpegurl",
    )


@router.get("/{song_id}/hls/{segment}")
async def get_hls_segment(
    song_id: int,
    segment: str,
    bitrate: int = Query(192, ge=32, le=320),
):
    """Get an HLS segment file."""
    if not _SEGMENT_NAME_RE.match(segment):
        raise HTTPException(status_code=400, detail="Invalid segment name")

    from core.config import settings
    segment_path = settings.hls_path / f"song_{song_id}" / f"br_{bitrate}" / segment

    if not segment_path.exists():
        raise HTTPException(status_code=404, detail="Segment not found")

    return FileResponse(
        path=str(segment_path),
        media_type="audio/aac",
    )


@router.post("/{song_id}/cache")
async def cache_song(song_id: int, db: AsyncSession = Depends(get_db)):
    """Cache a song for offline playback."""
    path = await smart_cache.cache_song(db, song_id)
    if path:
        return {"message": "Song cached", "path": path}
    raise HTTPException(status_code=500, detail="Failed to cache song")


@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics."""
    return await smart_cache.get_cache_stats()


@router.post("/cache/clear")
async def clear_cache():
    """Clear all cached songs."""
    await smart_cache.clear_cache()
    return {"message": "Cache cleared"}


@router.post("/cache/pre-cache")
async def pre_cache(
    song_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Pre-cache songs based on current playback."""
    cached = await smart_cache.predict_and_pre_cache(db, song_id)
    return {"cached_song_ids": cached}
