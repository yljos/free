#!/bin/sh

# 从远程 URL 获取 web.txt 文件内容
url_part=$(curl -s http://nas/clash.txt)

# 检查 URL 内容是否为空
if [ -z "$url_part" ]; then
  echo "Error: clash.txt文件内容为空。"
  exit 1
fi

echo "最终 URL: $url_part"

# 使用 curl 下载 config.yaml 文件，并处理错误
if ! curl -o /etc/mihomo/config.yaml "$url_part"; then
  echo "Error: 下载 config.yaml 文件失败。"
  exit 1
fi

# 删除 ui 目录（如果存在），并忽略错误
rm -rf /etc/mihomo/ui && rm -rf /etc/mihomo/cache.db && rm -rf /etc/mihomo/rules

/etc/init.d/mihomo restart

echo "mihomo 配置已更新。"

