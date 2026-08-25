"""Regression tests for SPA history-mode routing when the backend serves the frontend."""


def test_spa_deep_link_falls_back_to_index(client):
    """GET /library (a client-side route) must return index.html, not 404."""
    r = client.get("/library")
    assert r.status_code == 200
    assert "<div id=\"app\"></div>" in r.text

    r = client.get("/playlists")
    assert r.status_code == 200
    assert "<div id=\"app\"></div>" in r.text


def test_unmatched_api_route_still_404(client):
    """The SPA fallback must not swallow unmatched /api routes."""
    r = client.get("/api/this/route/does/not/exist")
    assert r.status_code == 404
