"""Regression test: fetch_cover must not NameError when the image payload is invalid."""
from types import SimpleNamespace


async def test_fetch_cover_invalid_image(monkeypatch, client, music_library):
    from services import metadata_fetcher
    from services.metadata_fetcher import MetadataFetcher

    async def fake_fetch_cover_from_netease(self, song_name, artist_name):
        return "http://example.com/cover.png"

    monkeypatch.setattr(
        metadata_fetcher.MetadataFetcher,
        "fetch_cover_from_netease",
        fake_fetch_cover_from_netease,
    )

    class FakeResponse:
        headers = {"content-type": "image/png"}
        content = b"this is definitely not an image"

        def raise_for_status(self):
            return None

    async def fake_get(url, follow_redirects=True):
        return FakeResponse()

    async def fake_aclose():
        pass

    fetcher = MetadataFetcher.__new__(MetadataFetcher)
    fetcher.db = None
    fetcher.client = SimpleNamespace(get=fake_get, aclose=fake_aclose)

    from models.song import Song

    song = Song(id=999, title="x", file_path="/tmp/x.wav")  # no artist -> skips DB query
    result = await fetcher.fetch_cover(song)
    assert result is None  # must not raise NameError / 500
