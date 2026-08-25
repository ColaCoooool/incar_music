"""Regression tests for streaming (HLS duration type, segment path traversal)."""
from pathlib import Path

from conftest import scan


async def test_create_hls_stream_accepts_str_duration(monkeypatch, tmp_path):
    """ffprobe returns duration as a string; create_hls_stream must coerce it."""
    from services import streamer

    async def fake_audio_info(path):
        return {"format": {"duration": "25.000000"}}

    async def fake_transcode(*a, **k):
        return True

    monkeypatch.setattr(streamer, "get_audio_info", fake_audio_info)
    monkeypatch.setattr(streamer, "transcode_segment", fake_transcode)

    playlist = await streamer.create_hls_stream("fake.mp3", 42, 192)
    assert playlist is not None, "create_hls_stream must handle string durations"
    content = Path(playlist).read_text(encoding="utf-8")
    assert "#EXTM3U" in content
    assert "segment_0000.aac" in content


def test_hls_segment_path_traversal_blocked(client, music_library):
    """HLS segment names must not allow escaping the HLS directory."""
    scan(client)
    # Backslash traversal (Windows) towards the SQLite DB
    r = client.get(
        "/api/stream/6/hls/..%5C..%5C..%5C..%5Cdata%5Ctest_pytest.db"
    )
    assert r.status_code in (400, 404), f"traversal leaked content: {r.status_code}"
    # Plain traversal attempt via encoded slashes (httpx normalizes the URL;
    # either the client strips it or the server rejects it - never DB content)
    r2 = client.get("/api/stream/6/hls/..%2F..%2F..%2F..%2Fdata%2Ftest_pytest.db")
    assert b"SQLite format 3" not in r2.content, "traversal leaked the database file"


def test_hls_segment_valid_name(client, music_library):
    """A well-formed segment name is routed to the segment handler (404 if absent, not 400)."""
    r = client.get("/api/stream/6/hls/segment_0000.aac")
    assert r.status_code == 404  # file does not exist yet, but name is accepted
