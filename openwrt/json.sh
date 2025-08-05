#!/bin/sh

# 检查参数数量
if [ $# -ne 2 ]; then
    echo "错误：请提供订阅源名称和解压密码作为参数"
    echo "使用方法：$0 <订阅源> <密码>"
    exit 1
fi

SUBSCRIPTION=$1
PASSWORD=$2

(/etc/init.d/mihomo stop) > /dev/null 2>&1
(/etc/init.d/mihomo disable) > /dev/null 2>&1

# 创建临时目录
temp_dir=$(mktemp -d)

# 从远程下载zip文件
if ! curl -s -o "$temp_dir/singbox.zip" "http://nas/singbox.zip"; then
    echo "错误：下载 singbox.zip 失败"
    rm -rf "$temp_dir"
    exit 1
fi

# 解压zip文件以获取txt文件
if ! unzip -P "$PASSWORD" "$temp_dir/singbox.zip" -d "$temp_dir"; then
    echo "错误：解压 zip 文件失败"
    rm -rf "$temp_dir"
    exit 1
fi

# 读取解压后的txt文件内容并获取指定订阅源的URL
url_part=$(grep "^$SUBSCRIPTION:" "$temp_dir/singbox.txt" | cut -d' ' -f2-)

# 检查URL内容是否为空
if [ -z "$url_part" ]; then
    echo "错误：找不到订阅源 '$SUBSCRIPTION' 或 URL 为空"
    rm -rf "$temp_dir"
    exit 1
fi

echo "使用订阅源：$SUBSCRIPTION"
echo "最终 URL：$url_part"

# 下载配置文件
if ! curl -o /etc/sing-box/config.json "$url_part"; then
    echo "错误：下载 config.json 文件失败"
    rm -rf "$temp_dir"
    exit 1
fi

# 清理临时目录
rm -rf "$temp_dir"

# 删除 ui 目录（如果存在），并忽略错误
rm -rf /usr/share/sing-box/ui && rm -rf /usr/share/sing-box/cache.db

(/etc/init.d/sing-box stop && /etc/init.d/sing-box start) > /dev/null 2>&1
echo "sing-box 已启动"

echo "sing-box 配置已更新（订阅：$SUBSCRIPTION）"

