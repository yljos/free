#!/bin/sh
cd /usr/bin && \
curl -LO $(curl -s https://api.github.com/repos/SagerNet/sing-box/releases | \
grep "browser_download_url.*linux-amd64" | head -n 1 | cut -d '"' -f 4) && \
tar zxvf *.tar.gz --strip-components=1 && \
chown root:root sing-box && \
chmod +x sing-box && \
rm LICENSE && rm *.tar.gz
/etc/init.d/sing-box restart