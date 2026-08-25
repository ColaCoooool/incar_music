"""Regression tests for lyrics (fetch with existing lyrics must not 500)."""
from conftest import scan


def test_fetch_lyrics_with_existing_lyrics(client, music_library, monkeypatch):
    """POST /api/lyrics/{id}/fetch must not crash when lyrics already exist."""
    scan(client)
    song = next(s for s in client.get("/api/songs/").json() if s["title"] == "山丘")

    client.put(
        f"/api/lyrics/{song['id']}",
        json={"content": "[00:01.00]已有的歌词", "format": "lrc"},
    )

    # Offline-safe: stub the online sources so the test does not depend on network
    from services import metadata_fetcher

    async def fake_fetch_lyrics_from_netease(*a, **k):
        return "[00:02.00]在线歌词\n[00:03.00]第二行"

    monkeypatch.setattr(
        metadata_fetcher.MetadataFetcher, "fetch_lyrics_from_netease", fake_fetch_lyrics_from_netease
    )

    r = client.post(f"/api/lyrics/{song['id']}/fetch")
    assert r.status_code == 200, r.text
    assert "在线歌词" in r.json().get("content", "")

    # The stored lyrics were updated, not duplicated
    stored = client.get(f"/api/lyrics/{song['id']}").json()
    assert "在线歌词" in stored["content"]
