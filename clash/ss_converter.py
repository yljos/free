#!/usr/bin/env python3
"""
Shadowsocks URL to YAML converter
转换为包含默认参数的Clash配置格式
"""

import yaml
import base64
from urllib.parse import urlparse, parse_qs, unquote
import urllib.parse


def parse_shadowsocks_url(url):
    """
    解析Shadowsocks URL，返回配置字典
    包含必要的默认参数，与Clash配置格式保持一致
    """
    # 解析URL
    parsed = urlparse(url)

    # 检查是否为ss协议
    if not url.startswith("ss://"):
        raise ValueError("不是有效的Shadowsocks URL")

    # 获取节点名称 (fragment部分)
    node_name = parsed.fragment if parsed.fragment else "SS节点"
    # URL解码节点名称
    node_name = urllib.parse.unquote(node_name)

    # 解析用户信息部分 (base64编码的method:password)
    user_info = parsed.username
    if not user_info:
        raise ValueError("URL缺少用户信息")

    try:
        # 尝试base64解码
        decoded_user = base64.b64decode(user_info + "===").decode("utf-8")
        if ":" in decoded_user:
            method, password = decoded_user.split(":", 1)
        else:
            raise ValueError("解码后的用户信息格式不正确")
    except Exception as e:
        # 如果base64解码失败，尝试直接分割
        if ":" in user_info:
            method, password = user_info.split(":", 1)
        else:
            raise ValueError(f"无法解析用户信息: {user_info}")

    # 获取服务器和端口
    server = parsed.hostname
    port = parsed.port

    if not server or not port:
        raise ValueError(f"URL缺少必要信息: server={server}, port={port}")

    # 基础配置 - 包含必要的默认参数
    config = {
        "name": node_name,
        "type": "ss",
        "server": server,
        "port": port,
        "cipher": method,
        "password": password,
        "udp": True,  # 默认启用UDP
    }

    # 处理插件参数
    query_params = parse_qs(parsed.query)
    if "plugin" in query_params:
        plugin_info = unquote(query_params["plugin"][0])

        # 解析插件信息，如 simple-obfs;obfs=http;obfs-host=xxx
        if "simple-obfs" in plugin_info or "obfs-local" in plugin_info:
            plugin_parts = plugin_info.split(";")
            obfs_mode = None
            obfs_host = None

            for part in plugin_parts:
                if part.startswith("obfs="):
                    obfs_mode = part.split("=", 1)[1]
                elif part.startswith("obfs-host="):
                    obfs_host = part.split("=", 1)[1]

            if obfs_mode:
                config["plugin"] = "obfs"
                plugin_opts = {"mode": obfs_mode}
                if obfs_host:
                    plugin_opts["host"] = obfs_host

                config["plugin-opts"] = plugin_opts

        elif "v2ray-plugin" in plugin_info:
            # 处理v2ray-plugin
            plugin_parts = plugin_info.split(";")
            v2ray_opts = {}

            for part in plugin_parts:
                if part.startswith("mode="):
                    v2ray_opts["mode"] = part.split("=", 1)[1]
                elif part.startswith("host="):
                    v2ray_opts["host"] = part.split("=", 1)[1]
                elif part.startswith("path="):
                    v2ray_opts["path"] = part.split("=", 1)[1]
                elif part == "tls":
                    v2ray_opts["tls"] = True

            if v2ray_opts:
                config["plugin"] = "v2ray-plugin"
                config["plugin-opts"] = v2ray_opts

    return config


def convert_url_to_yaml(url):
    """
    将Shadowsocks URL转换为YAML字符串
    """
    config = parse_shadowsocks_url(url)
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
    return parse_shadowsocks_url(url)


if __name__ == "__main__":
    pass
