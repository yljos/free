#!/bin/sh
cd /usr/bin && \
curl -LO $(curl -s https://api.github.com/repos/SagerNet/sing-box/releases | \
jq -r '.[] | select(.draft == false) | .assets[] | select(.name | contains("linux-amd64")).browser_download_url' | head -n 1) && \
tar zxvf *.tar.gz --strip-components=1 && \
chown root:root sing-box && \
chmod +x sing-box && \
rm LICENSE && rm *.tar.gz && rm -rf /usr/share/sing-box/ui && rm -rf /usr/share/sing-box/cache.db && \
/etc/init.d/sing-box stop && /etc/init.d/sing-box start
echo "sing-box 更新到最新版(包括预发布版本)"
