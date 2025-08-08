from flask import Flask, send_file, after_this_request, request
import requests
import json
import logging
import uuid
import os
from pathlib import Path
from dotenv import load_dotenv
import re
# 设置日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 加载.env文件 - 使用明确的路径并强制覆盖
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

logger.info(f"加载环境变量文件: {env_path}")

# 常量定义
USER_AGENT = os.getenv('USER_AGENT', 'sing-box')
UPLOAD_MBPS = int(os.getenv('UPLOAD_MBPS', 50))
DOWNLOAD_MBPS = int(os.getenv('DOWNLOAD_MBPS', 300))


# 路径配置
BASE_DIR = Path(__file__).parent
OUTPUT_FOLDER = BASE_DIR / 'outputs'

# 从.env读取模板文件名，默认为1.12.json
TEMPLATE_FILE = os.getenv('TEMPLATE_FILE', '1.12.json')
TEMPLATE_PATH = BASE_DIR / 'template' / TEMPLATE_FILE

logger.info(f"使用模板文件: {TEMPLATE_FILE}")
logger.info(f"模板路径: {TEMPLATE_PATH}")

app = Flask(__name__)

# 确保输出目录存在
OUTPUT_FOLDER.mkdir(exist_ok=True)

def get_unique_filepath(prefix, suffix):
    """生成唯一的文件路径"""
    return OUTPUT_FOLDER / f"{prefix}_{uuid.uuid4().hex}{suffix}"

def fetch_subscription(url):
    """获取订阅内容并缓存到本地outputs目录"""
    temp_path = get_unique_filepath("temp", ".json")
    
    try:
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # 保存响应内容
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        logger.info(f"成功获取订阅内容并保存到: {temp_path}")
        return temp_path
            
    except requests.exceptions.RequestException as error:
        if temp_path.exists():
            temp_path.unlink()
        logger.error(f"下载订阅失败: {str(error)}")
        raise

def process_subscription(sub_path, template_path):
    """处理本地订阅文件"""
    output_path = get_unique_filepath("config", ".json")
    node_path = get_unique_filepath("node", ".json")
    
    try:
        logger.info(f"开始处理本地订阅文件: {sub_path}")
        logger.info(f"使用模板文件: {template_path}")
        # 1. 读取订阅数据
        with open(sub_path, 'r', encoding='utf-8') as f:
            sub_data = json.load(f)

        # 读取 ports.json
        ports_file = BASE_DIR / 'template' / 'ports.json'
        ports_map = {}
        if ports_file.exists():
            with open(ports_file, 'r', encoding='utf-8') as f:
                ports_data = json.load(f)
                # 创建端口映射字典 {(type, tag): server_ports}
                for node in ports_data.get('outbounds', []):
                    if 'type' in node and 'tag' in node and 'server_ports' in node:
                        ports_map[(node['type'], node['tag'])] = node['server_ports']

        # 2. 提取节点标签并保存到 node.json
        node_tags = []
        seen_tags = set()
        sub_outbounds = []
        
        # 从订阅数据中提取节点配置
        for item in sub_data.get('outbounds', []):
            if (item.get('type') not in ['selector', 'urltest', 'direct', 'block', 'dns'] and 
                item.get('tag', '') and 
                item.get('tag') not in seen_tags):
                if item.get('type') == 'hysteria2':
                    item['up_mbps'] = UPLOAD_MBPS
                    item['down_mbps'] = DOWNLOAD_MBPS

                # 替换 packet_encoding 为 xudp 以提升性能
                if item.get('packet_encoding') == 'packetaddr':
                    item['packet_encoding'] = 'xudp'

                # 删除 flow 为空字符串的字段
                if 'flow' in item and item['flow'] == "":
                    del item['flow']
                    
                # 检查并更新 server_ports
                node_key = (item.get('type'), item.get('tag'))
                if node_key in ports_map:
                    # 添加 server_ports 字段    
                    item['server_ports'] = ports_map[node_key]
                    logger.info(f"更新节点 {item['tag']} 的 server_ports: {ports_map[node_key]}")
                
                seen_tags.add(item['tag'])
                node_tags.append(item['tag'])
                sub_outbounds.append(item)
                logger.info(f"提取节点: {item['tag']}")

        # 保存节点标签
        with open(node_path, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(node_tags, f, indent=2, ensure_ascii=False)
        logger.info(f"保存节点标签到: {node_path}")
            
        # 3. 读取模板
        with open(template_path, 'r', encoding='utf-8') as f:
            template_data = json.load(f)

        # 4. 处理代理组中的节点分配
        for outbound in template_data['outbounds']:
            if isinstance(outbound.get('outbounds'), list) and '{all}' in outbound['outbounds']:
                fixed_outbounds = [o for o in outbound['outbounds'] if o != '{all}']
                group_name = outbound.get('tag', '未知分组')
                
                if 'filter' in outbound:
                    filtered_tags = set()
                    logger.info(f"分组 [{group_name}] 过滤规则: {json.dumps(outbound['filter'], ensure_ascii=False)}")
                    
                    for f in outbound['filter']:
                        if f.get('action') == 'match' and 'regex' in f:
                            patterns = f['regex']
                            if isinstance(patterns, str):
                                patterns = [patterns]
                            
                            for pattern in patterns:
                                regex = re.compile(pattern)
                                matched = {tag for tag in node_tags if regex.search(tag)}
                                filtered_tags.update(matched)
                                if matched:
                                    logger.info(f"分组 [{group_name}] 正则 '{pattern}' 匹配到节点: {matched}")
                    
                    outbound['outbounds'] = fixed_outbounds + sorted(list(filtered_tags))
                    logger.info(f"分组 [{group_name}] 过滤后节点数: {len(filtered_tags)}")
                else:
                    outbound['outbounds'] = fixed_outbounds + sorted(node_tags)
                    logger.info(f"分组 [{group_name}] 使用全部节点: {len(node_tags)}")
                
                if 'filter' in outbound:
                    del outbound['filter']

        # 5. 重新组合配置
        basic_outbounds = [o for o in template_data['outbounds'] if o.get('type') in ['direct', 'block', 'dns']]
        template_outbounds = [o for o in template_data['outbounds'] if o.get('type') not in ['direct', 'block', 'dns']]
        template_data['outbounds'] = basic_outbounds + sub_outbounds + template_outbounds

        # 6. 保存最终配置
        with open(output_path, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(template_data, f, indent=2, ensure_ascii=False)
        logger.info(f"保存最终配置到: {output_path}")
        
        return output_path, node_path
        
    except Exception as error:
        if output_path.exists():
            output_path.unlink()
        if node_path.exists():
            node_path.unlink()
        logger.error(f"处理订阅文件失败: {str(error)}")
        raise
    finally:
        if sub_path.exists():
            sub_path.unlink()
            logger.info(f"清理临时文件: {sub_path}")

def create_cleanup_callback(temp_files, exclude_files=None):
    @after_this_request
    def cleanup_callback(response):
        # 延迟清理，确保文件传输完成
        import threading
        import time
        
        def delayed_cleanup():
            time.sleep(2)  # 等待2秒确保文件传输完成
            files_to_clean = temp_files.copy()
            if exclude_files:
                # 从清理列表中排除正在使用的文件
                for exclude_file in exclude_files:
                    if exclude_file in files_to_clean:
                        files_to_clean.remove(exclude_file)
            cleanup_files(files_to_clean)
            
            # 最后清理被排除的文件
            if exclude_files:
                time.sleep(1)  # 再等待1秒
                cleanup_files(exclude_files)
        
        # 使用新线程进行延迟清理
        cleanup_thread = threading.Thread(target=delayed_cleanup, daemon=True)
        cleanup_thread.start()
        return response
    return cleanup_callback

@app.route('/<path:sub_url>')
def process_subscription_url(sub_url):
    temp_files = []
    try:
        # 只使用1.12模板
        template_path = TEMPLATE_PATH
        
        # 重构完整URL，包括查询参数，避免被截断
        query_string = request.query_string.decode('utf-8')
        if query_string:
            full_url = f"{sub_url}?{query_string}"
        else:
            full_url = sub_url
        
        # 直接使用URL，不需要解码
        temp_path = fetch_subscription(full_url)
        temp_files.append(temp_path)
        
        output_path, node_path = process_subscription(temp_path, template_path)
        temp_files.extend([output_path, node_path])
        
        response = send_file(
            output_path,
            mimetype='application/json',
            as_attachment=True,
            download_name='config.json'
        )
        create_cleanup_callback(temp_files, exclude_files=[output_path])
        return response
    except Exception as error:
        cleanup_files(temp_files)
        return f'处理失败: {str(error)}', 500

def cleanup_files(file_paths):
    """清理临时文件"""
    if not file_paths:
        return
        
    import time
    
    for file_path in file_paths:
        if not file_path:
            continue
            
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"清理临时文件: {file_path}")
                    break
                else:
                    logger.debug(f"文件不存在，跳过清理: {file_path}")
                    break
            except PermissionError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"文件被占用，等待后重试 ({attempt + 1}/{max_retries}): {file_path}")
                    time.sleep(0.5)  # 等待0.5秒后重试
                else:
                    logger.error(f"清理文件失败，文件被占用: {file_path}")
            except Exception as error:
                logger.error(f"清理文件失败 {file_path}: {str(error)}")
                break

if __name__ == '__main__':
    debug_mode = os.getenv('DEBUG', 'True').lower() in ('true', '1', 't')
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    logger.info(f"启动应用 - 模板文件: {TEMPLATE_FILE}, 端口: {port}")
    app.run(debug=debug_mode, port=port, host=host)
