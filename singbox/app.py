#!/usr/bin/env python3
"""
Flask应用 - 处理base64编码的节点信息，生成config.yaml
支持从URL参数获取base64编码数据，解码后处理vless://节点信息
"""

from flask import Flask, request, jsonify, send_file
import base64
import tempfile
import requests

import json
import re
import os


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

def decode_base64_content(content):
    try:
        content = content.replace('-', '+').replace('_', '/')
        padding = len(content) % 4
        if padding:
            content += '=' * (4 - padding)
        decoded_bytes = base64.b64decode(content)
        return decoded_bytes.decode('utf-8')
    except Exception as e:
        raise ValueError(f"Base64解码失败: {str(e)}")


def fetch_content_from_url(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        content = response.text.strip()
        decoded_content = decode_base64_content(content)
        return decoded_content, ''
    except Exception as e:
        raise ValueError(f"获取URL内容失败: {str(e)}")

def extract_urls_from_text(text):
    urls = []
    for line in text.strip().split('\n'):
        line = line.strip()
        if line and line.startswith(('vless://', 'ss://', 'hysteria2://', 'hy2://')):
            urls.append(line)
    return urls

def parse_node_url(url):
    url = url.strip()
    if url.startswith('vless://'):
        if parse_vless_url:
            return parse_vless_url(url)
        else:
            raise ValueError("VLESS转换器未可用")
    elif url.startswith('ss://'):
        if parse_ss_url:
            return parse_ss_url(url)
        else:
            raise ValueError("SS转换器未可用")
    elif url.startswith(('hysteria2://', 'hy2://')):
        if parse_hysteria2_url:
            return parse_hysteria2_url(url)
        else:
            raise ValueError("Hysteria2转换器未可用")
    else:
        raise ValueError(f"不支持的协议类型: {url[:20]}...")




@app.route('/<path:url_path>', methods=['GET'])
def process_nodes_from_path(url_path):
    try:
        full_url = url_path
        if request.query_string:
            query_part = request.query_string.decode('utf-8')
            full_url = f"{url_path}?{query_part}"
        try:
            decoded_content, _ = fetch_content_from_url(full_url)
        except ValueError as e:
            return jsonify({'error': str(e), 'url': full_url}), 400
        node_urls = extract_urls_from_text(decoded_content)
        if not node_urls:
            return jsonify({'error': '未找到有效的节点URL', 'decoded_content': decoded_content[:500] + '...' if len(decoded_content) > 500 else decoded_content, 'url': full_url}), 400
        nodes = []
        errors = []
        for i, url in enumerate(node_urls):
            try:
                node_config = parse_node_url(url)
                nodes.append(node_config)
            except Exception as e:
                errors.append(f"节点 {i+1} 解析失败: {str(e)}")
        if not nodes:
            return jsonify({'error': '所有节点解析都失败了', 'errors': errors, 'url': full_url}), 400
        # 合并到1.12.json并替换urltest的outbounds
        config_path = os.path.join(os.path.dirname(__file__), '1.12.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            base_config = json.load(f)
        # 保留原有outbounds
        outbounds = base_config.get('outbounds', [])
        # 只追加新节点（避免重复tag）
        existing_tags = {o.get('tag') for o in outbounds}
        new_nodes = [n for n in nodes if n.get('tag') not in existing_tags]
        outbounds += new_nodes
        # 替换urltest的outbounds字段
        for outbound in outbounds:
            if outbound.get('type') == 'urltest' and 'filter' in outbound:
                regex_list = []
                for f in outbound['filter']:
                    regex_list += f.get('regex', [])
                if regex_list:
                    pattern = '|'.join(regex_list)
                    try:
                        compiled = re.compile(pattern, re.IGNORECASE)
                    except Exception:
                        continue
                    matched_tags = [n['tag'] for n in new_nodes if compiled.search(n['tag'])]
                    if matched_tags:
                        outbound['outbounds'] = matched_tags
                # 替换后删除filter字段
                del outbound['filter']
        base_config['outbounds'] = outbounds
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(base_config, f, ensure_ascii=False, indent=2)
            temp_file_path = f.name
        response = send_file(temp_file_path, as_attachment=True, download_name='config.json', mimetype='application/json')
        return response
    except Exception as e:
        return jsonify({'error': f'处理过程中发生错误: {str(e)}', 'url': full_url if 'full_url' in locals() else url_path}), 500
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)