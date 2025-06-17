from flask import Flask, send_file, after_this_request, request
import requests
from urllib.parse import unquote
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

# 添加调试输出
logger.info(f"加载环境变量文件: {env_path}")
logger.info(f"TEMPLATE_MODE: {os.getenv('TEMPLATE_MODE', '未设置')}")

# 常量定义
USER_AGENT = os.getenv('USER_AGENT', 'sing-box')
UPLOAD_MBPS = int(os.getenv('UPLOAD_MBPS', 50))
DOWNLOAD_MBPS = int(os.getenv('DOWNLOAD_MBPS', 300))

# 路径配置
BASE_DIR = Path(__file__).parent
OUTPUT_FOLDER = BASE_DIR / 'outputs'

# 模板映射
TEMPLATE_MAP = {
    'tproxy': BASE_DIR / 'template' / 'tproxy_1.11.json',  # tproxy模式
    'tun': BASE_DIR / 'template' / 'tun_1.11.json',       # tun模式
    'shouji': BASE_DIR / 'template' / 'tproxy_1.11_shouji.json'  # 手机tproxy模式
}

# 重新获取环境变量值 - 默认为 'tproxy'
template_mode = os.getenv('TEMPLATE_MODE', 'tproxy')
DEFAULT_TEMPLATE = TEMPLATE_MAP[template_mode]
logger.info(f"使用默认模板: {DEFAULT_TEMPLATE}")

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
                    
                # 检查并更新 server_ports
                node_key = (item.get('type'), item.get('tag'))
                if node_key in ports_map:
                    # 删除 server_port 字段
                    if 'server_port' in item:
                        del item['server_port']
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
                    group_name = outbound.get('tag', '未知分组')
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

def create_cleanup_callback(temp_files):
    @after_this_request
    def cleanup_callback(response):
        cleanup_files(temp_files)
        return response
    return cleanup_callback

@app.route('/<path:sub_url>')
def process_subscription_url(sub_url):
    temp_files = []
    try:
        # 更明确地获取和记录环境变量值
        env_template_mode = os.getenv('TEMPLATE_MODE', 'tproxy')
        template_switch = request.args.get('switch', env_template_mode)
        
        logger.info(f"URL参数switch: {request.args.get('switch', '未提供')}")
        logger.info(f"环境变量TEMPLATE_MODE: {env_template_mode}")
        logger.info(f"最终使用的模板模式: {template_switch}")
        
        template_path = TEMPLATE_MAP.get(template_switch, DEFAULT_TEMPLATE)
        
        sub_url = unquote(sub_url)
        if not sub_url.startswith(('http://', 'https://')):
            sub_url = 'https://' + sub_url
            
        temp_path = fetch_subscription(sub_url)
        temp_files.append(temp_path)
        
        # 修改process_subscription函数调用，传入模板路径
        output_path, node_path = process_subscription(temp_path, template_path)
        temp_files.extend([output_path, node_path])
        
        # 准备响应
        response = send_file(
            output_path,
            mimetype='application/json',
            as_attachment=True,
            download_name='config.json'
        )
        
        # 使用新的清理回调方式
        create_cleanup_callback(temp_files)
        
        return response
        
    except Exception as error:
        return f'处理失败: {str(error)}', 500
    finally:
        # 无论是否发生异常，都确保清理临时文件
        cleanup_files(temp_files)

def cleanup_files(file_paths):
    """清理临时文件"""
    for file_path in file_paths:
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"清理临时文件: {file_path}")
        except Exception as error:
            logger.error(f"清理文件失败 {file_path}: {str(error)}")

if __name__ == '__main__':
    debug_mode = os.getenv('DEBUG', 'True').lower() in ('true', '1', 't')
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    
    # 添加环境变量调试输出
    template_mode = os.getenv('TEMPLATE_MODE', '1')
    logger.info(f"当前TEMPLATE_MODE: {template_mode}")
    logger.info(f"默认模板: {DEFAULT_TEMPLATE}")
    
    app.run(debug=debug_mode, port=port, host=host)
