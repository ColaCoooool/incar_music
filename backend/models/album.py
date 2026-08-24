"""Album model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.database import Base

if TYPE_CHECKING:
    from models.song import Song


class Album(Base):
    __tablename__ = "albums"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    artist_id: Mapped[int] = mapped_column(Integer, ForeignKey("artists.id"))
    year: Mapped[int] = mapped_column(Integer)
    genre: Mapped[str] = mapped_column(String(100), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    musicbrainz_id: Mapped[str] = mapped_column(String(100), default="")

    # Timestamps
    date_added: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    songs: Mapped[list["Song"]] = relationship(back_populates="album")

    def __repr__(self) -> str:
        return f"<Album(id={self.id}, title='{self.title}')>"
