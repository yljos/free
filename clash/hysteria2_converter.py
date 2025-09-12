#!/usr/bin/env python3
"""
Hysteria2 URL to YAML converter
转换为包含默认参数的Clash配置格式
"""

import yaml
from urllib.parse import urlparse, parse_qs
import urllib.parse


def parse_hysteria2_url(url):
    """
    解析Hysteria2 URL，返回配置字典
    包含必要的默认参数，与Clash配置格式保持一致
    """
    # 解析URL
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    # 检查是否为hysteria2协议
    if not url.startswith("hysteria2://"):
        raise ValueError("不是有效的Hysteria2 URL")

    # 获取节点名称 (fragment部分)
    node_name = parsed.fragment if parsed.fragment else "Hysteria2节点"
    # URL解码节点名称
    node_name = urllib.parse.unquote(node_name)

    # 检查必要参数
    if not parsed.hostname or not parsed.port or not parsed.username:
        raise ValueError(
            f"URL缺少必要信息: server={parsed.hostname}, port={parsed.port}, password={parsed.username}"
        )

    # 根据端口号确定端口范围
    port = parsed.port
    if 5000 <= port <= 5999:
        ports_range = "5000-6000"
    elif 1000 <= port <= 1999:
        ports_range = "1000-2000"
    elif 3000 <= port <= 3999:
        ports_range = "3000-4000"
    elif 7000 <= port <= 7999:
        ports_range = "7000-8000"
    elif 9000 <= port <= 9999:
        ports_range = "9000-10000"
    else:
        # 默认端口范围
        ports_range = "5000-6000"

    # 基础配置 - 包含必要的默认参数
    config = {
        "name": node_name,
        "type": "hysteria2",
        "server": parsed.hostname,
        "ports": ports_range,  # 智能端口范围
        "password": parsed.username,
        "udp": True,  # 默认启用UDP
        "skip-cert-verify": False,  # 默认验证证书
        "up": "50 Mbps",  # 默认上传速度限制
        "down": "200 Mbps",  # 默认下载速度限制
    }

    # 处理查询参数 - 覆盖默认值或添加额外参数
    if "sni" in query and query["sni"][0]:
        config["sni"] = query["sni"][0]
    else:
        # 如果没有指定sni，使用服务器地址作为默认值
        config["sni"] = parsed.hostname

    if "insecure" in query:
        config["skip-cert-verify"] = query["insecure"][0].lower() == "true"

    if "obfs" in query and query["obfs"][0]:
        config["obfs"] = query["obfs"][0]

    if "obfs-password" in query and query["obfs-password"][0]:
        config["obfs-password"] = query["obfs-password"][0]

    # 处理上传下载速度参数（覆盖默认值）
    if "upmbps" in query or "up" in query:
        up_speed = query.get("upmbps", query.get("up", [""]))[0]
        if up_speed:
            config["up"] = f"{up_speed} Mbps"

    if "downmbps" in query or "down" in query:
        down_speed = query.get("downmbps", query.get("down", [""]))[0]
        if down_speed:
            config["down"] = f"{down_speed} Mbps"

    return config


def convert_url_to_yaml(url):
    """
    将Hysteria2 URL转换为YAML字符串
    """
    config = parse_hysteria2_url(url)
    clash_config = {"proxies": [config]}
    return yaml.dump(
        clash_config,
        default_flow_style=False,
        allow_unicode=True,
        indent=2,
        default_style=None,
        sort_keys=False,
    )


def main(url):
    """主函数 - 直接转换URL"""
    return parse_hysteria2_url(url)


if __name__ == "__main__":
    pass
