#!/bin/sh

# 设置默认模式,转换为大写以便统一比较
MODE=$(echo "${1:-clean}" | tr '[a-z]' '[A-Z]')  # 使用确定的字符范围进行转换

# 验证输入的模式是否有效
case "$MODE" in
    "SINGBOX"|"CLEAN")
        echo "当前运行模式: ${1:-clean}"  # 显示原始输入
        ;;
    *)
        echo "错误: 无效的模式 '${1:-clean}'"
        echo "用法: $0 [singbox|clean]"
        exit 1
        ;;
esac

# 检查 root 权限
if [ "$(id -u)" != "0" ]; then
    echo "错误: 此脚本需要 root 权限运行"
    exit 1
fi

# 配置参数
SINGBOX_PORT=7893  # 与 sing-box 中定义的一致
ROUTING_MARK=666   # 与 sing-box 中定义的一致
PROXY_FWMARK=1
PROXY_ROUTE_TABLE=100

# 获取默认接口，增加错误处理
INTERFACE=$(ip route show default | awk '/default/ {print $5}')
if [ -z "$INTERFACE" ]; then
    echo "错误: 无法获取默认网络接口"
    exit 1
fi

# 保留 IPv4/IPv6 地址集合
ReservedIP4='{ 127.0.0.0/8, 10.0.0.0/8, 100.64.0.0/10, 169.254.0.0/16, 172.16.0.0/12, 192.0.0.0/24, 192.0.2.0/24, 198.51.100.0/24, 192.88.99.0/24, 192.168.0.0/16, 203.0.113.0/24, 224.0.0.0/4, 240.0.0.0/4, 255.255.255.255/32 }'
ReservedIP6='{ ::1/128, fc00::/7, fe80::/10, ff00::/8 }'

# 检查必要工具是否存在
check_requirements() {
    for cmd in ip nft sysctl; do
        if ! command -v $cmd >/dev/null 2>&1; then
            echo "错误: 未找到必需的命令: $cmd"
            exit 1
        fi
    done
}


# 检查IPv4路由表中是否已有本地路由
check_local_route_exists() {
    ip route show table "$PROXY_ROUTE_TABLE" | grep -q "local" 2>/dev/null
    return $?
}
# 检查IPv6路由表中是否已有本地路由
check_local_route6_exists() {
    ip -6 route show table "$PROXY_ROUTE_TABLE" | grep -q "local" 2>/dev/null
    return $?
}

# 创建IPv4/IPv6路由表，如果不存在的话
create_route_table_if_not_exists() {
    if ! check_local_route_exists; then
        echo "创建本地IPv4路由表..."
        ip route add local 0.0.0.0/0 dev lo table "$PROXY_ROUTE_TABLE" || {
            echo "创建IPv4路由表失败"
            exit 1
        }
        echo "本地IPv4路由表创建成功"
    else
        echo "本地IPv4路由表已存在，跳过创建"
    fi
    if ! check_local_route6_exists; then
        echo "创建本地IPv6路由表..."
        ip -6 route add local ::/0 dev lo table "$PROXY_ROUTE_TABLE" || {
            echo "创建IPv6路由表失败"
            exit 1
        }
        echo "本地IPv6路由表创建成功"
    else
        echo "本地IPv6路由表已存在，跳过创建"
    fi
}

# 等待 FIB 表加载完成
wait_for_fib_table() {
    i=1
    while [ $i -le 10 ]; do
        if ip route show table "$PROXY_ROUTE_TABLE" | grep -q "local"; then
            echo "FIB 表加载完成"
            return 0
        fi
        echo "等待 FIB 表加载中，等待 $i 秒..."
        sleep 1
        i=$((i + 1))
    done
    echo "FIB 表加载失败，超出最大重试次数"
    return 1
}

# 清理现有 sing-box 防火墙规则（含IPv6）
clearSingboxRules() {
    echo "清理 sing-box 相关的防火墙规则..."

    # 清理 nftables 规则
    if nft list table inet sing-box >/dev/null 2>&1; then
        nft delete table inet sing-box
        echo "已清理 nftables 规则"
    fi

    # 清理 IPv4 IP 规则（可能有多条，循环删除）
    while ip rule del fwmark $PROXY_FWMARK lookup $PROXY_ROUTE_TABLE 2>/dev/null; do
        echo "已删除 IPv4 IP 规则"
    done
    # 清理 IPv6 IP 规则（可能有多条，循环删除）
    while ip -6 rule del fwmark $PROXY_FWMARK lookup $PROXY_ROUTE_TABLE 2>/dev/null; do
        echo "已删除 IPv6 IP 规则"
    done

    # 清理 IPv4 路由表内容
    if ip route show table $PROXY_ROUTE_TABLE | grep -q "local"; then
        ip route flush table $PROXY_ROUTE_TABLE 2>/dev/null || true
        echo "已清理 IPv4 路由表"
    fi
    # 清理 IPv6 路由表内容
    if ip -6 route show table $PROXY_ROUTE_TABLE | grep -q "local"; then
        ip -6 route flush table $PROXY_ROUTE_TABLE 2>/dev/null || true
        echo "已清理 IPv6 路由表"
    fi

    echo "sing-box 相关的防火墙规则清理完成"
}

# 验证设置是否正确
verify_setup() {
    echo "验证 tproxy 设置..."
    
    # 检查监听端口
    if ! netstat -tlnp 2>/dev/null | grep ":$SINGBOX_PORT" >/dev/null; then
        echo "警告: sing-box 未在端口 $SINGBOX_PORT 监听"
        echo "请确保 sing-box 正在运行且配置正确"
    else
        echo "✓ sing-box 端口监听正常"
    fi
    
    # 检查路由规则
    if ! ip rule show | grep "fwmark 0x$PROXY_FWMARK" >/dev/null; then
        echo "警告: 路由规则未正确设置"
        return 1
    else
        echo "✓ 路由规则设置正确"
    fi
    
    # 检查本地路由
    if ! ip route show table $PROXY_ROUTE_TABLE | grep -q "local"; then
        echo "警告: 本地路由表未正确设置"
        return 1
    else
        echo "✓ 本地路由表设置正确"
    fi
    
    # 检查 nftables 规则
    if ! nft list table inet sing-box >/dev/null 2>&1; then
        echo "警告: nftables 规则未正确应用"
        return 1
    else
        echo "✓ nftables 规则应用正确"
    fi
    
    echo "tproxy 设置验证完成"
    return 0
}

# 主程序开始
main() {
    # 检查必要工具
    check_requirements
    
    # 清理现有规则
    clearSingboxRules

    # 如果是 clean 模式,到此结束
    if [ "$MODE" = "CLEAN" ]; then
        echo "已清理所有 sing-box 相关的防火墙规则"
        exit 0
    fi

    # 仅在 SingBox 模式下应用新的防火墙规则
    if [ "$MODE" = "SINGBOX" ]; then
        echo "应用 SingBox 模式下的防火墙规则..."

        # 创建并确保路由表存在
        create_route_table_if_not_exists

        # 等待 FIB 表加载完成
        if ! wait_for_fib_table; then
            echo "FIB 表准备失败，退出脚本。"
            exit 1
        fi

        # 设置 IPv4/IPv6 IP 规则（不再重复创建路由）
        ip rule add fwmark $PROXY_FWMARK table $PROXY_ROUTE_TABLE || { 
            echo "添加 IPv4 IP 规则失败"
            exit 1
        }
        ip -6 rule add fwmark $PROXY_FWMARK table $PROXY_ROUTE_TABLE || {
            echo "添加 IPv6 IP 规则失败"
            exit 1
        }
        
        # 确保目录存在
        mkdir -p /etc/sing-box/nft

        # 手动创建 inet 表
        nft add table inet sing-box

        # 设置 SingBox 模式下的 nftables 规则
        cat > /etc/sing-box/nft/nftables.conf <<EOF
table inet sing-box {
    set RESERVED_IPSET {
        type ipv4_addr
        flags interval
        auto-merge
        elements = $ReservedIP4
    }

    set RESERVED_IPSET6 {
        type ipv6_addr
        flags interval
        auto-merge
        elements = $ReservedIP6
   }

    set DIRECT_IPSET4 {
        type ipv4_addr
        flags interval
        auto-merge
        elements = { 192.168.31.8 }
    }

    set DIRECT_IPSET6 {
        type ipv6_addr
        flags interval
        auto-merge
        elements = { ::1/128, fe80::/10, fc00::/7 }
    }

    chain prerouting_singbox {
        type filter hook prerouting priority mangle; policy accept;

        # 跳过本机发出的流量（避免循环）
        meta mark $ROUTING_MARK accept

        # 确保 DHCP 数据包不被拦截 UDP 67/68
        udp dport { 67, 68 } accept comment "Allow DHCP traffic"

        # 放行 ICMPv6
        ip6 nexthdr icmpv6 accept comment "Allow ICMPv6"

        # 跳过到本机的流量
        fib daddr type local accept

        # 保留地址绕过
        ip daddr @RESERVED_IPSET accept
        ip6 daddr @RESERVED_IPSET6 accept

        # 直连设备绕过
        ip saddr @DIRECT_IPSET4 accept comment "Allow direct connection for specific devices"
        ip daddr @DIRECT_IPSET4 accept comment "Allow direct connection for specific devices"
        ip6 saddr @DIRECT_IPSET6 accept comment "Allow direct connection for specific devices"
        ip6 daddr @DIRECT_IPSET6 accept comment "Allow direct connection for specific devices"

        # 放行所有经过 DNAT 的流量
        ct status dnat accept comment "Allow forwarded traffic"

        # DNS 透明代理
        meta l4proto { tcp, udp } th dport 53 tproxy to :$SINGBOX_PORT

        # 其他流量透明代理并打标
        meta l4proto { tcp, udp } tproxy to :$SINGBOX_PORT meta mark set $PROXY_FWMARK
    }

    chain output_singbox {
        type route hook output priority mangle; policy accept;

        # 放行本地回环接口流量
        meta oifname "lo" accept

        # 放行 ICMPv6
        ip6 nexthdr icmpv6 accept comment "Allow ICMPv6"

        # sing-box 发出的流量绕过
        meta mark $ROUTING_MARK accept

        # 本地地址绕过
        fib daddr type local accept

        # 保留地址绕过
        ip daddr @RESERVED_IPSET accept
        ip6 daddr @RESERVED_IPSET6 accept

        # 直连设备绕过
        ip saddr @DIRECT_IPSET4 accept comment "Allow direct connection for specific devices"
        ip daddr @DIRECT_IPSET4 accept comment "Allow direct connection for specific devices"
        ip6 saddr @DIRECT_IPSET6 accept comment "Allow direct connection for specific devices"
        ip6 daddr @DIRECT_IPSET6 accept comment "Allow direct connection for specific devices"

        # 绕过 NBNS 流量
        udp dport { netbios-ns, netbios-dgm, netbios-ssn } accept

        # 标记其他流量
        meta l4proto { tcp, udp } meta mark set $PROXY_FWMARK
    }
}
EOF

        # 应用防火墙规则和 IP 路由
        echo "正在应用 nftables 规则..."
        if ! nft -f /etc/sing-box/nft/nftables.conf; then
            echo "错误: 应用 nftables 规则失败"
            exit 1
        fi

        echo "SingBox 模式的防火墙规则已成功应用。"
        
        # 验证设置
        verify_setup || echo "设置可能存在问题，请检查日志"
    fi
}

# 执行主程序
main