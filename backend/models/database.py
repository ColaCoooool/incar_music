"""Database connection and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables and apply lightweight migrations."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate)


def _migrate(sync_conn):
    """Add columns introduced after the initial release (SQLite-safe)."""
    from sqlalchemy import inspect, text

    inspector = inspect(sync_conn)
    if "songs" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("songs")}
        if "source_url" not in cols:
            sync_conn.execute(
                text("ALTER TABLE songs ADD COLUMN source_url VARCHAR(2000)")
            )
