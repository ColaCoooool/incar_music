"""yt-dlp based scraper: download the best audio stream from supported sites.

Supports Bilibili and Douyin (and many other sites via yt-dlp). Only the
audio stream is fetched — never the full video — to save bandwidth and
device storage.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

import yt_dlp

logger = logging.getLogger(__name__)

# Prefer an audio-only container; fall back to whatever audio yt-dlp finds.
_FORMAT_SELECTION = "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best"

# Douyin serves only muxed video+audio streams (no audio-only format). Pick a
# low-bitrate stream to save bandwidth, then extract the audio track and
# delete the video file to save storage.
_DOUYIN_FORMAT_SELECTION = "worst[tbr<=400]/worst/best"
_AUDIO_EXTRACT = {
    "key": "FFmpegExtractAudio",
    "preferredcodec": "m4a",
    "preferredquality": "128",
}


def cookies_file_path() -> Optional[Path]:
    """Resolve the cookies file used by yt-dlp.

    Priority: YTDLP_COOKIES_FILE env/config, else the uploaded file at
    <data_dir>/cookies.txt. Returns None when neither exists.
    """
    from core.config import settings

    if settings.YTDLP_COOKIES_FILE:
        p = Path(settings.YTDLP_COOKIES_FILE)
        if p.exists():
            return p
    default = settings.data_dir / "cookies.txt"
    return default if default.exists() else None


def _ydl_opts(output_dir: Path, platform: str) -> dict:
    opts = {
        "outtmpl": str(output_dir / "%(title).120B.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "socket_timeout": 30,
        "retries": 2,
    }
    if platform == "douyin":
        opts["format"] = _DOUYIN_FORMAT_SELECTION
        opts["postprocessors"] = [_AUDIO_EXTRACT]
    else:
        opts["format"] = _FORMAT_SELECTION
    cookies = cookies_file_path()
    if cookies:
        opts["cookiefile"] = str(cookies)
    return opts


def _run_extract(url: str, output_dir: Path) -> Optional[dict]:
    platform = "bilibili" if "bilibili" in url else "douyin"
    with yt_dlp.YoutubeDL(_ydl_opts(output_dir, platform)) as ydl:
        info = ydl.extract_info(url, download=False)
        if not info:
            return None

        title = info.get("title") or "audio"
        artist = info.get("uploader") or info.get("creator") or ""

        ydl.download([url])

        # Locate the actual downloaded file
        filepath = ""
        dl = (info.get("requested_downloads") or [{}])[0]
        filepath = dl.get("filepath") or ""
        if not filepath or not Path(filepath).exists():
            matches = list(output_dir.glob(f"*{title}*"))
            if not matches:
                logger.error(f"yt-dlp download finished but file not found for {url}")
                return None
            filepath = str(matches[0])

        return {
            "title": title,
            "artist": artist,
            "file_path": filepath,
            "platform": platform,
        }


async def extract_audio(url: str, output_dir: Path) -> Optional[dict]:
    """Download the best audio stream for a URL.

    yt-dlp is synchronous and blocking, so it runs in a thread executor to
    keep the event loop responsive.

    Returns a dict with title/artist/file_path/platform, or None on failure.
    """
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, _run_extract, url, output_dir)
    except Exception as e:
        logger.error(f"yt-dlp extraction failed for {url}: {e}")
        return None
