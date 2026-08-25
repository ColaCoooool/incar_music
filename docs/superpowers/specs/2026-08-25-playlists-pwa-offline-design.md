# 设计：歌单功能 + PWA 离线播放

日期：2026-08-25
状态：已批准（用户确认：手动歌单、Service Worker 方案、曲库加"添加到歌单"入口）

## 背景

IncarMusic（FastAPI + Vue3）经系统测试后，以下功能缺口需补齐：

1. 歌单后端 API 完全缺失（`models/playlist.py` 已有 Playlist/PlaylistSong 模型，前端 Playlists.vue 是空壳）。
2. PWA 与离线播放未实现（README 声称支持，实际无 manifest / service worker）。

## A. 歌单后端 API

新建 `backend/api/playlists.py`，注册进 `main.py`（prefix `/api/playlists`）。

| 端点 | 方法 | 请求体 | 行为 |
|------|------|--------|------|
| `/` | GET | - | 列表，每项含 `song_count` |
| `/` | POST | `{name, description?}` | 创建；name 必填非空，否则 422/400 |
| `/{id}` | GET | - | 详情含歌曲数组（按 position 排序）；404 若不存在 |
| `/{id}` | PUT | `{name?, description?}` | 重命名/改描述；404 若不存在 |
| `/{id}` | DELETE | - | 删除歌单并级联删除 playlist_songs；404 若不存在 |
| `/{id}/songs` | POST | `{song_id}` | 添加歌曲；幂等（已存在则跳过）；position = 当前 max+1；404 若歌单或歌曲不存在 |
| `/{id}/songs/{song_id}` | DELETE | - | 移除歌曲；404 若不存在 |

约束与细节：

- 歌曲列表返回完整 SongResponse 兼容字段（id/title/artist_name/duration 等），前端直接可播。
- 不使用 `is_smart`/`smart_rule` 字段（智能歌单不做，YAGNI）。
- SQLAlchemy 关系 `Playlist.songs`（PlaylistSong 列表）已配置 `order_by=PlaylistSong.position`。

## B. 前端

### B1. Playlists.vue 重写

- 歌单列表：名称、歌曲数、删除按钮、点击进入详情。
- 创建：输入框 + 按钮（name 必填）。
- 详情视图：歌单内歌曲列表（复用 song-item 样式），点击播放（`playerStore.setPlaylist`），每行移除按钮。
- 重命名：歌单行内编辑（点击名称可改，保存调 PUT）。

### B2. Library.vue 加入口

- 歌曲行尾加"＋"按钮 → 弹出歌单选择浮层（`GET /api/playlists`）→ 点击歌单调 `POST /api/playlists/{id}/songs`，成功后提示。

## C. PWA + 离线播放（Service Worker）

文件：

- `frontend/public/manifest.webmanifest`：name "InCar Music"、short_name、start_url "/"、display "standalone"、theme_color/background_color、icons 192/512。
- `frontend/public/sw.js`：
  - `install`：预缓存 `/`（壳）。
  - `fetch` 策略：
    - `GET /api/stream/*`（音频）→ cache-first；未命中则网络，成功后 `cache.put`（播放即离线可用）。
    - 静态资源（`/assets/*`、`/icons/*`、`/manifest.webmanifest`）→ cache-first，运行时回填。
    - 其余 `/api/*` → network-only（不缓存动态数据）。
  - 不管理配额/LRU：浏览器存储配额自动淘汰（YAGNI）。
- `frontend/public/icons/icon-192.png`、`icon-512.png`：PIL 脚本生成（圆底 + 音符）。
- `frontend/index.html`：加 `<link rel="manifest">`、theme-color meta。
- `frontend/src/main.js`：注册 `navigator.serviceWorker.register('/sw.js')`（失败静默降级）。

### 已知限制（写入 README）

Service Worker 仅 HTTPS 或 localhost 生效。手机热点直连 `http://内网IP:8080` 时，PWA/离线播放静默降级（不影响在线播放）。

## D. 测试与文档

- 后端 pytest（`backend/tests/test_playlists_api.py`）：创建/列表/详情/重命名/删除/添加歌曲/幂等添加/移除歌曲/404 分支。
- 前端：`npm run build` 通过；断言 dist 产物含 `sw.js`、`manifest.webmanifest`、图标。
- README：API 表补歌单端点；新增 PWA/离线播放与 HTTPS 限制说明。

## 范围外（YAGNI）

- 智能歌单（is_smart/smart_rule）。
- 离线缓存管理 UI（进度/配额）。
- 歌单排序拖拽、封面。
