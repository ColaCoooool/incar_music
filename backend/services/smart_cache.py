"""Smart cache service.

Manages offline caching with predictive pre-caching and LRU eviction.
"""

import logging
import shutil
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.song import Song

logger = logging.getLogger(__name__)


class SmartCache:
    """Manages audio file caching for offline playback."""

    def __init__(self):
        self.cache_dir = settings.cache_path
        self.max_cache_bytes = settings.MAX_CACHE_SIZE_MB * 1024 * 1024
        self._cache_index: OrderedDict[int, Path] = OrderedDict()

    def _get_cache_path(self, song_id: int, extension: str = ".mp3") -> Path:
        """Get cache file path for a song."""
        return self.cache_dir / f"cached_{song_id}{extension}"

    def _current_cache_size(self) -> int:
        """Calculate current cache size in bytes."""
        total = 0
        if self.cache_dir.exists():
            for f in self.cache_dir.iterdir():
                if f.is_file():
                    total += f.stat().st_size
        return total

    def _evict_lru(self, needed_bytes: int = 0):
        """Evict least recently used cache entries until we have space."""
        while self._cache_index and self._current_cache_size() + needed_bytes > self.max_cache_bytes:
            song_id, path = self._cache_index.popitem(last=False)
            if path.exists():
                path.unlink()
                logger.info(f"Evicted cached file for song {song_id}")

    async def cache_song(self, db: AsyncSession, song_id: int) -> Optional[str]:
        """Cache a song for offline playback."""
        result = await db.execute(select(Song).where(Song.id == song_id))
        song = result.scalar_one_or_none()
        if not song:
            return None

        source_path = Path(song.file_path)
        if not source_path.exists():
            return None

        cache_path = self._get_cache_path(song_id, source_path.suffix)

        if cache_path.exists():
            self._cache_index[song_id] = cache_path
            self._cache_index.move_to_end(song_id)
            return str(cache_path)

        # Check if we need to evict
        needed = source_path.stat().st_size
        self._evict_lru(needed)

        try:
            shutil.copy2(str(source_path), str(cache_path))
            self._cache_index[song_id] = cache_path
            logger.info(f"Cached song {song_id}: {source_path.name}")
            return str(cache_path)
        except Exception as e:
            logger.error(f"Failed to cache song {song_id}: {e}")
            return None

    async def get_cached(self, song_id: int) -> Optional[str]:
        """Get cached file path if it exists."""
        # Check in-memory index first
        if song_id in self._cache_index:
            path = self._cache_index[song_id]
            if path.exists():
                self._cache_index.move_to_end(song_id)
                return str(path)
            del self._cache_index[song_id]

        # Check on disk
        for ext in [".mp3", ".flac", ".wav", ".aac", ".m4a", ".ogg", ".opus"]:
            p = self._get_cache_path(song_id, ext)
            if p.exists():
                self._cache_index[song_id] = p
                self._cache_index.move_to_end(song_id)
                return str(p)

        return None

    async def predict_and_pre_cache(self, db: AsyncSession, current_song_id: int) -> list[int]:
        """Predict songs to pre-cache based on play history.

        Simple strategy: cache the next N most-played songs
        that aren't already cached.
        """
        PRE_CACHE_COUNT = 5

        # Get most played songs not yet cached
        result = await db.execute(
            select(Song)
            .where(Song.id != current_song_id)
            .order_by(Song.play_count.desc())
            .limit(PRE_CACHE_COUNT * 2)
        )
        candidates = result.scalars().all()

        cached = []
        for song in candidates:
            if len(cached) >= PRE_CACHE_COUNT:
                break
            if await self.get_cached(song.id):
                continue
            path = await self.cache_song(db, song.id)
            if path:
                cached.append(song.id)

        return cached

    async def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        total_size = self._current_cache_size()
        file_count = len(list(self.cache_dir.glob("cached_*"))) if self.cache_dir.exists() else 0

        return {
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 1),
            "max_size_mb": settings.MAX_CACHE_SIZE_MB,
            "usage_percent": round(total_size / self.max_cache_bytes * 100, 1) if self.max_cache_bytes else 0,
            "file_count": file_count,
            "index_count": len(self._cache_index),
        }

    async def clear_cache(self):
        """Clear all cached files."""
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_index.clear()
        logger.info("Cache cleared")


# Singleton
smart_cache = SmartCache()
