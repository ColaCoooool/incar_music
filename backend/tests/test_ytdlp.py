"""Regression tests for the yt-dlp based scraper (audio-only download)."""
import asyncio

import pytest


class FakeYDL:
    """Minimal fake YoutubeDL that records opts and simulates a download."""

    def __init__(self, opts, fail_extract=False):
        self.opts = opts
        self.fail_extract = fail_extract
        self.calls = {}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def extract_info(self, url, download=False):
        self.calls["url"] = url
        if self.fail_extract:
            raise Exception("network error")
        return {"title": "测试歌曲", "uploader": "UP主", "requested_downloads": []}

    def download(self, urls):
        self.calls["downloaded"] = True
        # simulate the outtmpl producing a real file
        (self.opts["outtmpl"]).replace("%(title).120B.%(ext)s", "x")  # no-op sanity
        import re
        tmpl = self.opts["outtmpl"]
        filename = re.sub(r"%\(title\)\.\d+B\.%\(ext\)s", "测试歌曲.m4a", tmpl)
        open(filename, "wb").write(b"fakeaudio")


def _make_fake(monkeypatch, **kwargs):
    from scrapers import ytdlp

    fake = FakeYDL({}, **kwargs)

    class _FakeYDLClass:
        def __init__(self, opts):
            fake.opts = opts

        def __enter__(self):
            return fake

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(ytdlp.yt_dlp, "YoutubeDL", _FakeYDLClass)
    return fake


async def test_extract_audio_requests_audio_only(tmp_path, monkeypatch):
    """The format selection must request audio streams, never the full video."""
    from scrapers import ytdlp

    fake = _make_fake(monkeypatch)
    result = await ytdlp.extract_audio("https://www.douyin.com/video/123", tmp_path)

    assert fake.calls["downloaded"] is True
    assert "bestaudio" in fake.opts["format"]
    assert result is not None
    assert result["title"] == "测试歌曲"
    assert result["artist"] == "UP主"
    assert result["platform"] == "douyin"
    assert "测试歌曲.m4a" in result["file_path"]
    assert (tmp_path / "测试歌曲.m4a").exists()


async def test_extract_audio_bilibili_platform(tmp_path, monkeypatch):
    from scrapers import ytdlp

    fake = _make_fake(monkeypatch)
    result = await ytdlp.extract_audio("https://www.bilibili.com/video/BV1GJ411x7h7", tmp_path)
    assert result["platform"] == "bilibili"


async def test_extract_audio_failure_returns_none(tmp_path, monkeypatch):
    from scrapers import ytdlp

    _make_fake(monkeypatch, fail_extract=True)
    result = await ytdlp.extract_audio("https://www.douyin.com/video/123", tmp_path)
    assert result is None


async def test_extract_audio_uses_cookies_file_when_configured(tmp_path, monkeypatch):
    """When YTDLP_COOKIES_FILE is set, yt-dlp must receive the cookiefile option."""
    from core.config import settings
    from scrapers import ytdlp

    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text("# Netscape HTTP Cookie File\n")

    monkeypatch.setattr(settings, "YTDLP_COOKIES_FILE", str(cookie_file))
    fake = _make_fake(monkeypatch)

    await ytdlp.extract_audio("https://www.douyin.com/video/123", tmp_path)
    assert fake.opts.get("cookiefile") == str(cookie_file)


async def test_extract_audio_skips_cookies_when_missing(tmp_path, monkeypatch):
    from core.config import settings
    from scrapers import ytdlp

    monkeypatch.setattr(settings, "YTDLP_COOKIES_FILE", str(tmp_path / "nope.txt"))
    fake = _make_fake(monkeypatch)

    await ytdlp.extract_audio("https://www.douyin.com/video/123", tmp_path)
    assert "cookiefile" not in fake.opts


async def test_douyin_endpoint_uses_ytdlp(client, music_library, monkeypatch):
    """POST /api/scraper/douyin must go through the yt-dlp path and store the song."""
    from conftest import scan
    from scrapers import ytdlp

    scan(client)

    async def fake_extract(url, output_dir):
        out = output_dir / "抖音测试.m4a"
        out.write_bytes(b"fakeaudio")
        return {
            "title": "抖音测试",
            "artist": "作者",
            "file_path": str(out),
            "platform": "douyin",
        }

    monkeypatch.setattr(ytdlp, "extract_audio", fake_extract)

    before = client.get("/api/songs/count").json()["count"]
    r = client.post(
        "/api/scraper/douyin",
        json={"url": "https://www.douyin.com/video/7123456789012345678"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["song_id"] > 0
    assert client.get("/api/songs/count").json()["count"] == before + 1

    detail = client.get(f"/api/songs/{data['song_id']}").json()
    assert detail["title"] == "抖音测试"
