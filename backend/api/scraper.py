"""Scraper API routes."""

import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.database import get_db
from models.song import Song
from scrapers import ytdlp
from scrapers.bilibili import BilibiliScraper, extract_bvid
from scrapers.douyin import extract_douyin_id

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


async def _store_scraped_song(
    db: AsyncSession,
    url: str,
    title: str,
    file_path: str,
) -> int:
    """Insert a scraped audio file into the library and return its song id."""
    song = Song(
        title=title,
        file_path=file_path,
        relative_path=str(Path(file_path).relative_to(settings.MUSIC_LIBRARY_PATH)),
        format=Path(file_path).suffix.lower().lstrip("."),
        source_url=url,
    )
    db.add(song)
    await db.commit()
    await db.refresh(song)
    return song.id


async def _scrape_via_ytdlp(
    db: AsyncSession,
    request: ScrapeRequest,
    subdir: str,
) -> ScrapeResponse:
    """Fallback/generic path: use yt-dlp to fetch only the audio stream."""
    output_dir = Path(settings.MUSIC_LIBRARY_PATH) / "_scraped" / subdir
    output_dir.mkdir(parents=True, exist_ok=True)

    result = await ytdlp.extract_audio(request.url, output_dir)
    if not result:
        detail = "Failed to download audio"
        if "douyin.com" in request.url:
            detail += "（抖音需要新鲜 cookies，请在 NAS 配置 YTDLP_COOKIES_FILE，见 README）"
        raise HTTPException(status_code=500, detail=detail)

    song_id = await _store_scraped_song(db, request.url, result["title"], result["file_path"])
    return ScrapeResponse(
        message="Audio scraped successfully",
        title=result["title"],
        artist=result["artist"],
        file_path=result["file_path"],
        song_id=song_id,
    )


@router.post("/bilibili", response_model=ScrapeResponse)
async def scrape_bilibili(
    request: ScrapeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Scrape audio from a Bilibili video URL.

    Fast path: bilibili's DASH API returns an audio-only stream (m4a).
    Fallback: yt-dlp audio extraction.
    """
    bvid = extract_bvid(request.url)
    if not bvid:
        raise HTTPException(status_code=400, detail="Invalid Bilibili URL")

    scraper = BilibiliScraper()
    try:
        info = await scraper.get_video_info(bvid)
        if info:
            title = _sanitize_filename(info["title"])
            output_dir = Path(settings.MUSIC_LIBRARY_PATH) / "_scraped" / "bilibili"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(output_dir / title)

            result = await scraper.download_audio(bvid, output_path)
            if result:
                song_id = await _store_scraped_song(
                    db, request.url, result["title"], result["file_path"]
                )
                return ScrapeResponse(
                    message="Audio scraped successfully",
                    title=result["title"],
                    artist=result["artist"],
                    file_path=result["file_path"],
                    song_id=song_id,
                )
    finally:
        await scraper.close()

    # Fallback: yt-dlp (handles DASH failures, blocked videos, etc.)
    return await _scrape_via_ytdlp(db, request, "bilibili")


@router.post("/douyin", response_model=ScrapeResponse)
async def scrape_douyin(
    request: ScrapeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Scrape audio from a Douyin video URL via yt-dlp (audio stream only)."""
    video_id = extract_douyin_id(request.url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid Douyin URL")

    return await _scrape_via_ytdlp(db, request, "douyin")


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
