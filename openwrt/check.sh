#!/bin/sh

# 检测目标IP是否在线，并根据结果控制mihomo服务
# 每30秒检测一次，在线启动mihomo，不在线停止mihomo

TARGET_IP="10.0.0.25"
CHECK_INTERVAL=30
PING_COUNT=3
PING_TIMEOUT=1

logger "IP监控脚本已启动，监控目标: $TARGET_IP"

while true; do
    # 使用ping检测目标IP是否在线
    if ping -c $PING_COUNT -W $PING_TIMEOUT $TARGET_IP >/dev/null 2>&1; then
        # 检查mihomo是否已经运行
        if ! /etc/init.d/mihomo status >/dev/null 2>&1; then
            logger "$TARGET_IP 在线，启动mihomo服务"
            /etc/init.d/mihomo start
        else
            logger "$TARGET_IP 在线，mihomo服务已在运行中"
        fi
    else
        # 检查mihomo是否已经停止
        if /etc/init.d/mihomo status >/dev/null 2>&1; then
            logger "$TARGET_IP 离线，停止mihomo服务"
            /etc/init.d/mihomo stop
        else
            logger "$TARGET_IP 离线，mihomo服务已停止"
        fi
    fi
    
    # 等待指定的间隔时间
    sleep $CHECK_INTERVAL
done