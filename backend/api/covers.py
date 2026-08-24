"""Covers API routes."""

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.database import get_db
from models.cover import CoverArt
from models.song import Song

router = APIRouter(prefix="/api/covers", tags=["covers"])


@router.get("/{song_id}")
async def get_cover(song_id: int, db: AsyncSession = Depends(get_db)):
    """Get album cover for a song."""
    result = await db.execute(
        select(CoverArt).where(CoverArt.song_id == song_id)
    )
    cover = result.scalar_one_or_none()

    if not cover or not cover.file_path:
        # Return a default placeholder
        default_cover = Path("data/default_cover.png")
        if default_cover.exists():
            return FileResponse(str(default_cover), media_type="image/png")
        raise HTTPException(status_code=404, detail="Cover not found")

    if not os.path.exists(cover.file_path):
        raise HTTPException(status_code=404, detail="Cover file not found")

    media_types = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}
    content_type = media_types.get(cover.format, "image/jpeg")

    return FileResponse(path=cover.file_path, media_type=content_type)


@router.post("/{song_id}/upload")
async def upload_cover(
    song_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a custom cover for a song."""
    # Check song exists
    result = await db.execute(select(Song).where(Song.id == song_id))
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    # Determine format
    ext = "jpg"
    if file.content_type and "png" in file.content_type:
        ext = "png"

    # Save file
    cover_filename = f"{song_id}.{ext}"
    cover_path = settings.cover_path / cover_filename

    content = await file.read()
    cover_path.write_bytes(content)

    # Resize
    try:
        img = Image.open(cover_path)
        if max(img.size) > settings.COVER_MAX_SIZE:
            img.thumbnail(
                (settings.COVER_MAX_SIZE, settings.COVER_MAX_SIZE),
                Image.Resampling.LANCZOS,
            )
            img.save(cover_path)
    except Exception:
        pass

    # Update or create cover record
    existing = await db.execute(
        select(CoverArt).where(CoverArt.song_id == song_id)
    )
    cover = existing.scalar_one_or_none()

    if cover:
        cover.file_path = str(cover_path)
        cover.source = "upload"
        cover.format = ext
    else:
        cover = CoverArt(
            song_id=song_id,
            file_path=str(cover_path),
            source="upload",
            format=ext,
        )
        db.add(cover)

    song.has_cover = True
    await db.commit()

    return {"message": "Cover uploaded", "path": str(cover_path)}


@router.delete("/{song_id}")
async def delete_cover(song_id: int, db: AsyncSession = Depends(get_db)):
    """Delete cover art for a song."""
    result = await db.execute(
        select(CoverArt).where(CoverArt.song_id == song_id)
    )
    cover = result.scalar_one_or_none()
    if not cover:
        raise HTTPException(status_code=404, detail="Cover not found")

    # Delete file
    if cover.file_path and os.path.exists(cover.file_path):
        os.remove(cover.file_path)

    await db.delete(cover)

    # Update song
    song_result = await db.execute(select(Song).where(Song.id == song_id))
    song = song_result.scalar_one_or_none()
    if song:
        song.has_cover = False

    await db.commit()
    return {"message": "Cover deleted"}
