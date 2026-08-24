"""Scraper API routes."""

import os
import re
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.database import get_db
from models.song import Song
from scrapers.bilibili import BilibiliScraper, extract_bvid
from scrapers.douyin import DouyinScraper, extract_douyin_id

router = APIRouter(prefix="/api/scraper", tags=["scraper"])


class ScrapeRequest(BaseModel):
    url: str


class ScrapeResponse(BaseModel):
    message: str
    title: str = ""
    artist: str = ""
    file_path: str = ""
    song_id: int = 0


def _sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename."""
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip()[:200]


@router.post("/bilibili", response_model=ScrapeResponse)
async def scrape_bilibili(
    request: ScrapeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Scrape audio from a Bilibili video URL."""
    bvid = extract_bvid(request.url)
    if not bvid:
        raise HTTPException(status_code=400, detail="Invalid Bilibili URL")

    scraper = BilibiliScraper()
    try:
        # Get video info
        info = await scraper.get_video_info(bvid)
        if not info:
            raise HTTPException(status_code=404, detail="Video not found")

        # Prepare output path
        title = _sanitize_filename(info["title"])
        output_dir = settings.MUSIC_LIBRARY_PATH / "_scraped" / "bilibili"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / title)

        # Download
        result = await scraper.download_audio(bvid, output_path)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to download audio")

        # Add to database
        song = Song(
            title=info["title"],
            file_path=result["file_path"],
            relative_path=str(Path(result["file_path"]).relative_to(settings.MUSIC_LIBRARY_PATH)),
            format="m4a",
            source_url=request.url,
        )
        db.add(song)
        await db.commit()
        await db.refresh(song)

        return ScrapeResponse(
            message="Audio scraped successfully",
            title=info["title"],
            artist=info["owner"],
            file_path=result["file_path"],
            song_id=song.id,
        )

    finally:
        await scraper.close()


@router.post("/douyin", response_model=ScrapeResponse)
async def scrape_douyin(
    request: ScrapeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Scrape audio from a Douyin video URL."""
    video_id = extract_douyin_id(request.url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid Douyin URL")

    scraper = DouyinScraper()
    try:
        # Get video info
        info = await scraper.get_video_info(request.url)
        if not info:
            raise HTTPException(status_code=404, detail="Video not found")

        # Prepare output path
        title = _sanitize_filename(info["title"])
        output_dir = Path(settings.MUSIC_LIBRARY_PATH) / "_scraped" / "douyin"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / title)

        # Download
        result = await scraper.download_audio(request.url, output_path)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to download audio")

        # Add to database
        song = Song(
            title=info["title"],
            file_path=result["file_path"],
            relative_path=str(Path(result["file_path"]).relative_to(settings.MUSIC_LIBRARY_PATH)),
            format="mp4",
            source_url=request.url,
        )
        db.add(song)
        await db.commit()
        await db.refresh(song)

        return ScrapeResponse(
            message="Audio scraped successfully",
            title=info["title"],
            artist=info["author"],
            file_path=result["file_path"],
            song_id=song.id,
        )

    finally:
        await scraper.close()


@router.post("/auto")
async def scrape_auto(
    request: ScrapeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Auto-detect platform and scrape audio."""
    url = request.url

    if "bilibili.com" in url or "b23.tv" in url:
        return await scrape_bilibili(request, db)
    elif "douyin.com" in url:
        return await scrape_douyin(request, db)
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported URL. Supported platforms: Bilibili, Douyin",
        )
