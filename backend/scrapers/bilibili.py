"""Bilibili scraper.

Extracts audio from Bilibili videos.
"""

import logging
import re
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

BILIBILI_API = "https://api.bilibili.com/x/web-interface/view"
BILIBILI_PLAY_URL = "https://api.bilibili.com/x/player/playurl"


def extract_bvid(url: str) -> Optional[str]:
    """Extract BV ID from a Bilibili URL."""
    patterns = [
        r"bilibili\.com/video/(BV[\w]+)",
        r"b23\.tv/(BV[\w]+)",
        r"(BV[\w]{10})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


class BilibiliScraper:
    """Scrapes audio from Bilibili videos."""

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.bilibili.com",
            },
        )

    async def close(self):
        await self.client.aclose()

    async def get_video_info(self, bvid: str) -> Optional[dict]:
        """Get video metadata from Bilibili."""
        try:
            resp = await self.client.get(BILIBILI_API, params={"bvid": bvid})
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != 0:
                logger.error(f"Bilibili API error: {data.get('message')}")
                return None

            info = data.get("data", {})
            return {
                "title": info.get("title", ""),
                "description": info.get("desc", ""),
                "owner": info.get("owner", {}).get("name", ""),
                "cover": info.get("pic", ""),
                "duration": info.get("duration", 0),
                "cid": info.get("cid", 0),
                "aid": info.get("aid", 0),
                "bvid": bvid,
            }

        except Exception as e:
            logger.error(f"Failed to get Bilibili video info: {e}")
            return None

    async def get_audio_url(self, bvid: str) -> Optional[str]:
        """Get audio stream URL from a Bilibili video."""
        try:
            # First get video info for cid
            info = await self.get_video_info(bvid)
            if not info:
                return None

            # Get play URL (audio only)
            resp = await self.client.get(
                BILIBILI_PLAY_URL,
                params={
                    "bvid": bvid,
                    "cid": info["cid"],
                    "fnval": 16,  # DASH format
                    "fourk": 1,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != 0:
                return None

            # Get audio stream from DASH
            dash = data.get("data", {}).get("dash", {})
            audio_streams = dash.get("audio", [])

            if audio_streams:
                # Pick highest quality audio
                best = max(audio_streams, key=lambda x: x.get("bandwidth", 0))
                return best.get("baseUrl") or best.get("base_url")

            return None

        except Exception as e:
            logger.error(f"Failed to get Bilibili audio URL: {e}")
            return None

    async def download_audio(
        self, bvid: str, output_path: str
    ) -> Optional[dict]:
        """Download audio from a Bilibili video.

        Returns metadata dict or None on failure.
        """
        audio_url = await self.get_audio_url(bvid)
        if not audio_url:
            return None

        try:
            # Download audio with proper headers
            resp = await self.client.get(
                audio_url,
                headers={
                    "Referer": "https://www.bilibili.com",
                    "User-Agent": "Mozilla/5.0",
                },
                follow_redirects=True,
            )
            resp.raise_for_status()

            # Save as m4a (Bilibili uses DASH audio)
            output = f"{output_path}.m4a"
            with open(output, "wb") as f:
                f.write(resp.content)

            # Get video info for metadata
            info = await self.get_video_info(bvid)

            return {
                "file_path": output,
                "title": info["title"] if info else "",
                "artist": info["owner"] if info else "",
                "source": "bilibili",
                "bvid": bvid,
            }

        except Exception as e:
            logger.error(f"Failed to download Bilibili audio: {e}")
            return None
