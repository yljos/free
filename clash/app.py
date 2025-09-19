#!/usr/bin/env python3
"""
Flask应用 - 处理base64编码的节点信息，生成config.yaml
支持从URL参数获取base64编码数据，解码后处理vless://节点信息
"""


from flask import Flask, request, jsonify, send_file, after_this_request
import base64
import os
import tempfile
import requests
from ruamel.yaml import YAML


# --------- 临时文件清理工具 ---------
def cleanup_files(file_list):
    import os, sys

    for f in file_list:
        try:
            os.remove(f)
            print(f"[临时文件清理] 删除成功: {f}", file=sys.stderr)
        except Exception as ex:
            print(f"[临时文件清理] 删除失败: {f}, 错误: {ex}", file=sys.stderr)


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
                time.sleep(1)
                cleanup_files(exclude_files)

        cleanup_thread = threading.Thread(target=delayed_cleanup, daemon=True)
        cleanup_thread.start()
        return response

    return cleanup_callback


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
    """解码base64内容"""
    try:
        content = content.replace("-", "+").replace("_", "/")
        padding = len(content) % 4
        if padding:
            content += "=" * (4 - padding)
        decoded_bytes = base64.b64decode(content)
        return decoded_bytes.decode("utf-8")
    except Exception as e:
        raise ValueError(f"Base64解码失败: {str(e)}")


def fetch_subscription_info(url):
    """使用clash verge User-Agent获取订阅信息"""
    try:
        headers = {"User-Agent": "clash-verge"}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.headers.get("Subscription-Userinfo", "")
    except Exception as e:
        print(f"获取订阅信息失败: {str(e)}")
        return ""


def fetch_content_from_url(url):
    """从URL获取base64编码的内容并解码"""
    try:
        subscription_userinfo = fetch_subscription_info(url)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0"
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        content = response.text.strip()
        decoded_content = decode_base64_content(content)
        return decoded_content, subscription_userinfo
    except Exception as e:
        raise ValueError(f"获取URL内容失败: {str(e)}")


def extract_urls_from_text(text):
    """从文本中提取所有节点URL"""
    urls = []
    lines = text.strip().split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith(("vless://", "ss://", "hysteria2://", "hy2://")):
            urls.append(line)
    return urls


def parse_node_url(url):
    """根据协议类型解析节点URL"""
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


@app.route("/", methods=["GET"])
def index():
    return "", 200


@app.route("/<path:url_path>", methods=["GET"])
def process_nodes_from_path(url_path):
    """通过路径参数处理节点信息并生成config.yaml"""
    # 修正 1: 在 try 块外部初始化 full_url，确保其总有值
    full_url = url_path
    if request.query_string:
        query_part = request.query_string.decode("utf-8")
        full_url = f"{url_path}?{query_part}"

    try:
        # 从URL获取内容
        decoded_content, subscription_userinfo = fetch_content_from_url(full_url)

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
        nodes, errors = [], []
        # 修正 2: 将 'i' 重命名为 'idx' 避免变量遮蔽
        for idx, url in enumerate(node_urls):
            try:
                node_config = parse_node_url(url)
                nodes.append(node_config)
            except Exception as e:
                errors.append(f"节点 {idx + 1} 解析失败: {str(e)}")

        if not nodes:
            return (
                jsonify(
                    {"error": "所有节点解析都失败了", "errors": errors, "url": full_url}
                ),
                400,
            )

        # 合并到b.yaml
        b_yaml_path = os.path.join(os.path.dirname(__file__), "b.yaml")
        yaml_ruamel = YAML()
        yaml_ruamel.preserve_quotes = True
        base_config = (
            yaml_ruamel.load(open(b_yaml_path, "r", encoding="utf-8"))
            if os.path.exists(b_yaml_path)
            else yaml_ruamel.load("{}")
        )

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
        base_config["proxies"] = CommentedSeq(proxies_flow)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml_ruamel.width = 4096
            yaml_ruamel.dump(base_config, f)
            temp_file_path = f.name

        create_cleanup_callback([temp_file_path])
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
        return jsonify({"error": f"处理过程中发生错误: {str(e)}", "url": full_url}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
