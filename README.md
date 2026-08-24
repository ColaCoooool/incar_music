# 🚗 InCar Music - 车载音乐流媒体

基于家中 NAS 的车载音乐流媒体解决方案。支持从 NAS 远程播放音乐，智能缓存离线播放，自动获取歌词和封面。

## ✨ 功能特性

### 🎵 音乐播放
- **自适应码率流媒体** (HLS) - 根据网络质量自动切换音质
- **智能预缓存** - 预测下一首播放的歌曲并提前缓存
- **离线播放** - 断网时无缝切换到本地缓存
- **LRU 淘汰策略** - 智能管理缓存空间

### 📚 音乐管理
- **自动扫描** NAS 音乐目录
- **完整元数据提取** - 歌名、歌手、专辑、年份、流派
- **艺术家/专辑/流派分类** 浏览
- **播放列表管理**
- **播放统计** - 播放次数、最近播放

### 🎨 封面与歌词
- **自动获取专辑封面** - 从网易云、MusicBrainz 等来源
- **自动获取歌词** - 支持 LRC 格式同步歌词
- **歌词逐行滚动** 显示
- **手动编辑/上传** 封面和歌词

### 🕷️ 音乐爬取
- **Bilibili** - 从 B站视频提取音频
- **抖音** - 从抖音视频提取音频
- **自动识别平台** - 粘贴链接即可爬取

### 📱 多端适配
- **车载浏览器** - 大按钮、大字体、触屏优化
- **手机浏览器** - 响应式设计
- **PWA 支持** - 可添加到主屏幕

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────┐
│              绿联 NAS (Docker)                │
│                                               │
│  ┌──────────┐  ┌────────┐  ┌──────────┐    │
│  │ FastAPI  │  │ SQLite │  │  Redis   │    │
│  │ Backend  │  │  DB    │  │  Cache   │    │
│  └──────────┘  └────────┘  └──────────┘    │
│                                               │
│  ┌──────────┐  ┌────────┐  ┌──────────┐    │
│  │ FFmpeg   │  │ Music  │  │ Scraper  │    │
│  │ Transcode│  │ Scanner│  │ B站/抖音 │    │
│  └──────────┘  └────────┘  └──────────┘    │
│                                               │
│  ┌──────────────────────────────────────┐    │
│  │         /music (NAS 音乐挂载)         │    │
│  └──────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
                       │
                  手机热点
                       │
            ┌──────────┴──────────┐
            │                     │
     ┌──────┴──────┐    ┌───────┴───────┐
     │  车机浏览器  │    │   手机浏览器   │
     │  (Via等)    │    │              │
     └─────────────┘    └───────────────┘
```

## 🚀 快速开始

### 1. 准备 NAS 音乐目录

确保你的 NAS 上有音乐文件，目录结构如：
```
/music/
├── Artist A/
│   ├── Album 1/
│   │   ├── song1.mp3
│   │   └── song2.flac
│   └── Album 2/
│       └── song3.mp3
└── Artist B/
    └── ...
```

### 2. 修改 docker-compose.yml

编辑 `docker-compose.yml`，将音乐目录路径改为你的实际路径：

```yaml
volumes:
  - /your/nas/music/path:/music:ro  # 改为你的音乐目录
```

### 3. 启动服务

```bash
# 克隆项目
git clone https://github.com/ColaCoooool/incar_music.git
cd incar_music

# 启动
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 4. 访问应用

- **前端界面**: http://你的NAS-IP:8080
- **API 文档**: http://你的NAS-IP:8000/docs
- **健康检查**: http://你的NAS-IP:8000/api/health

### 5. 扫描音乐库

首次使用需要扫描音乐库：
1. 打开前端界面
2. 进入「曲库」页面
3. 点击「扫描音乐库」
4. 等待扫描完成

## 📁 项目结构

```
incar_music/
├── backend/                    # Python 后端
│   ├── api/                   # API 路由
│   │   ├── songs.py          # 歌曲 CRUD
│   │   ├── streaming.py      # 流媒体播放
│   │   ├── library.py        # 库管理
│   │   ├── covers.py         # 封面管理
│   │   ├── lyrics.py         # 歌词管理
│   │   └── scraper.py        # 音乐爬取
│   ├── models/                # 数据模型
│   │   ├── database.py       # 数据库连接
│   │   ├── song.py           # 歌曲模型
│   │   ├── artist.py         # 艺术家模型
│   │   ├── album.py          # 专辑模型
│   │   ├── lyrics.py         # 歌词模型
│   │   └── cover.py          # 封面模型
│   ├── services/              # 业务逻辑
│   │   ├── scanner.py        # 音乐扫描
│   │   ├── metadata_fetcher.py # 元数据获取
│   │   ├── streamer.py       # HLS 流媒体
│   │   └── smart_cache.py    # 智能缓存
│   ├── scrapers/              # 爬虫模块
│   │   ├── bilibili.py       # B站爬取
│   │   └── douyin.py         # 抖音爬取
│   ├── core/                  # 核心配置
│   │   └── config.py         # 应用配置
│   └── main.py               # 应用入口
├── frontend/                   # Vue.js 前端
│   ├── src/
│   │   ├── views/            # 页面组件
│   │   ├── stores/           # Pinia 状态
│   │   ├── styles/           # 样式
│   │   └── router.js         # 路由
│   └── package.json
├── docker-compose.yml          # Docker 部署
├── Dockerfile                  # 后端镜像
└── README.md
```

## 🔧 配置说明

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MUSIC_LIBRARY_PATH` | `/music` | NAS 音乐目录挂载点 |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/incar_music.db` | 数据库路径 |
| `CACHE_DIR` | `./data/cache` | 缓存目录 |
| `HLS_DIR` | `./data/hls` | HLS 流文件目录 |
| `COVER_DIR` | `./data/covers` | 封面图片目录 |
| `MAX_CACHE_SIZE_MB` | `2048` | 最大缓存大小 (MB) |
| `HOST` | `0.0.0.0` | 监听地址 |
| `PORT` | `8000` | 监听端口 |

### 音质设置

支持的码率：64kbps / 128kbps / 192kbps / 320kbps

- **320kbps**: 高音质，需要稳定网络
- **192kbps**: 标准音质，推荐
- **128kbps**: 低带宽
- **64kbps**: 极低带宽

### 缓存策略

- 默认最大缓存：2GB
- 使用 LRU 淘汰策略
- 自动预测预缓存下一首歌
- 支持手动触发缓存

## 🛠️ 开发

### 后端开发

```bash
cd backend

# 安装依赖
pip install -e ".[dev]"

# 启动开发服务器
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 前端开发

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

## 📝 API 文档

启动后端后访问 http://localhost:8000/docs 查看完整的 API 文档。

### 主要 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/songs/` | GET | 获取歌曲列表 |
| `/api/songs/{id}` | GET | 获取歌曲详情 |
| `/api/stream/{id}` | GET | 直接播放音频 |
| `/api/stream/{id}/hls/playlist.m3u8` | GET | HLS 流播放 |
| `/api/library/scan` | POST | 扫描音乐库 |
| `/api/library/stats` | GET | 库统计信息 |
| `/api/lyrics/{song_id}` | GET | 获取歌词 |
| `/api/covers/{song_id}` | GET | 获取封面 |
| `/api/scraper/auto` | POST | 自动爬取音频 |
| `/api/stream/cache/stats` | GET | 缓存统计 |

## 📄 License

MIT License
