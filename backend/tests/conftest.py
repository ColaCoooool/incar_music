"""Pytest configuration: isolated env, temp music library, TestClient fixture."""
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

# Must be set BEFORE importing app modules (settings singleton reads env)
os.environ["MUSIC_LIBRARY_PATH"] = str(BACKEND / "test_music_pytest")
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./data/test_pytest.db"
os.environ["CACHE_DIR"] = "./data/test_cache"
os.environ["HLS_DIR"] = "./data/test_hls"
os.environ["COVER_DIR"] = "./data/test_covers"
os.environ["MAX_CACHE_SIZE_MB"] = "64"

import pytest  # noqa: E402

from helpers import build_test_library  # noqa: E402


@pytest.fixture(scope="session")
def music_library():
    """One shared test music library, read-only for tests."""
    root = build_test_library(Path(os.environ["MUSIC_LIBRARY_PATH"]))
    yield root


async def _reset_state():
    """Rebuild DB schema and wipe cache/hls/covers files between tests."""
    import shutil as _shutil

    from core.config import settings
    from models.database import Base, engine
    from services.smart_cache import smart_cache

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    for p in [Path(settings.CACHE_DIR), Path(settings.HLS_DIR), Path(settings.COVER_DIR)]:
        if p.is_dir():
            _shutil.rmtree(p, ignore_errors=True)
        p.mkdir(parents=True, exist_ok=True)
    smart_cache._cache_index.clear()


@pytest.fixture()
async def client(music_library):
    """A TestClient with a pristine database, cache, hls and covers dirs."""
    await _reset_state()

    from main import app

    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c

    from services.smart_cache import smart_cache

    smart_cache._cache_index.clear()


def scan(client, force: bool = False):
    """Run a synchronous scan and return the response."""
    url = "/api/library/scan/sync" + ("?force=true" if force else "")
    return client.post(url)
