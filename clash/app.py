from flask import Flask, send_file, after_this_request, request
from ruamel.yaml import YAML
import requests
from urllib.parse import unquote
import json
import time
import threading
from datetime import datetime, timedelta
from filelock import FileLock
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

app = Flask(__name__)

# 基础配置
BASE_DIR = Path(os.getenv('BASE_DIR', '.')).absolute()
OUTPUT_FOLDER = BASE_DIR / os.getenv('OUTPUT_FOLDER', 'outputs')
TEMPLATE_PATH = BASE_DIR / os.getenv('TEMPLATE_PATH', 'template/b.yaml')
PORTS_PATH = BASE_DIR / os.getenv('PORTS_PATH', 'template/ports.yaml')
HEADERS_CACHE_PATH = OUTPUT_FOLDER / 'headers_cache.json'
TEMP_YAML_PATH = OUTPUT_FOLDER / 'temp.yaml'
TEMP_YAML_LOCK = OUTPUT_FOLDER / 'temp.yaml.lock'

USER_AGENT = os.getenv('USER_AGENT', 'clash verge')
CACHE_DURATION = int(os.getenv('CACHE_DURATION', 300))
HYSTERIA2_UP = os.getenv('HYSTERIA2_UP', '50 Mbps')
HYSTERIA2_DOWN = os.getenv('HYSTERIA2_DOWN', '300 Mbps')
INCLUDED_HEADERS = set(os.getenv('INCLUDED_HEADERS', 'Subscription-Userinfo').split(','))

# 节点替换功能开关
ENABLE_NODE_REPLACEMENT = os.getenv('ENABLE_NODE_REPLACEMENT', 'false').lower() == 'true'

# 确保输出目录存在
OUTPUT_FOLDER.mkdir(exist_ok=True)

# 验证必要文件存在
if not TEMPLATE_PATH.exists():
    raise FileNotFoundError(f"模板文件不存在: {TEMPLATE_PATH}")

# YAML 配置
yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def save_headers_cache(url, headers):
    """保存请求头缓存，仅保存白名单中的header"""
    try:
        if HEADERS_CACHE_PATH.exists():
            with open(HEADERS_CACHE_PATH, 'r', encoding='utf-8') as f:
                cache = json.load(f)
        else:
            cache = {}
        
        filtered_headers = {k: v for k, v in headers.items() 
                          if k.lower() in {h.lower() for h in INCLUDED_HEADERS}}
        
        cache[url] = {
            'headers': filtered_headers,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(HEADERS_CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"保存headers缓存失败: {e}")

def get_headers_cache(url):
    """获取指定URL的headers缓存，检查是否过期"""
    try:
        if HEADERS_CACHE_PATH.exists():
            with open(HEADERS_CACHE_PATH, 'r', encoding='utf-8') as f:
                cache = json.load(f)
                if url in cache:
                    cache_time = datetime.fromisoformat(cache[url]['timestamp'])
                    if datetime.now() - cache_time < timedelta(seconds=CACHE_DURATION):
                        return cache[url]['headers']
    except Exception as e:
        logger.error(f"读取headers缓存失败: {e}")
    return None

def fetch_yaml(url):
    """获取 YAML 内容并缓存到本地"""
    temp_path = TEMP_YAML_PATH.with_suffix('.tmp')
    
    with FileLock(TEMP_YAML_LOCK):
        try:
            headers = {'User-Agent': USER_AGENT}
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            save_headers_cache(url, response.headers)
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            if not temp_path.exists() or os.path.getsize(temp_path) == 0:
                raise IOError("临时文件写入失败")
                
            if TEMP_YAML_PATH.exists():
                TEMP_YAML_PATH.unlink()
            temp_path.rename(TEMP_YAML_PATH)
            
            logger.info(f"成功缓存YAML文件: {url}")
            return TEMP_YAML_PATH
            
        except Exception as e:
            logger.error(f"获取YAML失败: {str(e)}")
            if temp_path.exists():
                temp_path.unlink()
            raise

def save_node_names(proxies):
    """提取节点名称并保存到nodes.yaml文件"""
    try:
        # 提取所有代理节点的名称
        node_names = []
        for proxy in proxies:
            if isinstance(proxy, dict) and 'name' in proxy:
                node_names.append(proxy['name'])
        
        # 准备要保存的数据结构
        nodes_data = {
            'node_names': node_names,
            'total': len(node_names),
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 配置YAML输出格式
        nodes_yaml = YAML()
        nodes_yaml.indent(mapping=2, sequence=4, offset=2)
        nodes_yaml.preserve_quotes = True
        nodes_yaml.width = 4096
        
        # 保存到nodes.yaml
        nodes_path = OUTPUT_FOLDER / 'nodes.yaml'
        with open(nodes_path, 'w', encoding='utf-8') as f:
            nodes_yaml.dump(nodes_data, f)
            
        logger.info(f"成功保存节点名称到 {nodes_path}, 共 {len(node_names)} 个节点")
        return nodes_path
    except Exception as e:
        logger.error(f"保存节点名称失败: {str(e)}")
        return None

def replace_proxy_groups_with_nodes(template_data):
    """将代理组中的US_fallback、HK_fallback、SG_fallback和JP_fallback替换为实际节点"""
    try:
        # 检查nodes.yaml是否存在
        nodes_path = OUTPUT_FOLDER / 'nodes.yaml'
        if not nodes_path.exists():
            logger.warning("nodes.yaml不存在，无法替换节点")
            return template_data
            
        # 读取nodes.yaml获取所有节点名称
        nodes_yaml = YAML()
        with open(nodes_path, 'r', encoding='utf-8') as f:
            nodes_data = nodes_yaml.load(f)
            
        # 获取节点名称列表
        node_names = nodes_data.get('node_names', [])
        if not node_names:
            logger.warning("nodes.yaml中未找到节点名称")
            return template_data
            
        # 筛选US节点
        us_nodes = [name for name in node_names 
                   if (('US' in name.upper() or '美国' in name) and name != 'US')]
        us_nodes = list(dict.fromkeys(us_nodes))
        
        # 筛选HK节点
        hk_nodes = [name for name in node_names 
                   if (('HK' in name.upper() or '香港' in name) and name != 'HK')]
        hk_nodes = list(dict.fromkeys(hk_nodes))
        
        # 筛选SG节点
        sg_nodes = [name for name in node_names 
                   if (('SG' in name.upper() or '新加坡' in name or 'Singapore' in name) and name != 'SG')]
        sg_nodes = list(dict.fromkeys(sg_nodes))
        
        # 筛选JP节点
        jp_nodes = [name for name in node_names 
                   if (('JP' in name.upper() or '日本' in name or 'Japan' in name) and name != 'JP')]
        jp_nodes = list(dict.fromkeys(jp_nodes))
        
        logger.info(f"找到 {len(us_nodes)} 个US节点, {len(hk_nodes)} 个HK节点, {len(sg_nodes)} 个SG节点, {len(jp_nodes)} 个JP节点")
        
        # 处理代理组
        proxy_groups = template_data.get('proxy-groups', [])
        for group in proxy_groups:
            if isinstance(group, dict) and group.get('type') == 'fallback' and 'proxies' in group:
                proxies = group['proxies']
                
                # 替换US_fallback节点
                if 'US_fallback' in proxies and us_nodes:
                    index = proxies.index('US_fallback')
                    filtered_us_nodes = [node for node in us_nodes if node not in proxies]
                    
                    if filtered_us_nodes:
                        proxies.pop(index)
                        for i, node in enumerate(filtered_us_nodes):
                            proxies.insert(index + i, node)
                        logger.info(f"在代理组 '{group.get('name', '未命名')}' 中替换US_fallback为 {len(filtered_us_nodes)} 个实际节点")
                
                # 替换HK_fallback节点
                if 'HK_fallback' in proxies and hk_nodes:
                    index = proxies.index('HK_fallback')
                    filtered_hk_nodes = [node for node in hk_nodes if node not in proxies]
                    
                    if filtered_hk_nodes:
                        proxies.pop(index)
                        for i, node in enumerate(filtered_hk_nodes):
                            proxies.insert(index + i, node)
                        logger.info(f"在代理组 '{group.get('name', '未命名')}' 中替换HK_fallback为 {len(filtered_hk_nodes)} 个实际节点")
                
                # 替换SG_fallback节点
                if 'SG_fallback' in proxies and sg_nodes:
                    index = proxies.index('SG_fallback')
                    filtered_sg_nodes = [node for node in sg_nodes if node not in proxies]
                    
                    if filtered_sg_nodes:
                        proxies.pop(index)
                        for i, node in enumerate(filtered_sg_nodes):
                            proxies.insert(index + i, node)
                        logger.info(f"在代理组 '{group.get('name', '未命名')}' 中替换SG_fallback为 {len(filtered_sg_nodes)} 个实际节点")
                
                # 替换JP_fallback节点
                if 'JP_fallback' in proxies and jp_nodes:
                    index = proxies.index('JP_fallback')
                    filtered_jp_nodes = [node for node in jp_nodes if node not in proxies]
                    
                    if filtered_jp_nodes:
                        proxies.pop(index)
                        for i, node in enumerate(filtered_jp_nodes):
                            proxies.insert(index + i, node)
                        logger.info(f"在代理组 '{group.get('name', '未命名')}' 中替换JP_fallback为 {len(filtered_jp_nodes)} 个实际节点")
                

        
        return template_data
    except Exception as e:
        logger.error(f"替换代理组节点失败: {str(e)}")
        return template_data

def process_yaml_content(yaml_path):
    """处理本地YAML文件"""
    try:
        # 读取输入的YAML
        with open(yaml_path, 'r', encoding='utf-8') as f:
            input_data = yaml.load(f)
        
        if not isinstance(input_data, dict):
            raise ValueError('YAML内容必须是有效的字典格式')
            
        # 读取标准模板
        with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
            template_data = yaml.load(f)

        # 读取ports配置
        with open(PORTS_PATH, 'r', encoding='utf-8') as f:
            ports_data = yaml.load(f)
            
        ports_config = {proxy['name']: proxy['ports'] 
                       for proxy in ports_data.get('proxies', [])}
        
        proxies = input_data.get('proxies', [])
        if not proxies:
            raise ValueError('YAML文件中未找到有效的proxies配置')
            
        # 处理代理配置
        for proxy in proxies:
            if isinstance(proxy, dict):
                if proxy.get('type') == 'hysteria2':
                    proxy['up'] = HYSTERIA2_UP
                    proxy['down'] = HYSTERIA2_DOWN
                    proxy['skip-cert-verify'] = False
                    # 检查是否存在匹配的端口配置
                    if proxy.get('name') in ports_config:
                        proxy['ports'] = ports_config[proxy['name']]
                        proxy.pop('port', None)
                elif proxy.get('type') == 'vless':
                    proxy['skip-cert-verify'] = False
                    proxy['packet-encoding'] = 'xudp'
        
        # 提取节点名称并保存（如果启用了节点替换功能）
        if ENABLE_NODE_REPLACEMENT:
            save_node_names(proxies)
        
        # 更新模板中的代理列表
        template_data['proxies'] = proxies
        
        # 替换代理组中的节点（如果启用了节点替换功能）
        if ENABLE_NODE_REPLACEMENT:
            template_data = replace_proxy_groups_with_nodes(template_data)
        
        # 配置YAML输出格式
        yaml.indent(mapping=2, sequence=4, offset=2)
        yaml.preserve_quotes = True
        yaml.width = 4096  # 避免自动换行
        
        # 保存处理后的YAML
        output_path = OUTPUT_FOLDER / 'config.yaml'
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(template_data, f)
            
        return output_path
        
    except Exception as e:
        logger.error(f"处理YAML内容失败: {str(e)}")
        raise

def cleanup_files(*paths):
    """清理指定的文件"""
    for path in paths:
        try:
            path_obj = Path(path) if isinstance(path, str) else path
            if path_obj and path_obj.exists():
                path_obj.unlink()
                logger.info(f"成功删除文件: {path}")
        except Exception as e:
            logger.error(f"清理文件失败 {path}: {str(e)}")

def cleanup_response(response, *file_paths):
    """处理响应后的清理函数"""
    def delayed_cleanup():
        logger.info("开始执行延迟清理...")
        time.sleep(30)  # 等待30秒后删除文件
        cleanup_files(*file_paths, HEADERS_CACHE_PATH)
        logger.info("文件清理完成")
        
    threading.Thread(target=delayed_cleanup, daemon=True).start()
    return response

@app.route('/<path:yaml_url>')
def process_yaml(yaml_url):
    temp_yaml_path = None
    output_path = None
    
    try:
        yaml_url = unquote(yaml_url)
        
        # 确保URL以https://开头
        if not yaml_url.startswith('https://'):
            yaml_url = 'https://' + yaml_url.lstrip('/')
        
        temp_yaml_path = fetch_yaml(yaml_url)
        output_path = process_yaml_content(temp_yaml_path)
        cached_headers = get_headers_cache(yaml_url)
        
        response = send_file(
            output_path,
            mimetype='application/yaml',
            as_attachment=True,
            download_name='config.yaml'
        )
        
        response.headers['Content-Type'] = 'application/yaml; charset=utf-8'
        
        if cached_headers:
            for header, value in cached_headers.items():
                if header.lower() in {h.lower() for h in INCLUDED_HEADERS}:
                    response.headers[header] = value
        
        # 设置清理任务
        @after_this_request
        def cleanup(response):
            return cleanup_response(response, temp_yaml_path, output_path)
        
        return response
        
    except Exception as e:
        cleanup_files(temp_yaml_path, output_path)
        logger.error(f"处理请求失败: {str(e)}")
        return str(e), 500

if __name__ == '__main__':
    debug_mode = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')
    port = int(os.getenv('PORT', 5002))
    host = os.getenv('HOST', '0.0.0.0')
    
    app.run(debug=debug_mode, port=port, host=host)


