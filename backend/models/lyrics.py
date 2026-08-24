"""Lyrics model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.database import Base

if TYPE_CHECKING:
    from models.song import Song


class Lyrics(Base):
    __tablename__ = "lyrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    song_id: Mapped[int] = mapped_column(Integer, ForeignKey("songs.id"), unique=True)
    content: Mapped[str] = mapped_column(Text, default="")
    format: Mapped[str] = mapped_column(String(20), default="lrc")  # lrc, txt, srt
    language: Mapped[str] = mapped_column(String(20), default="zh")
    is_synced: Mapped[bool] = mapped_column(default=False)  # 是否带时间戳
    source: Mapped[str] = mapped_column(String(100), default="")  # 来源

    date_added: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    song: Mapped["Song"] = relationship(back_populates="lyrics")

    def __repr__(self) -> str:
        return f"<Lyrics(id={self.id}, song_id={self.song_id}, language='{self.language}')>"
