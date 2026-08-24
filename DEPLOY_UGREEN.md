# 🚀 绿联 Docker UI 部署指南

## 📋 部署步骤

### 第一步：SSH 连接到 NAS 构建镜像

因为绿联 Docker UI 不支持直接从源码构建，需要先通过 SSH 构建镜像。

```bash
# 1. SSH 连接到你的绿联 NAS
ssh root@你的NAS-IP

# 2. 克隆项目
cd /volume1
git clone https://github.com/ColaCoooool/incar_music.git
cd incar_music

# 3. 构建后端镜像
docker build -t incar-music-backend .

# 4. 构建前端镜像
cd frontend
docker build -t incar-music-frontend .
cd ..

# 5. 验证镜像
docker images | grep incar-music
```

你应该看到类似这样的输出：
```
incar-music-frontend   latest   xxxxxxxx   xx minutes ago   xxxMB
incar-music-backend    latest   xxxxxxxx   xx minutes ago   xxxMB
```

---

### 第二步：在绿联 Docker UI 中创建后端容器

1. 打开绿联管理界面：`http://你的NAS-IP:9999`
2. 左侧菜单 → **Docker** → **容器**
3. 点击 **创建容器**

#### 后端容器配置：

| 配置项 | 值 |
|--------|-----|
| **容器名称** | `incar-music-backend` |
| **镜像** | `incar-music-backend:latest` |
| **重启策略** | `除非手动停止` |

**端口映射：**
| 容器端口 | 主机端口 | 协议 |
|----------|----------|------|
| 8000 | 8000 | TCP |

**卷映射（存储空间）：**
| 主机路径 | 容器路径 | 模式 |
|----------|----------|------|
| `/volume1/音乐` | `/music` | 只读 |
| `incar-data` (新建卷) | `/app/data` | 读写 |

**环境变量：**
| 变量名 | 值 |
|--------|-----|
| `MUSIC_LIBRARY_PATH` | `/music` |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/incar_music.db` |
| `CACHE_DIR` | `/app/data/cache` |
| `HLS_DIR` | `/app/data/hls` |
| `COVER_DIR` | `/app/data/covers` |
| `MAX_CACHE_SIZE_MB` | `2048` |

---

### 第三步：在绿联 Docker UI 中创建前端容器

1. 继续点击 **创建容器**

#### 前端容器配置：

| 配置项 | 值 |
|--------|-----|
| **容器名称** | `incar-music-frontend` |
| **镜像** | `incar-music-frontend:latest` |
| **重启策略** | `除非手动停止` |

**端口映射：**
| 容器端口 | 主机端口 | 协议 |
|----------|----------|------|
| 80 | 8080 | TCP |

**网络设置：**
- 高级设置 → 网络 → 添加到与 `incar-music-backend` 相同的网络

**环境变量：**
（无特殊要求）

---

### 第四步：启动并验证

1. 确保两个容器都在运行
2. 打开浏览器访问：`http://你的NAS-IP:8080`
3. 如果看到 InCar Music 界面，部署成功！

---

### 第五步：首次使用

1. 打开前端界面 `http://NAS-IP:8080`
2. 点击底部 **曲库**
3. 点击 **扫描音乐库**
4. 等待扫描完成（取决于歌曲数量）
5. 点击 **补全元数据** 获取封面和歌词
6. 返回 **播放** 页面，开始享受音乐！

---

## 🔧 如果构建镜像失败

### 问题：网络问题导致构建慢

```bash
# 使用国内镜像加速（如果有的话）
# 或者使用代理
export HTTP_PROXY=http://你的代理:端口
export HTTPS_PROXY=http://你的代理:端口
docker build -t incar-music-backend .
```

### 问题：找不到 docker 命令

```bash
# 绿联 NAS 可能需要使用完整路径
/usr/bin/docker build -t incar-music-backend .
```

### 问题：权限不足

```bash
# 尝试使用 sudo
sudo docker build -t incar-music-backend .
```

---

## 📱 车机使用

### 方式一：车机浏览器直接访问

1. 手机开启热点
2. 车机连接热点
3. Via 浏览器打开：`http://NAS-IP:8080`

### 方式二：手机浏览器访问

1. 手机连接与 NAS 相同的 Wi-Fi（或热点）
2. 浏览器打开：`http://NAS-IP:8080`

---

## 📊 端口说明

| 端口 | 服务 | 说明 |
|------|------|------|
| 8080 | 前端 | Web 界面（车机/手机访问） |
| 8000 | 后端 | API 服务（内部通信） |

---

## ❓ 常见问题

### Q: 扫描不到音乐？

检查卷映射是否正确：
```bash
docker exec -it incar-music-backend ls /music
```

### Q: 封面/歌词获取失败？

部分歌曲可能无法从在线源获取，这是正常的。你可以：
- 手动上传封面
- 手动编辑歌词

### Q: 播放卡顿？

1. 在设置中降低码率（128kbps）
2. 预缓存常用歌曲
3. 检查网络信号

### Q: 如何更新？

```bash
# SSH 到 NAS
cd /volume1/incar_music
git pull

# 重新构建
docker build -t incar-music-backend .
cd frontend && docker build -t incar-music-frontend .

# 在绿联 Docker UI 中重启容器
```

---

## 📞 获取帮助

如有问题，请在 GitHub Issues 提交：
https://github.com/ColaCoooool/incar_music/issues
