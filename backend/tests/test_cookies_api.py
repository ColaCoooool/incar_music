"""Regression tests for the cookies upload/status/delete API."""
from pathlib import Path

import pytest


def _stub_cookies(monkeypatch, configured: bool, path: Path = None):
    """Isolate the status endpoint from any real cookies.txt uploaded manually."""
    from scrapers import ytdlp

    if configured:
        monkeypatch.setattr(ytdlp, "cookies_file_path", lambda: path)
    else:
        monkeypatch.setattr(ytdlp, "cookies_file_path", lambda: None)


@pytest.fixture()
def cookie_target(tmp_path, monkeypatch):
    from core.config import settings

    target = tmp_path / "cookies.txt"
    monkeypatch.setattr(settings, "YTDLP_COOKIES_FILE", str(target))
    return target


def test_cookies_status_not_configured(client, cookie_target, monkeypatch):
    _stub_cookies(monkeypatch, configured=False)
    r = client.get("/api/scraper/cookies")
    assert r.status_code == 200
    assert r.json() == {"configured": False}


def test_upload_cookies(client, cookie_target, monkeypatch):
    content = "# Netscape HTTP Cookie File\n.douyin.com\tTRUE\t/\tTRUE\t0\tsessionid\txyz\n"
    r = client.post(
        "/api/scraper/cookies",
        files={"file": ("cookies.txt", content.encode(), "text/plain")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["configured"] is True

    assert cookie_target.exists()
    assert ".douyin.com" in cookie_target.read_text(encoding="utf-8")

    # Status now reports configured
    _stub_cookies(monkeypatch, configured=True, path=cookie_target)
    assert client.get("/api/scraper/cookies").json() == {"configured": True}


def test_upload_cookies_rejects_oversized(client, cookie_target):
    r = client.post(
        "/api/scraper/cookies",
        files={"file": ("cookies.txt", b"a" * (2 * 1024 * 1024), "text/plain")},
    )
    assert r.status_code == 400


def test_delete_cookies(client, cookie_target, monkeypatch):
    client.post(
        "/api/scraper/cookies",
        files={"file": ("cookies.txt", b"# Netscape\n.douyin.com\tTRUE\n", "text/plain")},
    )
    r = client.delete("/api/scraper/cookies")
    assert r.status_code == 200
    assert r.json() == {"configured": False}
    assert not cookie_target.exists()

    _stub_cookies(monkeypatch, configured=False)
    assert client.get("/api/scraper/cookies").json() == {"configured": False}


def test_ytdlp_uses_uploaded_cookies_file(tmp_path, monkeypatch):
    """yt-dlp opts must pick up the cookies file when configured."""
    from core.config import settings
    from scrapers import ytdlp

    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text("# Netscape\n")

    monkeypatch.setattr(settings, "YTDLP_COOKIES_FILE", str(cookie_file))

    import asyncio

    class FakeYDL:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def extract_info(self, url, download=False):
            return {"title": "t", "requested_downloads": []}

        def download(self, urls):
            (tmp_path / "t.m4a").write_bytes(b"x")

    class _FakeYDLClass:
        def __init__(self, opts):
            self.opts = opts
            FakeYDL.opts = opts

        def __enter__(self):
            return FakeYDL(self.opts)

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(ytdlp.yt_dlp, "YoutubeDL", _FakeYDLClass)

    asyncio.run(ytdlp.extract_audio("https://www.douyin.com/video/1", tmp_path))
    assert FakeYDL.opts.get("cookiefile") == str(cookie_file)
