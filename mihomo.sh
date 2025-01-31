#!/bin/sh
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
/etc/init.d/mihomo restart
echo "mihomo 已更新到最新稳定版"

