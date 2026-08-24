"""Cover art model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.database import Base

if TYPE_CHECKING:
    from models.song import Song


class CoverArt(Base):
    __tablename__ = "cover_art"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    song_id: Mapped[int] = mapped_column(Integer, ForeignKey("songs.id"), unique=True)
    file_path: Mapped[str] = mapped_column(String(2000), default="")
    source_url: Mapped[str] = mapped_column(String(2000), default="")
    source: Mapped[str] = mapped_column(String(100), default="")  # local, musicbrainz, netease, etc.
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    format: Mapped[str] = mapped_column(String(20), default="jpg")  # jpg, png

    date_added: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    song: Mapped["Song"] = relationship(back_populates="cover")

    def __repr__(self) -> str:
        return f"<CoverArt(id={self.id}, song_id={self.song_id}, source='{self.source}')>"
