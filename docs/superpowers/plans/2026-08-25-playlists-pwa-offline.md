# 歌单功能 + PWA 离线播放 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 补齐歌单后端 API 与前端交互（创建/重命名/删除/增删歌曲），并实现 PWA manifest + Service Worker 离线播放（音频 cache-first）。

**架构：** 后端新增 `api/playlists.py` 路由（复用现有 Playlist/PlaylistSong 模型）；前端重写 Playlists.vue、给 Library.vue 加"添加到歌单"浮层；`frontend/public/` 下新增 manifest/sw.js/图标，main.js 注册 SW。

**技术栈：** FastAPI + SQLAlchemy（现有）、Vue3 + Pinia（现有）、PIL（仅用于生成图标）、原生 Service Worker。

**规格：** `docs/superpowers/specs/2026-08-25-playlists-pwa-offline-design.md`

---

### 任务 1：歌单后端 API

**文件：**
- 创建：`backend/api/playlists.py`
- 修改：`backend/main.py`（注册 router）
- 测试：`backend/tests/test_playlists_api.py`

- [ ] **步骤 1：编写失败的测试**

```python
# backend/tests/test_playlists_api.py
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
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd backend && .venv\Scripts\python.exe -m pytest tests/test_playlists_api.py -q`
预期：FAIL（ModuleNotFoundError: api.playlists 或 404 全部路由）

- [ ] **步骤 3：实现 `backend/api/playlists.py`**

```python
"""Playlists API routes."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.database import get_db
from models.playlist import Playlist, PlaylistSong
from models.song import Song

router = APIRouter(prefix="/api/playlists", tags=["playlists"])


class PlaylistCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""


class PlaylistUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None


class AddSongRequest(BaseModel):
    song_id: int


class PlaylistResponse(BaseModel):
    id: int
    name: str
    description: str
    song_count: int = 0


class PlaylistSongResponse(BaseModel):
    id: int
    title: str
    artist_name: str = ""
    duration: Optional[float] = None


class PlaylistDetailResponse(PlaylistResponse):
    songs: list[PlaylistSongResponse] = []


@router.get("", response_model=list[PlaylistResponse])
async def list_playlists(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Playlist).options(selectinload(Playlist.songs))
    )
    playlists = result.scalars().all()
    return [
        PlaylistResponse(
            id=p.id, name=p.name, description=p.description,
            song_count=len(p.songs),
        )
        for p in playlists
    ]


@router.post("", response_model=PlaylistResponse)
async def create_playlist(
    request: PlaylistCreateRequest, db: AsyncSession = Depends(get_db)
):
    playlist = Playlist(name=request.name, description=request.description)
    db.add(playlist)
    await db.commit()
    await db.refresh(playlist)
    return PlaylistResponse(id=playlist.id, name=playlist.name, description=playlist.description)


async def _get_playlist(db: AsyncSession, playlist_id: int) -> Playlist:
    result = await db.execute(
        select(Playlist)
        .options(selectinload(Playlist.songs).selectinload(PlaylistSong.song))
        .where(Playlist.id == playlist_id)
    )
    playlist = result.scalar_one_or_none()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return playlist


@router.get("/{playlist_id}", response_model=PlaylistDetailResponse)
async def get_playlist(playlist_id: int, db: AsyncSession = Depends(get_db)):
    playlist = await _get_playlist(db, playlist_id)
    songs = []
    for ps in playlist.songs:  # already ordered by position via relationship
        s = ps.song
        songs.append(
            PlaylistSongResponse(
                id=s.id, title=s.title,
                artist_name=s.artist.name if s.artist else "",
                duration=s.duration,
            )
        )
    return PlaylistDetailResponse(
        id=playlist.id, name=playlist.name, description=playlist.description,
        song_count=len(songs), songs=songs,
    )


@router.put("/{playlist_id}", response_model=PlaylistResponse)
async def update_playlist(
    playlist_id: int,
    request: PlaylistUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    playlist = await _get_playlist(db, playlist_id)
    if request.name is not None:
        playlist.name = request.name
    if request.description is not None:
        playlist.description = request.description
    await db.commit()
    await db.refresh(playlist)
    return PlaylistResponse(
        id=playlist.id, name=playlist.name, description=playlist.description,
        song_count=len(playlist.songs),
    )


@router.delete("/{playlist_id}")
async def delete_playlist(playlist_id: int, db: AsyncSession = Depends(get_db)):
    playlist = await _get_playlist(db, playlist_id)
    for ps in list(playlist.songs):
        await db.delete(ps)
    await db.delete(playlist)
    await db.commit()
    return {"message": "Playlist deleted"}


@router.post("/{playlist_id}/songs", response_model=PlaylistDetailResponse)
async def add_song_to_playlist(
    playlist_id: int,
    request: AddSongRequest,
    db: AsyncSession = Depends(get_db),
):
    playlist = await _get_playlist(db, playlist_id)

    song = (
        await db.execute(select(Song).where(Song.id == request.song_id))
    ).scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    # Idempotent: skip if already present
    existing = (
        await db.execute(
            select(PlaylistSong).where(
                PlaylistSong.playlist_id == playlist_id,
                PlaylistSong.song_id == request.song_id,
            )
        )
    ).scalar_one_or_none()
    if not existing:
        max_pos = (
            await db.execute(
                select(func.max(PlaylistSong.position)).where(
                    PlaylistSong.playlist_id == playlist_id
                )
            )
        ).scalar() or 0
        db.add(PlaylistSong(playlist_id=playlist_id, song_id=request.song_id, position=max_pos + 1))
        await db.commit()

    return await get_playlist(playlist_id, db)


@router.delete("/{playlist_id}/songs/{song_id}")
async def remove_song_from_playlist(
    playlist_id: int,
    song_id: int,
    db: AsyncSession = Depends(get_db),
):
    playlist = await _get_playlist(db, playlist_id)
    ps = (
        await db.execute(
            select(PlaylistSong).where(
                PlaylistSong.playlist_id == playlist_id,
                PlaylistSong.song_id == song_id,
            )
        )
    ).scalar_one_or_none()
    if not ps:
        raise HTTPException(status_code=404, detail="Song not in playlist")
    await db.delete(ps)
    await db.commit()
    return {"message": "Song removed from playlist"}
```

- [ ] **步骤 4：注册路由**

`backend/main.py`：在 `from api.scraper import router as scraper_router` 后加：

```python
from api.playlists import router as playlists_router
```

在 `app.include_router(scraper_router)` 后加：

```python
app.include_router(playlists_router)
```

- [ ] **步骤 5：运行测试验证通过**

运行：`cd backend && .venv\Scripts\python.exe -m pytest tests/test_playlists_api.py -q`
预期：5 passed

- [ ] **步骤 6：Commit**

```bash
git add backend/api/playlists.py backend/main.py backend/tests/test_playlists_api.py
git commit -m "feat: add playlists CRUD API with song management"
```

---

### 任务 2：前端歌单页（Playlists.vue 重写）

**文件：**
- 重写：`frontend/src/views/Playlists.vue`
- 测试：`npm run build`（编译期验证）+ 代码评审

- [ ] **步骤 1：重写 Playlists.vue**

```vue
<template>
  <div>
    <div class="view-header">
      <div class="view-title">{{ editingPlaylist ? '歌单详情' : '歌单' }}</div>
    </div>

    <!-- Detail view -->
    <template v-if="editingPlaylist">
      <button class="btn btn-secondary" style="margin: 0 4px 8px;" @click="backToList">← 返回</button>
      <div class="settings-group">
        <div class="settings-group-title">{{ editingPlaylist.name }} ({{ editingPlaylist.song_count }} 首)</div>
        <div v-if="playlistSongs.length" class="song-list">
          <div v-for="song in playlistSongs" :key="song.id" class="song-item" @click="playFromPlaylist(song)">
            <div class="song-cover-small song-cover-small-placeholder">🎵</div>
            <div class="song-info">
              <div class="song-title">{{ song.title }}</div>
              <div class="song-meta">{{ song.artist_name }}</div>
            </div>
            <button class="btn btn-secondary" style="padding: 4px 10px;" @click.stop="removeSong(song.id)">移除</button>
          </div>
        </div>
        <div v-else class="empty-state" style="padding: 24px;">歌单为空</div>
      </div>
    </template>

    <!-- List view -->
    <template v-else>
      <div class="settings-group">
        <div class="settings-group-title">创建歌单</div>
        <div style="display: flex; gap: 8px; padding: 0 4px;">
          <input v-model="newName" type="text" placeholder="歌单名称..." style="flex: 1; padding: 10px; background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); color: var(--text-primary); outline: none;" />
          <button class="btn btn-primary" :disabled="!newName.trim()" @click="createPlaylist">创建</button>
        </div>
      </div>

      <div class="settings-group">
        <div class="settings-group-title">我的歌单</div>
        <div v-if="playlists.length" class="song-list">
          <div v-for="pl in playlists" :key="pl.id" class="song-item" @click="openPlaylist(pl)">
            <div class="song-cover-small song-cover-small-placeholder">📋</div>
            <div class="song-info">
              <div class="song-title">{{ pl.name }}</div>
              <div class="song-meta">{{ pl.song_count }} 首歌</div>
            </div>
            <button class="btn btn-secondary" style="padding: 4px 10px;" @click.stop="renamePlaylist(pl)">改名</button>
            <button class="btn btn-secondary" style="padding: 4px 10px; margin-left: 4px;" @click.stop="deletePlaylist(pl)">删除</button>
          </div>
        </div>
        <div v-else class="empty-state" style="padding: 40px 20px;">
          <div class="empty-icon">📋</div>
          <div class="empty-text">暂无歌单，先创建一个吧</div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { usePlayerStore } from '../stores/player'

const playerStore = usePlayerStore()
const playlists = ref([])
const playlistSongs = ref([])
const editingPlaylist = ref(null)
const newName = ref('')

async function loadPlaylists() {
  const resp = await fetch('/api/playlists')
  playlists.value = await resp.json()
}

async function createPlaylist() {
  if (!newName.value.trim()) return
  await fetch('/api/playlists', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: newName.value.trim() }),
  })
  newName.value = ''
  await loadPlaylists()
}

async function openPlaylist(pl) {
  const resp = await fetch(`/api/playlists/${pl.id}`)
  const data = await resp.json()
  editingPlaylist.value = data
  playlistSongs.value = data.songs
}

function backToList() {
  editingPlaylist.value = null
  playlistSongs.value = []
  loadPlaylists()
}

async function renamePlaylist(pl) {
  const name = window.prompt('新名称：', pl.name)
  if (!name || name === pl.name) return
  await fetch(`/api/playlists/${pl.id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
  await loadPlaylists()
}

async function deletePlaylist(pl) {
  if (!window.confirm(`删除歌单「${pl.name}」？`)) return
  await fetch(`/api/playlists/${pl.id}`, { method: 'DELETE' })
  await loadPlaylists()
}

async function removeSong(songId) {
  await fetch(`/api/playlists/${editingPlaylist.value.id}/songs/${songId}`, { method: 'DELETE' })
  await openPlaylist(editingPlaylist.value)
}

function playFromPlaylist(song) {
  playerStore.setPlaylist(playlistSongs.value, playlistSongs.value.indexOf(song))
}

onMounted(loadPlaylists)
</script>
```

- [ ] **步骤 2：构建验证**

运行：`cd frontend && npm run build`
预期：构建成功（无编译错误）

- [ ] **步骤 3：Commit**

```bash
git add frontend/src/views/Playlists.vue
git commit -m "feat(frontend): playlist page with create/rename/delete/detail"
```

---

### 任务 3：曲库"添加到歌单"入口（Library.vue）

**文件：**
- 修改：`frontend/src/views/Library.vue`
- 测试：`npm run build`

- [ ] **步骤 1：给歌曲行加"＋"按钮与歌单浮层**

模板中 `.song-item` 内（`song-duration` 之前）加：

```html
<div class="song-actions" @click.stop>
  <button class="btn btn-secondary add-to-playlist-btn" @click="showPlaylistPicker(song)">＋</button>
  <div v-if="pickerSong && pickerSong.id === song.id" class="playlist-picker">
    <div v-for="pl in pickerPlaylists" :key="pl.id" class="playlist-picker-item" @click="addToPlaylist(pl, song)">
      {{ pl.name }}
    </div>
    <div v-if="!pickerPlaylists.length" class="playlist-picker-item muted">暂无歌单</div>
  </div>
</div>
```

`<script setup>` 内加：

```js
const pickerSong = ref(null)
const pickerPlaylists = ref([])

async function showPlaylistPicker(song) {
  pickerSong.value = pickerSong.value?.id === song.id ? null : song
  if (pickerSong.value) {
    const resp = await fetch('/api/playlists')
    pickerPlaylists.value = await resp.json()
  }
}

async function addToPlaylist(pl, song) {
  await fetch(`/api/playlists/${pl.id}/songs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ song_id: song.id }),
  })
  pickerSong.value = null
}
```

`<style>` 或 `main.css` 中补浮层样式（`main.css` 追加）：

```css
.song-actions { position: relative; }
.playlist-picker {
  position: absolute; right: 0; top: 110%;
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 6px 0; z-index: 20;
  min-width: 140px; max-height: 240px; overflow-y: auto;
}
.playlist-picker-item { padding: 8px 14px; font-size: 13px; cursor: pointer; }
.playlist-picker-item:hover { background: var(--bg-hover, rgba(255,255,255,0.06)); }
.playlist-picker-item.muted { color: var(--text-secondary); }
```

- [ ] **步骤 2：构建验证**

运行：`cd frontend && npm run build`
预期：构建成功

- [ ] **步骤 3：Commit**

```bash
git add frontend/src/views/Library.vue frontend/src/styles/main.css
git commit -m "feat(frontend): add-to-playlist picker in library"
```

---

### 任务 4：PWA 清单与图标

**文件：**
- 创建：`frontend/public/manifest.webmanifest`
- 创建：`frontend/public/icons/icon-192.png`、`icon-512.png`
- 创建：`tools/generate_icons.py`
- 修改：`frontend/index.html`
- 修改：`frontend/src/main.js`

- [ ] **步骤 1：生成图标（PIL 脚本）**

创建 `tools/generate_icons.py`：

```python
"""Generate PWA icons (rounded square + note glyph) with PIL."""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "frontend" / "public" / "icons"
OUT.mkdir(parents=True, exist_ok=True)

BG = (20, 26, 36, 255)
FG = (255, 255, 255, 255)


def make_icon(size: int, path: Path):
    img = Image.new("RGBA", (size, size), BG)
    d = ImageDraw.Draw(img)
    # Double note: two heads + stems
    head_r = size * 0.16
    y = size * 0.62
    for x in (size * 0.36, size * 0.62):
        d.ellipse((x - head_r, y - head_r, x + head_r, y + head_r), fill=FG)
    stem_w = max(2, int(size * 0.045))
    d.rectangle((size * 0.36 - stem_w / 2, size * 0.30, size * 0.36 + stem_w / 2, y), fill=FG)
    d.rectangle((size * 0.62 - stem_w / 2, size * 0.30, size * 0.62 + stem_w / 2, y), fill=FG)
    # Beam connecting stems
    d.rectangle((size * 0.36 - stem_w / 2, size * 0.30, size * 0.62 + stem_w / 2, size * 0.30 + stem_w), fill=FG)
    img.save(path)


if __name__ == "__main__":
    make_icon(192, OUT / "icon-192.png")
    make_icon(512, OUT / "icon-512.png")
    print("icons written to", OUT)
```

运行：`cd backend && .venv\Scripts\python.exe ..\tools\generate_icons.py`（复用 venv 的 PIL）
验证：两个 PNG 文件存在且尺寸正确。

- [ ] **步骤 2：创建 manifest**

`frontend/public/manifest.webmanifest`：

```json
{
  "name": "InCar Music",
  "short_name": "InCarMusic",
  "description": "车载音乐流媒体",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "background_color": "#101824",
  "theme_color": "#101824",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

- [ ] **步骤 3：index.html 加 manifest 与主题色**

`<head>` 内加：

```html
<link rel="manifest" href="/manifest.webmanifest" />
<meta name="theme-color" content="#101824" />
```

- [ ] **步骤 4：main.js 注册 Service Worker**

```js
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {})
  })
}
```

- [ ] **步骤 5：构建验证**

运行：`cd frontend && npm run build`
验证：`dist/manifest.webmanifest`、`dist/icons/icon-192.png`、`dist/sw.js`（任务 5 后再验 sw）存在。

- [ ] **步骤 6：Commit**

```bash
git add tools/generate_icons.py frontend/public frontend/index.html frontend/src/main.js
git commit -m "feat(frontend): PWA manifest, icons and SW registration"
```

---

### 任务 5：Service Worker（离线音频缓存）

**文件：**
- 创建：`frontend/public/sw.js`
- 测试：构建后文件存在 + 静态评审

- [ ] **步骤 1：创建 sw.js**

`frontend/public/sw.js`：

```js
/* InCar Music service worker: shell + offline audio (cache-first for /api/stream/*) */
const SHELL_CACHE = 'incar-shell-v1'
const AUDIO_CACHE = 'incar-audio-v1'

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(SHELL_CACHE).then((c) => c.addAll(['/'])))
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== SHELL_CACHE && k !== AUDIO_CACHE)
          .map((k) => caches.delete(k))
      )
    )
  )
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  const req = event.request
  if (req.method !== 'GET') return
  const url = new URL(req.url)

  // Audio streams: cache-first, backfill on success (playback = offline enablement)
  if (url.pathname.startsWith('/api/stream/')) {
    event.respondWith(
      caches.open(AUDIO_CACHE).then(async (cache) => {
        const hit = await cache.match(req)
        if (hit) return hit
        const resp = await fetch(req)
        if (resp.ok) cache.put(req, resp.clone())
        return resp
      })
    )
    return
  }

  // Static assets: cache-first with runtime backfill
  const isStatic =
    url.origin === self.location.origin &&
    (url.pathname.startsWith('/assets/') ||
      url.pathname.startsWith('/icons/') ||
      url.pathname === '/manifest.webmanifest')
  if (isStatic) {
    event.respondWith(
      caches.open(SHELL_CACHE).then(async (cache) => {
        const hit = await cache.match(req)
        if (hit) return hit
        const resp = await fetch(req)
        if (resp.ok) cache.put(req, resp.clone())
        return resp
      })
    )
  }
  // Other /api/* requests: network only (not intercepted)
})
```

- [ ] **步骤 2：构建并验证产物**

运行：`cd frontend && npm run build`
验证：`dist/sw.js` 存在；`dist/index.html` 含 `manifest.webmanifest` 引用。

- [ ] **步骤 3：Commit**

```bash
git add frontend/public/sw.js
git commit -m "feat(frontend): service worker with offline audio cache"
```

---

### 任务 6：README 更新与全量验证

**文件：**
- 修改：`README.md`

- [ ] **步骤 1：README 补歌单 API 与 PWA/离线说明**

在"主要 API"表加：

```markdown
| `/api/playlists/` | GET/POST | 歌单列表 / 创建 |
| `/api/playlists/{id}` | GET/PUT/DELETE | 歌单详情 / 重命名 / 删除 |
| `/api/playlists/{id}/songs` | POST | 添加歌曲到歌单 |
| `/api/playlists/{id}/songs/{song_id}` | DELETE | 从歌单移除歌曲 |
```

新增"离线播放与 PWA"一节（要点：播放过的歌曲自动缓存、断网可回放；Service Worker 需要 HTTPS 或 localhost，手机热点 HTTP 直连时离线功能静默降级，在线播放不受影响）。

- [ ] **步骤 2：全量回归**

运行：`cd backend && .venv\Scripts\python.exe -m pytest tests -q`
预期：全部通过（含 21 个既有测试 + 新增歌单测试）
运行：`cd frontend && npm run build`
预期：构建成功

- [ ] **步骤 3：Commit**

```bash
git add README.md
git commit -m "docs: playlists API and PWA/offline notes"
```

---

## 自检记录

- 规格覆盖：A（歌单 API）→ 任务 1；B1（歌单页）→ 任务 2；B2（曲库入口）→ 任务 3；C（PWA/图标/SW）→ 任务 4、5；D（README）→ 任务 6。无遗漏。
- 类型一致性：`PlaylistResponse.song_count`、`PlaylistDetailResponse.songs[].id` 在前后端一致；端点路径统一 `/api/playlists`。
- 占位符扫描：无 TODO/待定；所有代码块为完整实现。
