"""Application configuration."""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "InCar Music"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/incar_music.db"

    # Music library path (NAS mount point)
    MUSIC_LIBRARY_PATH: str = "/music"

    # Cache settings
    CACHE_DIR: str = "./data/cache"
    MAX_CACHE_SIZE_MB: int = 2048  # 2GB max cache on car device

    # HLS streaming
    HLS_DIR: str = "./data/hls"
    HLS_SEGMENT_DURATION: int = 6  # seconds

    # Transcoding
    TRANSCODE_BITRATES: list[int] = [128, 192, 320]  # kbps options
    DEFAULT_BITRATE: int = 192

    # Redis (optional)
    REDIS_URL: Optional[str] = None

    # Metadata sources
    MUSICBRAINZ_ENABLED: bool = True
    NETEASE_API_ENABLED: bool = True

    # Scraper (yt-dlp)
    # Optional cookies file (Netscape format) for sites requiring login/fresh
    # cookies (e.g. Douyin). Deploy a cookies.txt on the NAS and point here.
    YTDLP_COOKIES_FILE: Optional[str] = None

    # Cover art
    COVER_DIR: str = "./data/covers"
    COVER_MAX_SIZE: int = 600  # pixels

    @property
    def data_dir(self) -> Path:
        p = Path(self.DATABASE_URL.replace("sqlite+aiosqlite:///", "")).parent
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def cache_path(self) -> Path:
        p = Path(self.CACHE_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def hls_path(self) -> Path:
        p = Path(self.HLS_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def cover_path(self) -> Path:
        p = Path(self.COVER_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
