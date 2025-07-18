#!/bin/bash

# 设置错误时退出
set -e

# 检查参数数量
if [ $# -ne 2 ]; then
    echo "用法: $0 <订阅名称> <密码>"
    exit 1
fi

SUBSCRIPTION=$1
PASSWORD=$2

# 保存原始工作目录
ORIGINAL_DIR=$(pwd)

# 创建临时目录
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR" || exit 1

echo "选择的订阅: $SUBSCRIPTION"

# 下载并解压 clash.zip
if ! curl -s -o clash.zip http://nas/clash.zip; then
    echo "错误: 下载 clash.zip 失败"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# 使用提供的密码解压 clash.zip
if ! unzip -P "$PASSWORD" clash.zip; then
    echo "错误: 解压 clash.zip 失败，可能是密码错误"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# 检查解压后是否存在clash.txt文件
if [ ! -f "clash.txt" ]; then
    echo "错误: 无法找到clash.txt文件"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# 根据参数获取对应的 URL
url_part=$(grep "^$SUBSCRIPTION:" clash.txt | cut -d' ' -f2)

# 检查 URL 内容是否为空
if [ -z "$url_part" ]; then
    echo "错误: 无效的订阅选项 '$SUBSCRIPTION'"
    rm -rf "$TEMP_DIR"
    exit 1
fi

echo "使用的 URL: $url_part"

# 使用 curl 下载并保存为 config.yaml
if curl -f -A "clash verge" -o config.yaml "$url_part"; then
    echo "成功下载配置文件到 config.yaml"
else
    echo "错误: 下载失败，请检查 URL 是否有效"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# 移动文件到原始目录
if ! mv config.yaml "$ORIGINAL_DIR/"; then
    echo "错误: 无法移动配置文件"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# 清理临时文件和目录
cd "$ORIGINAL_DIR"
rm -rf "$TEMP_DIR"

echo "配置文件已保存到: $ORIGINAL_DIR/config.yaml"

