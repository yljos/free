#!/usr/bin/env python3
"""
Shadowsocks URL to JSON converter for Sing-box compatible format
"""

import json
import base64
import binascii  # 导入 binascii 模块
from urllib.parse import urlparse, parse_qs, unquote
import urllib.parse
from typing import Any, Dict

# 这些属性可以从外部设置，以应用于所有解析的URL
# 例如: parse_shadowsocks_url.udp_over_tcp = True
UDP_OVER_TCP = False
MULTIPLEX = False


def parse_shadowsocks_url(url: str) -> Dict[str, Any]:
    """
    解析Shadowsocks URL，返回适配Sing-box格式的配置字典
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
    # FIX: 捕获更具体的异常，不再需要未使用的变量 'e'
    except (ValueError, TypeError, binascii.Error):
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

    # FIX: 明确 config 字典的值可以为任意类型
    config: Dict[str, Any] = {
        "type": "shadowsocks",
        "tag": node_name,
        "server": server,
        "server_port": port,
        "method": method,
        "password": password,
    }

    # 处理插件参数
    query_params = parse_qs(parsed.query)
    if "plugin" in query_params:
        plugin_info = unquote(query_params["plugin"][0])
        # 只要包含simple-obfs或obfs-local，plugin字段统一输出'obfs-local'
        if "simple-obfs" in plugin_info or "obfs-local" in plugin_info:
            config["plugin"] = "obfs-local"
            plugin_parts = plugin_info.split(";")
            obfs_mode = None
            obfs_host = None
            for part in plugin_parts:
                if part.startswith("obfs="):
                    obfs_mode = part.split("=", 1)[1]
                elif part.startswith("obfs-host="):
                    obfs_host = part.split("=", 1)[1]
            plugin_opts_str = ""
            if obfs_mode:
                plugin_opts_str += f"obfs={obfs_mode}"
            if obfs_host:
                if plugin_opts_str:
                    plugin_opts_str += ";"
                plugin_opts_str += f"obfs-host={obfs_host}"
            if plugin_opts_str:
                config["plugin_opts"] = plugin_opts_str
        else:
            # 解析v2ray-plugin等其它插件
            if "v2ray-plugin" in plugin_info:
                config["plugin"] = "v2ray-plugin"
                plugin_parts = plugin_info.split(";")
                v2ray_opts: Dict[str, Any] = {}
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
                    # 此处赋值字典不再导致类型错误
                    config["plugin_opts"] = v2ray_opts
            else:
                config["plugin"] = plugin_info

    # 仅当全局设置不为空时才写入
    if UDP_OVER_TCP:
        config["udp_over_tcp"] = True
    if MULTIPLEX:
        config["multiplex"] = True

    return config


def convert_url_to_json(url: str) -> str:
    """
    将Shadowsocks URL转换为JSON字符串
    """
    config = parse_shadowsocks_url(url)
    return json.dumps(config, ensure_ascii=False, indent=2)


def main(url: str) -> Dict[str, Any]:
    """主函数 - 直接转换URL"""
    return parse_shadowsocks_url(url)


if __name__ == "__main__":
    pass
