#!/usr/bin/env python3
"""
VLESS URL to YAML converter
转换为包含默认参数的Clash配置格式
"""

import json
from urllib.parse import urlparse, parse_qs
import urllib.parse


def parse_vless_url(url):
    """
    解析VLESS URL，返回配置字典
    包含必要的默认参数，与Clash配置格式保持一致
    """
    # 解析URL
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    # 检查是否为vless协议
    if not url.startswith("vless://"):
        raise ValueError("不是有效的VLESS URL")

    # 获取节点名称 (fragment部分)
    node_name = parsed.fragment if parsed.fragment else "VLESS节点"
    # URL解码节点名称
    node_name = urllib.parse.unquote(node_name)

    # 检查必要参数
    if not parsed.hostname or not parsed.port or not parsed.username:
        raise ValueError(
            f"URL缺少必要信息: server={parsed.hostname}, port={parsed.port}, uuid={parsed.username}"
        )

    # 目标结构
    config = {
        "type": "vless",
        "tag": node_name,
        "server": parsed.hostname,
        "server_port": parsed.port,
        "uuid": parsed.username,
        "tls": {
            "enabled": False,
            "server_name": "",
            "utls": {"enabled": False, "fingerprint": "chrome"},
            "reality": {"enabled": False},
        },
        "transport": {"type": "tcp"},
        "packet_encoding": "xudp",
    }

    # 处理security参数
    security = query.get("security", [""])[0]
    if security in ["tls", "reality"]:
        config["tls"]["enabled"] = True
    if "sni" in query and query["sni"][0]:
        config["tls"]["server_name"] = query["sni"][0]
    else:
        config["tls"]["server_name"] = parsed.hostname
    # utls
    config["tls"]["utls"]["enabled"] = True
    if "fp" in query and query["fp"][0]:
        config["tls"]["utls"]["fingerprint"] = query["fp"][0]
    # reality
    if security == "reality":
        config["tls"]["reality"]["enabled"] = True
        if "pbk" in query and query["pbk"][0]:
            config["tls"]["reality"]["public_key"] = query["pbk"][0]
        if "sid" in query and query["sid"][0]:
            config["tls"]["reality"]["short_id"] = query["sid"][0]
    # 传输协议
    network_type = query.get("type", ["tcp"])[0]
    config["transport"]["type"] = network_type
    if network_type == "grpc":
        if "serviceName" in query and query["serviceName"][0]:
            config["transport"]["service_name"] = query["serviceName"][0]
    elif network_type == "ws":
        if "path" in query and query["path"][0]:
            config["transport"]["path"] = query["path"][0]
        if "host" in query and query["host"][0]:
            config["transport"]["host"] = query["host"][0]
    # packet_encoding
    if "packet_encoding" in query and query["packet_encoding"][0]:
        config["packet_encoding"] = query["packet_encoding"][0]
    return config


def convert_url_to_json(url):
    """
    将VLESS URL转换为JSON字符串
    """
    config = parse_vless_url(url)
    return json.dumps(config, ensure_ascii=False, indent=2)


def main(url):
    """主函数 - 直接转换URL"""
    return parse_vless_url(url)


if __name__ == "__main__":
    pass
