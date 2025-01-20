#!/bin/sh

/etc/init.d/sing-box stop

# 从远程 URL 获取 web.txt 文件内容
url_part=$(curl -s http://nas/singbox.txt)

# 检查 URL 内容是否为空
if [ -z "$url_part" ]; then
  echo "Error: singbox.txt文件内容为空。"
  exit 1
fi
# 解码 URL (如果需要可以取消注释)
decoded_url=$(echo "$url_part" | python -c "import sys, urllib.parse; print(urllib.parse.unquote(sys.stdin.read().strip()))")
# 拼接最终的 URL，并添加额外的查询参数
final_url="http://nas:5000/config/$decoded_url&emoji=0&ua=sing-box"
echo "最终 URL: $final_url"

# 使用 curl 下载 config.json 文件，并处理错误
if ! curl -o /etc/sing-box/config.json "$final_url"; then
  echo "Error: 下载 config.json 文件失败。"
  exit 1
fi

# 删除 ui 目录（如果存在），并忽略错误
rm -rf /usr/share/sing-box/ui && rm -rf /usr/share/sing-box/cache.db

/etc/init.d/sing-box start

echo "sing-box 配置已更新。"

