#!/bin/sh

/etc/init.d/sing-box stop

# 从远程 URL 获取 web.txt 文件内容
url_part=$(curl -s http://nas/web.txt)

# 检查 URL 内容是否为空
if [ -z "$url_part" ]; then
  echo "Error: web.txt 文件内容为空。"
  exit 1
fi

# 拼接最终的 URL，并添加额外的查询参数
final_url="http://nas:5000/config/$url_part&emoji=0&ua=sing-box"

# 使用 curl 下载 config.json 文件，并处理错误
if ! curl -o /etc/sing-box/config.json "$final_url"; then
  echo "Error: 下载 config.json 文件失败。"
  exit 1
fi

# 删除 ui 目录（如果存在），并忽略错误
rm -rf /usr/share/sing-box/ui && rm -rf /usr/share/sing-box/cache.db

/etc/init.d/sing-box start

echo "sing-box config.json 已更新。"

