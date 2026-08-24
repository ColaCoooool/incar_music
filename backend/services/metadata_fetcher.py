"""Metadata fetcher service.

Fetches missing metadata (lyrics, cover art, album info, artist info)
from various online sources.
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Optional

import httpx
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.album import Album
from models.artist import Artist
from models.cover import CoverArt
from models.lyrics import Lyrics
from models.song import Song

logger = logging.getLogger(__name__)

# Netease Cloud Music API (unofficial)
NETEASE_SEARCH_URL = "https://music.163.com/api/search/get"
NETEASE_SONG_URL = "https://music.163.com/api/song/detail"
NETEASE_LYRIC_URL = "https://music.163.com/api/song/lyric"

# MusicBrainz API
MUSICBRAINZ_SEARCH_URL = "https://musicbrainz.org/ws/2/recording"
MUSICBRAINZ_COVER_URL = "https://coverartarchive.org/release-group"

# QQ Music API (unofficial)
QQ_SEARCH_URL = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"


class MetadataFetcher:
    """Fetches metadata from various online sources."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "InCarMusic/0.1 (https://github.com/ColaCoooool/incar_music)"
            },
        )

    async def close(self):
        await self.client.aclose()

    # ─── Lyrics ───────────────────────────────────────────────────────

    async def fetch_lyrics_from_netease(self, song_name: str, artist_name: str) -> Optional[str]:
        """Fetch lyrics from Netease Cloud Music."""
        try:
            # Search for the song
            params = {"s": f"{song_name} {artist_name}", "type": 1, "limit": 5}
            resp = await self.client.post(NETEASE_SEARCH_URL, data=params)
            resp.raise_for_status()
            data = resp.json()

            if not data.get("result", {}).get("songs"):
                return None

            song_id = data["result"]["songs"][0]["id"]

            # Get lyrics
            params = {"id": song_id, "lv": 1, "tv": 1}
            resp = await self.client.get(NETEASE_LYRIC_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            lrc = data.get("lrc", {}).get("lyric", "")
            return lrc if lrc else None

        except Exception as e:
            logger.warning(f"Netease lyrics fetch failed for '{song_name}': {e}")
            return None

    async def fetch_lyrics_from_qq(self, song_name: str, artist_name: str) -> Optional[str]:
        """Fetch lyrics from QQ Music."""
        try:
            params = {
                "w": f"{song_name} {artist_name}",
                "format": "json",
                "p": 1,
                "n": 5,
            }
            resp = await self.client.get(QQ_SEARCH_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            songs = data.get("data", {}).get("song", {}).get("list", [])
            if not songs:
                return None

            song_mid = songs[0].get("songmid", "")
            if not song_mid:
                return None

            # Get lyrics
            lyric_url = f"https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg"
            resp = await self.client.get(
                lyric_url,
                params={"songmid": song_mid, "format": "json"},
                headers={"Referer": "https://y.qq.com/"},
            )
            resp.raise_for_status()
            data = resp.json()

            import base64
            lrc = data.get("lyric", "")
            if lrc:
                return base64.b64decode(lrc).decode("utf-8")
            return None

        except Exception as e:
            logger.warning(f"QQ lyrics fetch failed for '{song_name}': {e}")
            return None

    async def fetch_lyrics(self, song: Song) -> Optional[str]:
        """Fetch lyrics from the best available source."""
        artist_name = ""
        if song.artist_id:
            artist_result = await self.db.execute(select(Artist).where(Artist.id == song.artist_id))
            artist = artist_result.scalar_one_or_none()
            if artist:
                artist_name = artist.name

        # Try sources in order
        lrc = await self.fetch_lyrics_from_netease(song.title, artist_name)
        if not lrc:
            lrc = await self.fetch_lyrics_from_qq(song.title, artist_name)

        if lrc:
            # Determine if synced (has timestamps)
            is_synced = bool(re.search(r"\[\d{2}:\d{2}\.\d{2,3}\]", lrc))

            lyrics = Lyrics(
                song_id=song.id,
                content=lrc,
                format="lrc",
                language="zh",
                is_synced=is_synced,
                source="netease" if not lrc.startswith("[") else "qq",
            )
            self.db.add(lyrics)
            song.has_lyrics = True
            await self.db.flush()
            return lrc

        return None

    # ─── Cover Art ────────────────────────────────────────────────────

    async def fetch_cover_from_netease(
        self, song_name: str, artist_name: str
    ) -> Optional[str]:
        """Fetch album cover from Netease Cloud Music."""
        try:
            params = {"s": f"{song_name} {artist_name}", "type": 1, "limit": 5}
            resp = await self.client.post(NETEASE_SEARCH_URL, data=params)
            resp.raise_for_status()
            data = resp.json()

            songs = data.get("result", {}).get("songs", [])
            if not songs:
                return None

            # Get album cover URL
            album = songs[0].get("album", {})
            pic_url = album.get("picUrl", "")
            if pic_url:
                return pic_url

            return None

        except Exception as e:
            logger.warning(f"Netease cover fetch failed for '{song_name}': {e}")
            return None

    async def fetch_cover_from_musicbrainz(
        self, song_name: str, artist_name: str
    ) -> Optional[str]:
        """Fetch album cover from MusicBrainz Cover Art Archive."""
        try:
            # Search for recording
            params = {
                "query": f'"{song_name}" AND artist:"{artist_name}"',
                "fmt": "json",
                "limit": 5,
            }
            resp = await self.client.get(MUSICBRAINZ_SEARCH_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            recordings = data.get("recordings", [])
            if not recordings:
                return None

            # Get release group
            releases = recordings[0].get("releases", [])
            if not releases:
                return None

            release = releases[0]
            release_group_id = release.get("release-group", {}).get("id")
            if not release_group_id:
                return None

            # Get cover art
            cover_url = f"{MUSICBRAINZ_COVER_URL}/{release_group_id}/front-500"
            resp = await self.client.head(cover_url, follow_redirects=True)
            if resp.status_code == 200:
                return cover_url

            return None

        except Exception as e:
            logger.warning(f"MusicBrainz cover fetch failed for '{song_name}': {e}")
            return None

    async def fetch_cover(self, song: Song) -> Optional[str]:
        """Fetch album cover and save to disk."""
        artist_name = ""
        if song.artist_id:
            artist_result = await self.db.execute(select(Artist).where(Artist.id == song.artist_id))
            artist = artist_result.scalar_one_or_none()
            if artist:
                artist_name = artist.name

        # Try sources in order
        cover_url = await self.fetch_cover_from_netease(song.title, artist_name)
        if not cover_url:
            cover_url = await self.fetch_cover_from_musicbrainz(song.title, artist_name)

        if cover_url:
            # Download and save
            try:
                resp = await self.client.get(cover_url, follow_redirects=True)
                resp.raise_for_status()

                # Determine format
                content_type = resp.headers.get("content-type", "")
                fmt = "jpg"
                if "png" in content_type:
                    fmt = "png"

                # Save file
                cover_filename = f"{song.id}.{fmt}"
                cover_path = settings.cover_path / cover_filename
                cover_path.write_bytes(resp.content)

                # Resize if too large
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

                # Create cover record
                cover = CoverArt(
                    song_id=song.id,
                    file_path=str(cover_path),
                    source_url=cover_url,
                    source="netease" if "163.com" in cover_url else "musicbrainz",
                    width=img.size[0] if img else 0,
                    height=img.size[1] if img else 0,
                    format=fmt,
                )
                self.db.add(cover)
                song.has_cover = True
                await self.db.flush()
                return str(cover_path)

            except Exception as e:
                logger.warning(f"Failed to download cover for '{song.title}': {e}")

        return None

    # ─── Artist Info ──────────────────────────────────────────────────

    async def fetch_artist_info(self, artist: Artist) -> dict:
        """Fetch artist biography and avatar from online sources."""
        info = {"biography": "", "avatar_url": ""}

        try:
            # Try MusicBrainz
            params = {
                "query": f'"{artist.name}"',
                "fmt": "json",
                "limit": 1,
            }
            resp = await self.client.get(
                "https://musicbrainz.org/ws/2/artist", params=params
            )
            resp.raise_for_status()
            data = resp.json()

            artists = data.get("artists", [])
            if artists:
                artist_data = artists[0]
                artist.musicbrainz_id = artist_data.get("id", "")

                # Get disambiguation as biography
                info["biography"] = artist_data.get("disambiguation", "")

        except Exception as e:
            logger.warning(f"Artist info fetch failed for '{artist.name}': {e}")

        return info

    # ─── Batch Processing ─────────────────────────────────────────────

    async def fill_missing_metadata(self, song_ids: Optional[list[int]] = None) -> dict:
        """Fill missing metadata for songs that lack lyrics/covers.

        Args:
            song_ids: Specific song IDs to process. If None, processes all songs missing data.
        """
        stats = {"lyrics_found": 0, "covers_found": 0, "errors": 0}

        if song_ids:
            result = await self.db.execute(select(Song).where(Song.id.in_(song_ids)))
        else:
            result = await self.db.execute(
                select(Song).where(Song.has_lyrics == False)  # noqa: E712
            )

        songs = result.scalars().all()

        for song in songs:
            try:
                # Fetch lyrics if missing
                if not song.has_lyrics:
                    lrc = await self.fetch_lyrics(song)
                    if lrc:
                        stats["lyrics_found"] += 1

                # Fetch cover if missing
                if not song.has_cover:
                    cover_path = await self.fetch_cover(song)
                    if cover_path:
                        stats["covers_found"] += 1

                # Small delay to be nice to APIs
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Error fetching metadata for song {song.id}: {e}")
                stats["errors"] += 1

        await self.db.commit()
        return stats
