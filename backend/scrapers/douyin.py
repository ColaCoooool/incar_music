"""Douyin scraper.

Extracts audio from Douyin (TikTok China) videos.
"""

import logging
import re
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


def extract_douyin_id(url: str) -> Optional[str]:
    """Extract video ID from a Douyin URL."""
    patterns = [
        r"douyin\.com/video/(\d+)",
        r"douyin\.com/note/(\d+)",
        r"v\.douyin\.com/[\w]+",
        r"(?<!\w)(\d{19,})(?!\w)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


class DouyinScraper:
    """Scrapes audio from Douyin videos."""

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
            },
            follow_redirects=True,
        )

    async def close(self):
        await self.client.aclose()

    async def resolve_short_url(self, url: str) -> str:
        """Resolve a short URL (v.douyin.com) to the full URL."""
        try:
            resp = await self.client.head(url)
            return str(resp.url)
        except Exception:
            return url

    async def get_video_info(self, url: str) -> Optional[dict]:
        """Get video metadata from Douyin."""
        try:
            # Resolve short URL if needed
            if "v.douyin.com" in url:
                url = await self.resolve_short_url(url)

            # Extract video ID
            video_id = extract_douyin_id(url)
            if not video_id:
                return None

            # Fetch page HTML for metadata
            resp = await self.client.get(url)
            resp.raise_for_status()
            html = resp.text

            # Try to extract JSON data from page
            # Douyin embeds video data in a script tag
            json_match = re.search(r'window\._ROUTER_DATA\s*=\s*({.*?})\s*</script>', html, re.DOTALL)
            if json_match:
                import json
                try:
                    data = json.loads(json_match.group(1))
                    # Extract relevant info
                    return {
                        "title": data.get("title", ""),
                        "author": data.get("author", {}).get("nickname", ""),
                        "cover": data.get("cover", {}).get("url_list", [""])[0],
                        "duration": data.get("duration", 0),
                        "video_id": video_id,
                    }
                except json.JSONDecodeError:
                    pass

            # Fallback: basic info from URL
            return {
                "title": f"Douyin Video {video_id}",
                "author": "",
                "cover": "",
                "duration": 0,
                "video_id": video_id,
            }

        except Exception as e:
            logger.error(f"Failed to get Douyin video info: {e}")
            return None

    async def get_audio_url(self, url: str) -> Optional[str]:
        """Get audio stream URL from a Douyin video."""
        try:
            if "v.douyin.com" in url:
                url = await self.resolve_short_url(url)

            video_id = extract_douyin_id(url)
            if not video_id:
                return None

            # Note: Douyin's anti-scraping is aggressive
            # This is a best-effort approach
            resp = await self.client.get(url)
            resp.raise_for_status()
            html = resp.text

            # Look for video URL in page source
            video_url_match = re.search(r'"playApi":"([^"]+)"', html)
            if video_url_match:
                video_url = video_url_match.group(1).replace("\\u002F", "/")
                return video_url

            return None

        except Exception as e:
            logger.error(f"Failed to get Douyin audio URL: {e}")
            return None

    async def download_audio(
        self, url: str, output_path: str
    ) -> Optional[dict]:
        """Download audio from a Douyin video.

        Returns metadata dict or None on failure.
        """
        audio_url = await self.get_audio_url(url)
        if not audio_url:
            return None

        try:
            resp = await self.client.get(audio_url, follow_redirects=True)
            resp.raise_for_status()

            # Save as mp4 (Douyin uses mp4 container)
            output = f"{output_path}.mp4"
            with open(output, "wb") as f:
                f.write(resp.content)

            # Get metadata
            info = await self.get_video_info(url)

            return {
                "file_path": output,
                "title": info["title"] if info else "",
                "artist": info["author"] if info else "",
                "source": "douyin",
                "url": url,
            }

        except Exception as e:
            logger.error(f"Failed to download Douyin audio: {e}")
            return None
