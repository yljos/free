#!/bin/sh

/etc/init.d/sing-box stop
# 检查 web.txt 文件是否存在
if [ ! -f web.txt ]; then
  echo "Error: web.txt 文件不存在。"
  exit 1
fi

# 从 web.txt 文件中读取 URL，并去除可能的空格和换行符
url=$(cat web.txt | xargs)

# 检查 URL 是否为空
if [ -z "$url" ]; then
  echo "Error: web.txt 文件内容为空。"
  exit 1
fi

# 使用 curl 下载 config.json 文件，并处理错误
if ! curl -o /etc/sing-box/config.json "$url"; then
  echo "Error: 下载 config.json 文件失败。"
  exit 1
fi

# 删除 ui 目录（如果存在），并忽略错误
rm -rf /usr/share/sing-box/ui && rm -rf /usr/share/sing-box/cache.db


/etc/init.d/sing-box start

echo "sing-box config.json 已更新。"
