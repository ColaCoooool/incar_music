"""Regression tests for scrapers (regex group, str division, source_url kwarg)."""
from pathlib import Path

from conftest import scan


def test_extract_douyin_id_short_url():
    """Short douyin URLs must not raise IndexError (regex capture group bug)."""
    from scrapers.douyin import extract_douyin_id

    vid = extract_douyin_id("https://v.douyin.com/AbCdEfG/")
    assert vid is None or isinstance(vid, str)  # must not raise


def test_extract_douyin_id_normal_url():
    from scrapers.douyin import extract_douyin_id

    assert extract_douyin_id("https://www.douyin.com/video/7123456789012345678") == "7123456789012345678"


def test_extract_bvid():
    from scrapers.bilibili import extract_bvid

    assert extract_bvid("https://www.bilibili.com/video/BV1GJ411x7h7") == "BV1GJ411x7h7"


def _mock_scraper(monkeypatch, library_root: Path):
    """Replace network calls with canned responses that write a real file."""
    from scrapers import bilibili, douyin

    out = library_root / "_scraped" / "bilibili" / "test.m4a"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(b"fakem4a")

    info = {
        "title": "测试歌曲",
        "description": "d",
        "owner": "UP主",
        "cover": "",
        "duration": 10,
        "cid": 1,
        "aid": 1,
        "bvid": "BV1GJ411x7h7",
    }

    async def fake_get_video_info(self, bvid):
        return info

    async def fake_download_audio(self, bvid, output_path):
        Path(output_path + ".m4a").write_bytes(b"fakem4a")
        return {"file_path": str(out), "title": info["title"], "artist": info["owner"]}

    async def fake_close(self):
        pass

    monkeypatch.setattr(bilibili.BilibiliScraper, "get_video_info", fake_get_video_info)
    monkeypatch.setattr(bilibili.BilibiliScraper, "download_audio", fake_download_audio)
    monkeypatch.setattr(bilibili.BilibiliScraper, "close", fake_close)
    return out


def test_scrape_bilibili_flow(client, music_library, monkeypatch):
    """The bilibili scrape endpoint must work end-to-end (no TypeError)."""
    _mock_scraper(monkeypatch, music_library)
    scan(client)
    before = client.get("/api/songs/count").json()["count"]

    r = client.post(
        "/api/scraper/bilibili",
        json={"url": "https://www.bilibili.com/video/BV1GJ411x7h7"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["song_id"] > 0
    assert client.get("/api/songs/count").json()["count"] == before + 1

    detail = client.get(f"/api/songs/{data['song_id']}").json()
    assert detail["title"] == "测试歌曲"
