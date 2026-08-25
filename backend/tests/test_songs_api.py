"""Regression tests for the songs API (search join, update fields, delete cascade, sort)."""
from conftest import scan


def test_search_joins_artist_no_cartesian(client, music_library):
    """Search must not produce a cartesian product with the artists table."""
    scan(client)

    # Artist-name search returns only that artist's songs
    r = client.get("/api/songs/", params={"search": "周杰伦"})
    assert r.status_code == 200, r.text
    songs = r.json()
    assert len(songs) == 2  # 夜的第七章 + 听妈妈的话
    assert all(s["artist_name"] == "周杰伦" for s in songs)

    # Title search returns exactly one row per match
    r = client.get("/api/songs/", params={"search": "山丘"})
    songs = r.json()
    assert len(songs) == 1
    assert songs[0]["title"] == "山丘"


def test_update_song_all_metadata_fields(client, music_library):
    """PUT must apply artist/album/genre/year, not only title."""
    scan(client)
    song = next(s for s in client.get("/api/songs/").json() if s["title"] == "山丘")

    r = client.put(
        f"/api/songs/{song['id']}",
        json={
            "title": "山丘(重制)",
            "artist_name": "李宗盛",
            "album_title": "山丘专辑",
            "genre_name": "摇滚",
            "year": 2020,
        },
    )
    assert r.status_code == 200, r.text

    detail = client.get(f"/api/songs/{song['id']}").json()
    assert detail["title"] == "山丘(重制)"
    assert detail["artist_name"] == "李宗盛"
    assert detail["album_title"] == "山丘专辑"
    assert detail["genre_name"] == "摇滚"
    assert detail["year"] == 2020


def test_delete_song_with_lyrics_and_cover(client, music_library):
    """Deleting a song with related lyrics/cover must succeed (cascade)."""
    scan(client)
    song = next(s for s in client.get("/api/songs/").json() if s["title"] == "山丘")

    client.put(
        f"/api/lyrics/{song['id']}",
        json={"content": "[00:01.00]山丘", "format": "lrc"},
    )
    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "0000000d49444154789c6200010000000500010d0a2db40000000049454e44ae426082"
    )
    client.post(
        f"/api/covers/{song['id']}/upload",
        files={"file": ("c.png", png, "image/png")},
    )

    r = client.delete(f"/api/songs/{song['id']}")
    assert r.status_code == 200, r.text
    assert client.get(f"/api/songs/{song['id']}").status_code == 404


def test_invalid_sort_by_returns_400(client, music_library):
    """Unvalidated sort_by values must not crash the server."""
    scan(client)
    r = client.get("/api/songs/", params={"sort_by": "__class__"})
    assert r.status_code == 400, r.text
    r = client.get("/api/songs/", params={"sort_by": "artist_name"})
    assert r.status_code in (200, 400)
