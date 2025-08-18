#!/bin/sh

# 检查必要工具是否存在
check_requirements() {
	if ! lsmod | grep -q 'nft_tproxy'; then
		echo "未检测到 kmod-nf-tproxy，正在尝试自动安装..."
		opkg update && opkg install kmod-nf-tproxy
		if ! lsmod | grep -q 'nft_tproxy'; then
			echo "自动安装 kmod-nf-tproxy 失败，请手动检查！"
			exit 1
		fi
	fi
}
# 设置 tproxy 路由和策略规则
setup_tproxy_route() {
	ip route add local default dev lo table 100
	ip rule add fwmark 0x1 table 100
	ip -6 route add local default dev lo table 100
	ip -6 rule add fwmark 0x1 table 100
}
# 清理 tproxy 路由和策略规则
cleanup_tproxy_route() {
	ip route flush table 100
	ip rule del fwmark 0x1 lookup 100
	ip -6 route flush table 100
	ip -6 rule del fwmark 0x1 lookup 100
}
# 插入 sing-box jump 规则
insert_singbox_jump_rule() {
	nft insert rule inet fw4 mangle_prerouting jump prerouting_sing-box
	nft insert rule inet fw4 mangle_output jump output_sing-box
}
# 删除 sing-box jump 规则
delete_singbox_jump_rule() {
	nft delete rule inet fw4 mangle_prerouting handle $(nft --handle list chain inet fw4 mangle_prerouting | awk '/jump prerouting_sing-box/ {print $(NF)}') 
	nft delete rule inet fw4 mangle_output handle $(nft --handle list chain inet fw4 mangle_output | awk '/jump output_sing-box/ {print $(NF)}') 
}

if [ $# -eq 0 ]; then
	# 无参数，执行清理
	echo "[tproxy] 清理 tproxy 路由和策略规则..."
	cleanup_tproxy_route
	echo "[tproxy] 删除 sing-box 跳转规则..."
	delete_singbox_jump_rule
	echo "[tproxy] 清理完成。"
	exit 0
else
	# 有参数，执行启用
	echo "[tproxy] 检查依赖..."
	check_requirements
	echo "[tproxy] 设置 tproxy 路由和策略规则..."
	setup_tproxy_route
	echo "[tproxy] 插入 sing-box 跳转规则..."
	insert_singbox_jump_rule
	echo "[tproxy] 启用完成。"
fi