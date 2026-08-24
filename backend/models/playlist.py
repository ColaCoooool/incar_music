"""Playlist models."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.database import Base

if TYPE_CHECKING:
    from models.song import Song


class Playlist(Base):
    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(500), default="")
    is_smart: Mapped[bool] = mapped_column(default=False)  # 智能播放列表
    smart_rule: Mapped[str] = mapped_column(String(1000), default="")  # JSON rule

    date_added: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    date_modified: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    songs: Mapped[list["PlaylistSong"]] = relationship(
        back_populates="playlist", order_by="PlaylistSong.position"
    )

    def __repr__(self) -> str:
        return f"<Playlist(id={self.id}, name='{self.name}')>"


class PlaylistSong(Base):
    __tablename__ = "playlist_songs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    playlist_id: Mapped[int] = mapped_column(Integer, ForeignKey("playlists.id"))
    song_id: Mapped[int] = mapped_column(Integer, ForeignKey("songs.id"))
    position: Mapped[int] = mapped_column(Integer, default=0)
    date_added: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    playlist: Mapped["Playlist"] = relationship(back_populates="songs")
    song: Mapped["Song"] = relationship()

    def __repr__(self) -> str:
        return f"<PlaylistSong(playlist_id={self.playlist_id}, song_id={self.song_id})>"
