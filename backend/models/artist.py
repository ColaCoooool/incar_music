"""Artist model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.database import Base

if TYPE_CHECKING:
    from models.song import Song


class Artist(Base):
    __tablename__ = "artists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    name_pinyin: Mapped[str] = mapped_column(String(500), default="")
    biography: Mapped[str] = mapped_column(Text, default="")
    avatar_url: Mapped[str] = mapped_column(String(2000), default="")
    musicbrainz_id: Mapped[str] = mapped_column(String(100), default="")

    # Timestamps
    date_added: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    songs: Mapped[list["Song"]] = relationship(back_populates="artist")

    def __repr__(self) -> str:
        return f"<Artist(id={self.id}, name='{self.name}')>"
