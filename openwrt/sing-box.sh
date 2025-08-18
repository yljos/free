#!/bin/sh

# 依赖检测与自动安装
for cmd in curl jq tar; do
    if ! command -v $cmd >/dev/null 2>&1; then
        echo "检测到缺少依赖: $cmd，尝试自动安装..."
        if command -v opkg >/dev/null 2>&1; then
            opkg update && opkg install $cmd
            if ! command -v $cmd >/dev/null 2>&1; then
                echo "$cmd 安装失败，请手动安装后重试。"
                exit 1
            fi
        else
            echo "未检测到 opkg，请手动安装 $cmd 后重试。"
            exit 1
        fi
    fi
done

cd /usr/bin && \
curl -LO $(curl -s https://api.github.com/repos/SagerNet/sing-box/releases | \
jq -r '.[] | select(.prerelease == false and .draft == false) | .assets[] | select(.name | contains("linux-amd64")).browser_download_url' | head -n 1) && \
tar zxvf *.tar.gz --strip-components=1 && \
chown root:root sing-box && \
chmod +x sing-box && \
rm LICENSE && rm *.tar.gz && rm -rf /usr/share/sing-box/ui && rm -rf /usr/share/sing-box/cache.db && \
/etc/init.d/sing-box stop && /etc/init.d/sing-box start
echo "sing-box 更新到最新稳定版"

