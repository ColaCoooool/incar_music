"""Regression test: init_db must migrate databases created before the source_url column."""
import sqlite3

from models.database import init_db


async def test_init_db_adds_source_url_column(tmp_path, client):
    """An existing database from the initial release (no source_url) must be migrated."""
    import os

    db_path = "data/test_pytest.db"

    # Simulate the original schema: drop the songs table and recreate it without source_url
    conn = sqlite3.connect(db_path)
    conn.execute("DROP TABLE IF EXISTS songs")
    conn.execute(
        """CREATE TABLE songs (
            id INTEGER NOT NULL PRIMARY KEY,
            title VARCHAR(500) NOT NULL,
            file_path VARCHAR(2000) NOT NULL UNIQUE,
            relative_path VARCHAR(2000),
            duration FLOAT,
            format VARCHAR(20),
            bitrate INTEGER,
            sample_rate INTEGER,
            channels INTEGER,
            file_size INTEGER,
            year INTEGER,
            track_number INTEGER,
            disc_number INTEGER,
            comment TEXT,
            has_lyrics BOOLEAN,
            has_cover BOOLEAN,
            metadata_complete BOOLEAN,
            play_count INTEGER,
            last_played DATETIME,
            date_added DATETIME,
            date_modified DATETIME,
            artist_id INTEGER,
            album_id INTEGER,
            genre_id INTEGER
        )"""
    )
    conn.commit()
    conn.close()

    await init_db()

    conn = sqlite3.connect(db_path)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(songs)")}
    conn.close()
    assert "source_url" in cols, f"source_url column missing after migration: {cols}"
