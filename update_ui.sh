#!/bin/zsh

# 创建临时目录
TEMP_DIR="/tmp/zashboard_dist"
mkdir -p "$TEMP_DIR"

# 下载最新发布包
echo "正在下载最新UI文件..."
if ! curl -L https://github.com/Zephyruso/zashboard/releases/latest/download/dist.zip -o "$TEMP_DIR/dist.zip"; then
    echo "下载失败!"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# 解压文件
echo "正在解压文件..."
if ! 7z x "$TEMP_DIR/dist.zip" -o"$TEMP_DIR" -y; then
    echo "解压失败!"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# 移动文件到目标目录
echo "正在更新文件..."
cp -r "$TEMP_DIR/dist/"* ./

# 清理临时文件
echo "清理临时文件..."
rm -rf "$TEMP_DIR"

echo "UI更新完成!"