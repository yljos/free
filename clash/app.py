import threading


# --------- 临时文件清理工具 ---------
def cleanup_files(file_list):
    import os, sys

    for f in file_list:
        try:
            os.remove(f)
            print(f"[临时文件清理] 删除成功: {f}", file=sys.stderr)
        except Exception as ex:
            print(f"[临时文件清理] 删除失败: {f}, 错误: {ex}", file=sys.stderr)


from flask import after_this_request


def create_cleanup_callback(temp_files, exclude_files=None):
    @after_this_request
    def cleanup_callback(response):
        import threading
        import time

        def delayed_cleanup():
            time.sleep(2)  # 等待2秒确保文件传输完成
            files_to_clean = temp_files.copy()
            if exclude_files:
                for exclude_file in exclude_files:
                    if exclude_file in files_to_clean:
                        files_to_clean.remove(exclude_file)
            cleanup_files(files_to_clean)
            if exclude_files:
                time.sleep(1)  # 再等待1秒
                cleanup_files(exclude_files)

        cleanup_thread = threading.Thread(target=delayed_cleanup, daemon=True)
        cleanup_thread.start()
        return response

    return cleanup_callback


#!/usr/bin/env python3
"""
Flask应用 - 处理base64编码的节点信息，生成config.yaml
支持从URL参数获取base64编码数据，解码后处理vless://节点信息
"""

from flask import Flask, request, jsonify, send_file
import base64
import yaml
import os
import tempfile
from urllib.parse import urlparse, unquote
import re
import requests
from ruamel.yaml import YAML

# 导入现有的转换器模块
try:
    from vless_converter import parse_vless_url
except ImportError:
    print("警告: 无法导入vless_converter模块")
    parse_vless_url = None

try:
    from ss_converter import parse_shadowsocks_url as parse_ss_url
except ImportError:
    print("警告: 无法导入ss_converter模块")
    parse_ss_url = None

try:
    from hysteria2_converter import parse_hysteria2_url
except ImportError:
    print("警告: 无法导入hysteria2_converter模块")
    parse_hysteria2_url = None

app = Flask(__name__)


def decode_base64_content(content):
    """
    解码base64内容
    """
    try:
        # 处理可能的URL安全base64编码
        content = content.replace("-", "+").replace("_", "/")
        # 添加填充字符
        padding = len(content) % 4
        if padding:
            content += "=" * (4 - padding)

        decoded_bytes = base64.b64decode(content)
        decoded_text = decoded_bytes.decode("utf-8")
        return decoded_text
    except Exception as e:
        raise ValueError(f"Base64解码失败: {str(e)}")


def fetch_subscription_info(url):
    """
    使用clash verge User-Agent获取订阅信息
    """
    try:
        headers = {"User-Agent": "clash-verge"}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        # 只获取订阅信息头部
        subscription_userinfo = response.headers.get("Subscription-Userinfo", "")
        return subscription_userinfo

    except Exception as e:
        print(f"获取订阅信息失败: {str(e)}")
        return ""


def fetch_content_from_url(url):
    """
    从URL获取base64编码的内容并解码
    """
    try:
        # 第一步：使用clash verge User-Agent获取订阅信息
        subscription_userinfo = fetch_subscription_info(url)

        # 第二步：使用Firefox User-Agent获取base64内容
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0"
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        # 获取响应内容并尝试base64解码
        content = response.text.strip()
        decoded_content = decode_base64_content(content)
        # 返回解码内容和订阅信息
        return decoded_content, subscription_userinfo

    except Exception as e:
        raise ValueError(f"获取URL内容失败: {str(e)}")


def extract_urls_from_text(text):
    """
    从文本中提取所有节点URL
    """
    urls = []
    lines = text.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 检查是否为支持的协议
        if line.startswith(("vless://", "ss://", "hysteria2://", "hy2://")):
            urls.append(line)

    return urls


def parse_node_url(url):
    """
    根据协议类型解析节点URL
    """
    url = url.strip()

    if url.startswith("vless://"):
        if parse_vless_url:
            return parse_vless_url(url)
        else:
            raise ValueError("VLESS转换器未可用")

    elif url.startswith("ss://"):
        if parse_ss_url:
            return parse_ss_url(url)
        else:
            raise ValueError("SS转换器未可用")

    elif url.startswith(("hysteria2://", "hy2://")):
        if parse_hysteria2_url:
            return parse_hysteria2_url(url)
        else:
            raise ValueError("Hysteria2转换器未可用")

    else:
        raise ValueError(f"不支持的协议类型: {url[:20]}...")


def generate_clash_config(nodes):
    """
    生成Clash配置文件 - 仅包含节点信息
    """
    config = {"proxies": nodes}

    return config


@app.route("/", methods=["GET"])
def index():
    return "", 200


@app.route("/<path:url_path>", methods=["GET"])
def process_nodes_from_path(url_path):
    """
    通过路径参数处理节点信息并生成config.yaml
    URL格式: http://127.0.0.1:5000/https://example.com/path/to/base64/content
    """
    try:
        # 重新组合完整的URL，包括查询参数
        full_url = url_path
        if request.query_string:
            # 如果有查询参数，重新组合完整URL
            query_part = request.query_string.decode("utf-8")
            full_url = f"{url_path}?{query_part}"

        # 从URL获取内容
        try:
            decoded_content, subscription_userinfo = fetch_content_from_url(full_url)
        except ValueError as e:
            return jsonify({"error": str(e), "url": full_url}), 400

        # 提取节点URL
        node_urls = extract_urls_from_text(decoded_content)
        if not node_urls:
            return (
                jsonify(
                    {
                        "error": "未找到有效的节点URL",
                        "decoded_content": (
                            decoded_content[:500] + "..."
                            if len(decoded_content) > 500
                            else decoded_content
                        ),
                        "url": full_url,
                    }
                ),
                400,
            )

        # 解析所有节点
        nodes = []
        errors = []

        for i, url in enumerate(node_urls):
            try:
                node_config = parse_node_url(url)
                nodes.append(node_config)
            except Exception as e:
                errors.append(f"节点 {i+1} 解析失败: {str(e)}")

        if not nodes:
            return (
                jsonify(
                    {"error": "所有节点解析都失败了", "errors": errors, "url": full_url}
                ),
                400,
            )

        # 合并到b.yaml（只追加proxies，其它内容保持原样）
        b_yaml_path = os.path.join(os.path.dirname(__file__), "b.yaml")
        yaml_ruamel = YAML()
        yaml_ruamel.preserve_quotes = True
        if os.path.exists(b_yaml_path):
            with open(b_yaml_path, "r", encoding="utf-8") as f:
                base_config = yaml_ruamel.load(f)
        else:
            base_config = yaml_ruamel.load("{}")
        # 只合并proxies，全部转为内嵌JSON（YAML flow style）
        proxies = list(base_config.get("proxies", []))
        proxies.extend(nodes)
        from ruamel.yaml.comments import CommentedSeq, CommentedMap

        def dict_to_flow_map(d):
            if not isinstance(d, dict):
                return d
            m = CommentedMap()
            for k, v in d.items():
                if isinstance(v, bool):
                    m[k] = v
                elif isinstance(v, dict):
                    m[k] = dict_to_flow_map(v)
                elif isinstance(v, list):
                    m[k] = CommentedSeq(
                        [dict_to_flow_map(i) if isinstance(i, dict) else i for i in v]
                    )
                    m[k].fa.set_flow_style()
                else:
                    m[k] = v
            m.fa.set_flow_style()
            return m

        proxies_flow = [
            dict_to_flow_map(p) if isinstance(p, dict) else p for p in proxies
        ]
        proxies_seq = CommentedSeq(proxies_flow)
        # 不设置 proxies_seq.fa.set_flow_style()，让它保持 block list
        base_config["proxies"] = proxies_seq
        # 生成合并后的YAML内容并写入临时文件
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml_ruamel.width = 4096  # 设置更大的换行宽度，默认80，4096足够长
            yaml_ruamel.dump(base_config, f)
            temp_file_path = f.name

        # 注册延迟清理回调
        create_cleanup_callback([temp_file_path])

        # 创建响应并添加订阅信息头部
        response = send_file(
            temp_file_path,
            as_attachment=True,
            download_name="config.yaml",
            mimetype="text/yaml",
        )
        if subscription_userinfo:
            response.headers["Subscription-Userinfo"] = subscription_userinfo
        return response

    except Exception as e:
        return (
            jsonify(
                {
                    "error": f"处理过程中发生错误: {str(e)}",
                    "url": full_url if "full_url" in locals() else url_path,
                }
            ),
            500,
        )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
