"""Song model."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.database import Base

if TYPE_CHECKING:
    from models.album import Album
    from models.artist import Artist
    from models.cover import CoverArt
    from models.genre import Genre
    from models.lyrics import Lyrics


class Song(Base):
    __tablename__ = "songs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(2000), nullable=False, unique=True)
    relative_path: Mapped[Optional[str]] = mapped_column(String(2000))

    # Audio properties
    duration: Mapped[Optional[float]] = mapped_column(Float)  # seconds
    format: Mapped[Optional[str]] = mapped_column(String(20))  # mp3, flac, wav, etc.
    bitrate: Mapped[Optional[int]] = mapped_column(Integer)  # kbps
    sample_rate: Mapped[Optional[int]] = mapped_column(Integer)  # Hz
    channels: Mapped[Optional[int]] = mapped_column(Integer)
    file_size: Mapped[Optional[int]] = mapped_column(Integer)  # bytes

    # Metadata
    year: Mapped[Optional[int]] = mapped_column(Integer)
    track_number: Mapped[Optional[int]] = mapped_column(Integer)
    disc_number: Mapped[Optional[int]] = mapped_column(Integer)
    comment: Mapped[Optional[str]] = mapped_column(Text)

    # Source (scraped songs)
    source_url: Mapped[Optional[str]] = mapped_column(String(2000))

    # Status
    has_lyrics: Mapped[bool] = mapped_column(default=False)
    has_cover: Mapped[bool] = mapped_column(default=False)
    metadata_complete: Mapped[bool] = mapped_column(default=False)

    # Play count
    play_count: Mapped[int] = mapped_column(Integer, default=0)
    last_played: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Timestamps
    date_added: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    date_modified: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Foreign keys
    artist_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("artists.id"))
    album_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("albums.id"))
    genre_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("genres.id"))

    # Relationships
    artist: Mapped[Optional["Artist"]] = relationship(back_populates="songs")
    album: Mapped[Optional["Album"]] = relationship(back_populates="songs")
    genre: Mapped[Optional["Genre"]] = relationship(back_populates="songs")
    lyrics: Mapped[Optional["Lyrics"]] = relationship(back_populates="song", uselist=False)
    cover: Mapped[Optional["CoverArt"]] = relationship(back_populates="song", uselist=False)

    def __repr__(self) -> str:
        return f"<Song(id={self.id}, title='{self.title}', artist='{self.artist}')>"
