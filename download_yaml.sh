#!/bin/bash

# 使用 cat 读取整个 web.txt 文件内容
encoded_url=$(cat web.txt)


# 解码 URL
decoded_url=$(echo "$encoded_url" | python -c "import sys, urllib.parse; print(urllib.parse.unquote(sys.stdin.read().strip()))")


# 使用 curl 下载并保存为 a.yaml
curl -A "sing-box" -o a.yaml "$decoded_url"

