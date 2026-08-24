"""Genre model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.database import Base

if TYPE_CHECKING:
    from models.song import Song


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)

    date_added: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    songs: Mapped[list["Song"]] = relationship(back_populates="genre")

    def __repr__(self) -> str:
        return f"<Genre(id={self.id}, name='{self.name}')>"
