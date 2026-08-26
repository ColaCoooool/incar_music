"""Regression tests for browser-unsupported codecs (ALAC m4a, etc.)."""
import asyncio
from pathlib import Path

from models.database import async_session
from models.song import Song
from services import streamer

DATA = Path(__file__).resolve().parent / "data"


def test_needs_browser_transcode_detects_alac():
    """ALAC-encoded m4a cannot be decoded by browsers and must be transcoded."""
    assert streamer.needs_browser_transcode(str(DATA / "alac.m4a")) is True


def test_needs_browser_transcode_allows_aac_m4a():
    """Ordinary AAC m4a plays natively in browsers; no transcode needed."""
    assert streamer.needs_browser_transcode(str(DATA / "aac.m4a")) is False


def test_stream_alac_serves_transcoded_copy(client, monkeypatch, tmp_path):
    """The direct stream endpoint must serve the transcoded AAC copy for ALAC."""
    src = str(DATA / "alac.m4a")
    fake = tmp_path / "song_transcoded.m4a"
    fake.write_bytes(b"fake aac content")

    async def _insert_song() -> int:
        async with async_session() as db:
            song = Song(title="斗牛", file_path=src, relative_path="alac.m4a", format="m4a")
            db.add(song)
            await db.commit()
            await db.refresh(song)
            return song.id

    song_id = asyncio.run(_insert_song())

    async def _need(_path: str) -> bool:
        return True

    async def _transcode(_path: str, _song_id: int) -> str:
        return str(fake)

    monkeypatch.setattr(streamer, "needs_browser_transcode", _need)
    monkeypatch.setattr(streamer, "transcode_for_browser", _transcode)

    r = client.get(f"/api/stream/{song_id}")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/mp4")
    assert r.content == b"fake aac content"
