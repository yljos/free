#!/usr/bin/env python3
"""
VLESS URL to YAML converter
转换为包含默认参数的Clash配置格式
"""

import yaml
from urllib.parse import urlparse, parse_qs
import urllib.parse
# 导入类型提示所需的模块
from typing import Any, Dict


def parse_vless_url(url: str) -> Dict[str, Any]:
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

    # 基础配置 - 使用 Dict[str, Any] 明确指定值的类型可以为任意类型
    config: Dict[str, Any] = {
        "name": node_name,
        "type": "vless",
        "server": parsed.hostname,
        "port": parsed.port,
        "uuid": parsed.username,
        "udp": True,  # 默认启用UDP
        "packet-encoding": "xudp",  # 默认数据包编码
        "tls": True,  # 默认启用TLS，根据security参数调整
        "servername": "",  # 服务器名称，根据sni参数设置
        "client-fingerprint": "chrome",  # 默认客户端指纹
        "skip-cert-verify": False,  # 默认验证证书
        "network": "tcp",  # 默认传输协议
    }

    # 处理security参数
    security = query.get("security", [""])[0]
    if security in ["tls", "reality"]:
        config["tls"] = True

    # 处理SNI参数
    if "sni" in query and query["sni"][0]:
        config["servername"] = query["sni"][0]

    # 处理Reality配置
    if security == "reality":
        reality_opts: Dict[str, Any] = {}
        if "pbk" in query and query["pbk"][0]:
            reality_opts["public-key"] = query["pbk"][0]
        if "sid" in query and query["sid"][0]:
            reality_opts["short-id"] = query["sid"][0]

        if reality_opts:
            config["reality-opts"] = reality_opts

    # 处理传输协议
    network_type = query.get("type", ["tcp"])[0]
    config["network"] = network_type

    if network_type == "grpc":
        grpc_opts: Dict[str, Any] = {}
        if "serviceName" in query and query["serviceName"][0]:
            grpc_opts["grpc-service-name"] = query["serviceName"][0]

        if grpc_opts:
            config["grpc-opts"] = grpc_opts

    elif network_type == "ws":
        ws_opts: Dict[str, Any] = {}
        if "path" in query and query["path"][0]:
            ws_opts["path"] = query["path"][0]

        headers: Dict[str, Any] = {}
        if "host" in query and query["host"][0]:
            headers["Host"] = query["host"][0]

        if headers:
            ws_opts["headers"] = headers

        if ws_opts:
            config["ws-opts"] = ws_opts

    elif network_type == "tcp":
        if query.get("headerType", [""])[0] == "http":
            # 明确 http_opts 的值可以为任意类型，解决第一个错误
            http_opts: Dict[str, Any] = {"method": "GET"}
            if "path" in query and query["path"][0]:
                # 此处赋值为 list[str]，现在是允许的
                http_opts["path"] = query["path"][0].split(",")

            headers: Dict[str, Any] = {}
            if "host" in query and query["host"][0]:
                headers["Host"] = query["host"][0].split(",")

            if headers:
                http_opts["headers"] = headers

            # 此处赋值为 dict，因为 config 的值类型已声明为 Any，所以不再报错
            config["http-opts"] = http_opts

    # 处理flow参数
    if "flow" in query and query["flow"][0]:
        config["flow"] = query["flow"][0]

    # 处理fingerprint参数
    if "fp" in query and query["fp"][0]:
        config["client-fingerprint"] = query["fp"][0]

    # 清理空值和无效配置
    cleaned_config: Dict[str, Any] = {}
    for key, value in config.items():
        if value is not None and value != "" and value != {}:
            if isinstance(value, dict):
                # 对于字典类型，检查是否为空或包含空值
                cleaned_dict = {
                    k: v for k, v in value.items() if v is not None and v != ""
                }
                if cleaned_dict:
                    cleaned_config[key] = cleaned_dict
            else:
                cleaned_config[key] = value

    return cleaned_config


def convert_url_to_yaml(url: str) -> str:
    """
    将VLESS URL转换为YAML字符串
    """
    config = parse_vless_url(url)
    clash_config = {"proxies": [config]}
    return yaml.dump(
        clash_config,
        default_flow_style=False,
        allow_unicode=True,
        indent=2,
        default_style=None,
        sort_keys=False,
    )


def main(url: str) -> Dict[str, Any]:
    """主函数 - 直接转换URL"""
    return parse_vless_url(url)


if __name__ == "__main__":
    pass