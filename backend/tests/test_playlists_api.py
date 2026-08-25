"""Regression tests for the playlists API."""
from conftest import scan


def _song_id(client):
    scan(client)
    return client.get("/api/songs/").json()[0]["id"]


def test_create_and_list_playlists(client, music_library):
    r = client.post("/api/playlists", json={"name": "开车听", "description": "通勤"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["name"] == "开车听"
    assert data["song_count"] == 0

    # empty name rejected
    r = client.post("/api/playlists", json={"name": ""})
    assert r.status_code == 422

    lst = client.get("/api/playlists").json()
    assert len(lst) == 1
    assert lst[0]["name"] == "开车听"


def test_playlist_add_song_idempotent_and_sorted(client, music_library):
    sid1 = _song_id(client)
    pid = client.post("/api/playlists", json={"name": "p"}).json()["id"]

    # add twice -> idempotent, one entry
    assert client.post(f"/api/playlists/{pid}/songs", json={"song_id": sid1}).status_code == 200
    assert client.post(f"/api/playlists/{pid}/songs", json={"song_id": sid1}).status_code == 200

    d = client.get(f"/api/playlists/{pid}").json()
    assert d["song_count"] == 1
    assert len(d["songs"]) == 1
    assert d["songs"][0]["id"] == sid1

    # adding a nonexistent song -> 404
    r = client.post(f"/api/playlists/{pid}/songs", json={"song_id": 99999})
    assert r.status_code == 404


def test_rename_and_remove_song(client, music_library):
    sid = _song_id(client)
    pid = client.post("/api/playlists", json={"name": "old"}).json()["id"]
    client.post(f"/api/playlists/{pid}/songs", json={"song_id": sid})

    r = client.put(f"/api/playlists/{pid}", json={"name": "new"})
    assert r.status_code == 200
    assert r.json()["name"] == "new"

    assert client.delete(f"/api/playlists/{pid}/songs/{sid}").status_code == 200
    d = client.get(f"/api/playlists/{pid}").json()
    assert d["song_count"] == 0

    # removing again -> 404
    assert client.delete(f"/api/playlists/{pid}/songs/{sid}").status_code == 404


def test_delete_playlist_cascades(client, music_library):
    sid = _song_id(client)
    pid = client.post("/api/playlists", json={"name": "del"}).json()["id"]
    client.post(f"/api/playlists/{pid}/songs", json={"song_id": sid})

    assert client.delete(f"/api/playlists/{pid}").status_code == 200
    assert client.get(f"/api/playlists/{pid}").status_code == 404
    assert client.get("/api/playlists").json() == []


def test_playlist_404s(client, music_library):
    assert client.get("/api/playlists/999").status_code == 404
    assert client.put("/api/playlists/999", json={"name": "x"}).status_code == 404
    assert client.delete("/api/playlists/999").status_code == 404
