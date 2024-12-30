#！/bin/sh
curl -o /etc/sing-box/config.json http://nas:5000/config/https://\&app\=sing_box\&file\=2
/etc/init.d/sing-box restart
