#!/usr/bin/env python3
"""
Flask应用 - 处理base64编码的节点信息，生成config.json
支持从URL参数获取base64编码数据，并将其节点注入到JSON模板中。
"""

import threading
import base64
import tempfile
import requests
import json
import re
import os
import sys
# 导入 Union 以支持多种返回类型
from typing import Any, Dict, List, Tuple, Union
from flask import Flask, request, jsonify, send_file, after_this_request, Response

TEMP_FILES = set()


# --------- 临时文件清理工具 ---------
def cleanup_files(file_list: List[str]):
    for f in file_list:
        try:
            os.remove(f)
            TEMP_FILES.discard(f)
            print(f"[临时文件清理] 删除成功: {f}", file=sys.stderr)
        except Exception as ex:
            print(f"[临时文件清理] 删除失败: {f}, 错误: {ex}", file=sys.stderr)


def create_cleanup_callback(temp_files: List[str], exclude_files: List[str] = None):
    @after_this_request
    def cleanup_callback(response: Response) -> Response:
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

        import time
        cleanup_thread = threading.Thread(target=delayed_cleanup, daemon=True)
        cleanup_thread.start()
        return response

    return cleanup_callback


# 动态导入解析器
try:
    from vless_converter import parse_vless_url
except ImportError:
    parse_vless_url = None
try:
    from ss_converter import parse_shadowsocks_url as parse_ss_url
except ImportError:
    parse_ss_url = None
try:
    from hysteria2_converter import parse_hysteria2_url
except ImportError:
    parse_hysteria2_url = None

app = Flask(__name__)


def decode_base64_content(content: str) -> str:
    try:
        content = content.replace("-", "+").replace("_", "/")
        padding = len(content) % 4
        if padding:
            content += "=" * (4 - padding)
        decoded_bytes = base64.b64decode(content)
        return decoded_bytes.decode("utf-8")
    except Exception as e:
        raise ValueError(f"Base64解码失败: {str(e)}")


def fetch_content_from_url(url: str) -> Tuple[str, str]:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0"
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        content = response.text.strip()
        decoded_content = decode_base64_content(content)
        return decoded_content, ""
    except Exception as e:
        raise ValueError(f"获取URL内容失败: {str(e)}")


def extract_urls_from_text(text: str) -> List[str]:
    urls = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if line and line.startswith(("vless://", "ss://", "hysteria2://", "hy2://")):
            urls.append(line)
    return urls


def parse_node_url(url: str) -> Dict[str, Any]:
    url = url.strip()
    if url.startswith("vless://"):
        if parse_vless_url:
            return parse_vless_url(url)
        raise ValueError("VLESS转换器未可用")
    elif url.startswith("ss://"):
        if parse_ss_url:
            return parse_ss_url(url)
        raise ValueError("SS转换器未可用")
    elif url.startswith(("hysteria2://", "hy2://")):
        if parse_hysteria2_url:
            return parse_hysteria2_url(url)
        raise ValueError("Hysteria2转换器未可用")
    else:
        raise ValueError(f"不支持的协议类型: {url[:20]}...")


@app.route("/<path:url_path>", methods=["GET"])
# FIX: Update the return type to allow for both Response and tuple[Response, int]
def process_nodes_from_path(url_path: str) -> Union[Response, Tuple[Response, int]]:
    full_url = url_path
    if request.query_string:
        query_part = request.query_string.decode("utf-8")
        full_url = f"{url_path}?{query_part}"

    try:
        decoded_content, _ = fetch_content_from_url(full_url)
        node_urls = extract_urls_from_text(decoded_content)
        if not node_urls:
            return jsonify({
                "error": "未找到有效的节点URL",
                "decoded_content": (decoded_content[:500] + "..." if len(decoded_content) > 500 else decoded_content),
                "url": full_url,
            }), 400

        nodes, errors = [], []
        for i, url in enumerate(node_urls):
            try:
                node_config = parse_node_url(url)
                if "name" in node_config and "tag" not in node_config:
                    node_config["tag"] = node_config["name"]
                nodes.append(node_config)
            except Exception as e:
                errors.append(f"节点 {i + 1} 解析失败: {str(e)}")

        if not nodes:
            return jsonify({"error": "所有节点解析都失败了", "errors": errors, "url": full_url}), 400

        config_path = os.path.join(os.path.dirname(__file__), "1.12.json")
        with open(config_path, "r", encoding="utf-8") as f:
            base_config = json.load(f)

        outbounds = base_config.get("outbounds", [])
        existing_tags = {o.get("tag") for o in outbounds}
        new_nodes = [n for n in nodes if n.get("tag") and n.get("tag") not in existing_tags]

        outbounds.extend(new_nodes)

        for outbound in outbounds:
            if outbound.get("type") == "urltest" and "filter" in outbound:
                regex_list = [reg for f in outbound.get("filter", []) for reg in f.get("regex", [])]
                if not regex_list:
                    del outbound["filter"]
                    continue

                pattern = "|".join(regex_list)
                try:
                    compiled = re.compile(pattern, re.IGNORECASE)
                    all_node_tags = [o.get("tag") for o in outbounds if
                                     o.get("tag") and o.get("type") not in ["urltest", "selector", "direct", "block"]]
                    matched_tags = [tag for tag in all_node_tags if compiled.search(tag)]

                    if matched_tags:
                        outbound["outbounds"] = matched_tags
                except re.error as e:
                    print(f"无效的正则表达式 '{pattern}': {e}", file=sys.stderr)
                    continue

                del outbound["filter"]

        base_config["outbounds"] = outbounds
        json_str = json.dumps(base_config, ensure_ascii=False, separators=(",", ":"))

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            f.write(json_str)
            temp_file_path = f.name
        TEMP_FILES.add(temp_file_path)

        create_cleanup_callback([temp_file_path])

        return send_file(
            temp_file_path,
            as_attachment=True,
            download_name="config.json",
            mimetype="application/json",
        )
    except Exception as e:
        # This now correctly matches the Union type hint
        return jsonify({
            "error": f"处理过程中发生错误: {str(e)}",
            "url": full_url,
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)