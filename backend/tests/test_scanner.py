"""Regression tests for the scanner (metadata extraction, force scan, album scoping)."""
from pathlib import Path

import pytest

from conftest import scan


def test_wav_metadata_extraction(music_library):
    """WAV files with ID3 tags must yield title/artist/album/genre, not filename stems."""
    from services.scanner import extract_metadata

    meta = extract_metadata(music_library / "周杰伦" / "依然范特西" / "t1.wav")
    assert meta["title"] == "夜的第七章", f"title was {meta['title']!r}"
    assert meta["artist"] == "周杰伦"
    assert meta["album"] == "依然范特西"
    assert meta["genre"] == "流行"
    assert meta["year"] == 2006


def test_scan_populates_artist_album_genre(client, music_library):
    """After a scan, songs carry artist/album/genre and stats are populated."""
    r = scan(client)
    assert r.status_code == 200, r.text

    stats = client.get("/api/library/stats").json()
    assert stats["total_songs"] == 5  # 5 tagged wavs, garbage mp3 skipped
    assert stats["total_artists"] == 3  # 周杰伦, Adele, 李宗盛
    assert stats["total_albums"] == 4  # 依然范特西, 21, 同名专辑x2

    songs = client.get("/api/songs/").json()
    by_title = {s["title"]: s for s in songs}
    assert by_title["夜的第七章"]["artist_name"] == "周杰伦"
    assert by_title["Rolling in the Deep"]["genre_name"] == "Pop"


def test_scan_supports_python311_without_path_walk(client, music_library, monkeypatch):
    """Regression: scan must run on Python 3.11, where Path.walk() does not exist.

    The container image uses python:3.11-slim; Path.walk was added in 3.12 and
    crashes the scan with AttributeError: 'PosixPath' object has no attribute 'walk'.
    """
    from pathlib import Path as PathCls

    # Simulate the Python 3.11 runtime where Path.walk is absent.
    monkeypatch.delattr(PathCls, "walk", raising=False)

    r = scan(client)
    assert r.status_code == 200, r.text
    assert client.get("/api/library/stats").json()["total_songs"] == 5


def test_scan_finds_music_in_nested_subdirectories(client, music_library):
    """Music scattered across subfolders (not only the library root) must be discovered."""
    r = scan(client)
    assert r.status_code == 200, r.text

    songs = client.get("/api/songs/").json()
    by_title = {s["title"]: s["file_path"] for s in songs}

    assert "依然范特西" in by_title["夜的第七章"]
    assert "21" in by_title["Rolling in the Deep"]


def test_garbage_file_skipped(client, music_library):
    """Unparseable audio files must not be added to the library."""
    scan(client)
    songs = client.get("/api/songs/").json()
    assert all(s["title"] != "broken" for s in songs)


def test_force_rescan_is_idempotent(client, music_library):
    """force=true must update existing songs instead of crashing with UNIQUE violations."""
    r1 = scan(client)
    assert r1.status_code == 200, r1.text
    count_after_first = client.get("/api/songs/count").json()["count"]

    r2 = scan(client, force=True)
    assert r2.status_code == 200, r2.text
    count_after_force = client.get("/api/songs/count").json()["count"]
    assert count_after_force == count_after_first == 5


def test_album_scoping_by_artist(client, music_library):
    """Two artists with the same album title must each keep their own album."""
    scan(client)
    albums = client.get("/api/library/albums").json()
    same_named = [a for a in albums if a["title"] == "同名专辑"]
    assert len(same_named) == 2, f"expected 2 distinct 同名专辑 albums, got {albums}"

    for a in same_named:
        detail = client.get(f"/api/library/albums/{a['id']}").json()
        song_artists = {s["artist_name"] for s in detail["songs"]}
        assert len(song_artists) == 1, f"album {a['id']} mixes artists: {song_artists}"
