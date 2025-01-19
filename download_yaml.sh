#!/bin/bash

# 设置错误时退出
set -e

# 使用 curl 读取 web.txt 文件内容
url_part=$(curl -s http://nas/web.txt)

# 检查 URL 是否为空
if [ -z "$url_part" ]; then
    echo "错误: 无法获取 URL，web.txt 可能为空或无法访问"
    exit 1
fi

# 解码 URL (如果需要可以取消注释)
decoded_url=$(echo "$url_part" | python -c "import sys, urllib.parse; print(urllib.parse.unquote(sys.stdin.read().strip()))")

# 使用 curl 下载并保存为 a.yaml
if curl -f -A "clash verge" -o a.yaml "$decoded_url"; then
    echo "成功下载配置文件到 a.yaml"
else
    echo "错误: 下载失败，请检查 URL 是否有效"
    exit 1
fi

