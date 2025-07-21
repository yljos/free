#!/bin/sh

# 检查并安装必需的工具
check_and_install() {
    local cmd=$1
    if ! command -v $cmd >/dev/null 2>&1; then
        echo "正在安装 $cmd..."
        opkg update >/dev/null 2>&1
        opkg install $cmd
        if ! command -v $cmd >/dev/null 2>&1; then
            echo "错误: 无法安装 $cmd, 请手动安装后重试."
            exit 1
        fi
    fi
}

# 检查并安装必需的工具
for cmd in curl jq gunzip; do
    check_and_install $cmd
done

cd /usr/bin && \
curl -LO $(curl -s https://api.github.com/repos/MetaCubeX/mihomo/releases | \
jq -r '[.[] | select(.prerelease == false and .draft == false)][0] | .assets[] | select(.name | startswith("mihomo-linux-amd64-compatible") and (contains("go") | not) and endswith(".gz")).browser_download_url') && \
FILENAME=$(ls mihomo-linux-amd64-compatible-*.gz) && \
gunzip "$FILENAME" && \
UNZIPPED_NAME=${FILENAME%.gz} && \
mv "$UNZIPPED_NAME" mihomo && \
chown root:root mihomo && \
chmod +x mihomo && \
rm -f "$FILENAME" && \
rm -rf /etc/mihomo/ui && rm -rf /etc/mihomo/cache.db && rm -rf /etc/mihomo/rules && \
#/etc/init.d/mihomo restart
echo "mihomo 已更新到最新稳定版"

