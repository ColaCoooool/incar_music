# 🚀 绿联 NAS 部署指南

## 前置条件

1. ✅ 绿联 NAS 已开启 Docker 功能
2. ✅ NAS 已连接网络
3. ✅ 已有音乐文件（或准备爬取）

## 方式一：SSH 部署（推荐）

### 1. SSH 连接到 NAS

```bash
ssh root@你的NAS-IP
# 或
ssh admin@你的NAS-IP
```

### 2. 克隆项目

```bash
cd /vol1  # 或你的存储池路径
git clone https://github.com/ColaCoooool/incar_music.git
cd incar_music
```

### 3. 配置音乐路径

编辑 `docker-compose.yml`，修改音乐目录路径：

```bash
# 查看你的音乐目录在哪里
ls /vol1/music  # 常见路径
ls /vol1/Music
ls /vol1/下载

# 修改 docker-compose.yml
vi docker-compose.yml
```

找到这一行并修改：
```yaml
- /vol1/music:/music:ro  # 改为你的实际音乐目录
```

### 4. 启动服务

```bash
# 构建并启动
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 查看状态
docker-compose ps
```

### 5. 访问应用

- **前端界面**: http://你的NAS-IP:8080
- **API 文档**: http://你的NAS-IP:8000/docs

---

## 方式二：绿联 Docker UI 部署

### 1. 打开绿联管理界面

浏览器访问：`http://你的NAS-IP:9999`

### 2. 进入 Docker 管理

左侧菜单 → Docker → 镜像

### 3. 导入镜像

由于是本地项目，需要通过 SSH 先构建镜像：

```bash
# SSH 连接到 NAS 后
cd /vol1/incar_music

# 构建后端镜像
docker build -t incar-music-backend .

# 构建前端镜像
cd frontend
docker build -t incar-music-frontend .
```

### 4. 在 Docker UI 中创建容器

#### 后端容器：
- 镜像：`incar-music-backend`
- 容器名：`incar-music-backend`
- 端口映射：`8000:8000`
- 卷映射：
  - `/vol1/music` → `/music` (只读)
  - `incar-data` → `/app/data`

#### 前端容器：
- 镜像：`incar-music-frontend`
- 容器名：`incar-music-frontend`
- 端口映射：`8080:80`
- 依赖：`incar-music-backend`

---

## 方式三：一键部署脚本

将以下脚本保存为 `deploy.sh` 并在 NAS 上执行：

```bash
#!/bin/bash

echo "🚗 InCar Music 部署脚本"
echo "========================"

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先在绿联管理界面开启 Docker"
    exit 1
fi

# 检查 docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "⚠️  docker-compose 未安装，尝试使用 docker compose"
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

# 获取音乐目录
echo ""
echo "📁 请输入你的音乐目录路径（例如 /vol1/music）:"
read -r MUSIC_PATH

if [ ! -d "$MUSIC_PATH" ]; then
    echo "❌ 目录不存在: $MUSIC_PATH"
    exit 1
fi

echo "✅ 音乐目录: $MUSIC_PATH"

# 修改配置
sed -i "s|/path/to/your/music|$MUSIC_PATH|g" docker-compose.yml

# 启动服务
echo ""
echo "🚀 启动服务..."
$COMPOSE_CMD up -d --build

echo ""
echo "✅ 部署完成！"
echo ""
echo "📱 访问地址:"
echo "   前端界面: http://$(hostname -I | awk '{print $1}'):8080"
echo "   API 文档: http://$(hostname -I | awk '{print $1}'):8000/docs"
echo ""
echo "📖 首次使用请："
echo "   1. 打开前端界面"
echo "   2. 进入「曲库」页面"
echo "   3. 点击「扫描音乐库」"
```

使用方法：
```bash
chmod +x deploy.sh
./deploy.sh
```

---

## 🔧 常用命令

### 查看服务状态
```bash
docker-compose ps
```

### 查看日志
```bash
# 所有日志
docker-compose logs -f

# 仅后端日志
docker-compose logs -f backend

# 仅前端日志
docker-compose logs -f frontend
```

### 重启服务
```bash
docker-compose restart
```

### 停止服务
```bash
docker-compose down
```

### 更新代码
```bash
git pull
docker-compose up -d --build
```

### 清理缓存
```bash
# 通过 API
curl -X POST http://localhost:8000/api/stream/cache/clear

# 或通过前端界面
# 设置 → 清除缓存
```

---

## ❓ 常见问题

### Q: 扫描不到音乐文件？

检查音乐目录是否正确挂载：
```bash
# 进入容器查看
docker exec -it incar-music-backend bash
ls /music
```

### Q: 封面/歌词获取失败？

这是正常的，部分歌曲可能无法从在线源获取。你可以：
1. 手动上传封面（前端界面）
2. 手动编辑歌词

### Q: 播放卡顿？

1. 检查手机热点信号
2. 在设置中降低默认码率（128kbps）
3. 预缓存常用歌曲

### Q: 车机浏览器无法访问？

1. 确保车机和手机在同一热点下
2. 检查 NAS 的防火墙设置
3. 尝试使用 IP 地址而不是域名

---

## 📊 端口说明

| 端口 | 服务 | 说明 |
|------|------|------|
| 8080 | 前端 | Web 界面 |
| 8000 | 后端 | API 服务 |

如有问题，欢迎在 GitHub Issues 提问！
