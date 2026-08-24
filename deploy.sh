#!/bin/bash

echo "🚗 InCar Music 一键部署脚本"
echo "=========================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker 未安装${NC}"
    echo "请先在绿联管理界面开启 Docker 功能"
    exit 1
fi

echo -e "${GREEN}✅ Docker 已安装${NC}"

# 检查 docker-compose
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    echo -e "${RED}❌ docker-compose 未安装${NC}"
    exit 1
fi

echo -e "${GREEN}✅ docker-compose 可用${NC}"

# 获取 NAS IP
NAS_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
if [ -z "$NAS_IP" ]; then
    NAS_IP="你的NAS-IP"
fi

# 获取音乐目录
echo ""
echo -e "${YELLOW}📁 请输入你的音乐目录路径:${NC}"
echo "   例如: /vol1/music 或 /vol1/Music"
echo "   (直接回车使用默认路径 /vol1/music)"
read -r MUSIC_PATH

if [ -z "$MUSIC_PATH" ]; then
    MUSIC_PATH="/vol1/music"
fi

if [ ! -d "$MUSIC_PATH" ]; then
    echo -e "${YELLOW}⚠️  目录不存在: $MUSIC_PATH${NC}"
    echo "   是否继续部署？(y/n)"
    read -r CONTINUE
    if [ "$CONTINUE" != "y" ]; then
        exit 1
    fi
fi

echo -e "${GREEN}✅ 音乐目录: $MUSIC_PATH${NC}"

# 修改配置
echo ""
echo "📝 更新配置..."
sed -i "s|/path/to/your/music|$MUSIC_PATH|g" docker-compose.yml

# 构建并启动
echo ""
echo "🔨 构建镜像..."
$COMPOSE_CMD build --no-cache

echo ""
echo "🚀 启动服务..."
$COMPOSE_CMD up -d

# 等待服务启动
echo ""
echo "⏳ 等待服务启动..."
sleep 5

# 检查状态
if $COMPOSE_CMD ps | grep -q "Up"; then
    echo ""
    echo -e "${GREEN}✅ 部署成功！${NC}"
    echo ""
    echo "📱 访问地址:"
    echo -e "   前端界面: ${GREEN}http://$NAS_IP:8080${NC}"
    echo -e "   API 文档: ${GREEN}http://$NAS_IP:8000/docs${NC}"
    echo ""
    echo "📖 首次使用步骤:"
    echo "   1. 打开前端界面"
    echo "   2. 进入「曲库」页面"
    echo "   3. 点击「扫描音乐库」"
    echo "   4. 等待扫描完成即可使用"
    echo ""
    echo "🚗 车机使用:"
    echo "   1. 手机开启热点"
    echo "   2. 车机连接热点"
    echo "   3. 浏览器打开 http://$NAS_IP:8080"
    echo "   4. 开始享受音乐！"
else
    echo ""
    echo -e "${RED}❌ 部署失败，请检查日志:${NC}"
    echo "   $COMPOSE_CMD logs"
fi
