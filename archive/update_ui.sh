#!/bin/bash

(
# 检查命令行参数
if [ -z "$1" ] || [ "$1" != "1" ] && [ "$1" != "2" ]; then
    echo "请输入1或2"
    exit 1
fi

# 检查并读取下载地址
if [ ! -f "ui.txt" ]; then
    echo "未找到ui.txt文件"
    exit 1
fi

# 根据选项读取对应行
LINE_NUM="$1"
DOWNLOAD_URL=$(sed -n "${LINE_NUM}p" ui.txt | tr -d '\r\n')
if [ -z "$DOWNLOAD_URL" ]; then
    echo "ui.txt文件第${LINE_NUM}行为空"
    exit 1
fi

# 创建临时目录
TEMP_DIR="./.temp_dist"
mkdir -p "$TEMP_DIR" 2>/dev/null

# 下载最新发布包
echo "正在下载UI文件..."
if ! curl -L -s "$DOWNLOAD_URL" -o "$TEMP_DIR/dist.zip" 2>/dev/null; then
    echo "下载失败"
    rm -rf "$TEMP_DIR" 2>/dev/null
    exit 1
fi

# 解压文件
echo "正在解压文件..."
if command -v unzip >/dev/null 2>&1; then
    # 使用 unzip 命令，-q 安静模式，-o 覆盖已存在文件
    if ! unzip -q -o "$TEMP_DIR/dist.zip" -d "$TEMP_DIR" >/dev/null 2>&1; then
        echo "解压失败"
        rm -rf "$TEMP_DIR" 2>/dev/null
        exit 1
    fi
else
    echo "未找到unzip命令"
    echo "正在安装unzip..."
    sudo pacman -S --noconfirm unzip || {
        echo "unzip安装失败"
        rm -rf "$TEMP_DIR" 2>/dev/null
        exit 1
    }
    echo "unzip安装成功，继续执行..."
fi

# 检查解压后的目录结构并移动文件
echo "正在更新文件..."
TARGET_DIR="$TEMP_DIR/$([ "$LINE_NUM" = "1" ] && echo 'metacubexd-gh-pages' || echo 'dist')"
if [ -d "$TARGET_DIR" ]; then
    if ! cp -r "$TARGET_DIR/"* ./ 2>/dev/null; then
        echo "文件复制失败"
        rm -rf "$TEMP_DIR" 2>/dev/null
        exit 1
    fi
else
    echo "未找到目标目录"
    rm -rf "$TEMP_DIR" 2>/dev/null
    exit 1
fi

# 清理临时文件
echo "清理临时文件..."
rm -rf "$TEMP_DIR" 2>/dev/null

echo "UI更新完成"

# 等待几秒确保日志写入完成
sleep 3
rm -f update_ui.log
) > update_ui.log 2>&1 &
