from flask import Flask, send_file
import requests
from urllib.parse import unquote
from pathlib import Path
import json
import logging
import threading
import uuid
import time

app = Flask(__name__)

# 常量定义
USER_AGENT = 'sing-box'

# 使用 Path 对象处理路径
BASE_DIR = Path(__file__).parent
OUTPUT_FOLDER = BASE_DIR / 'outputs'
TEMPLATE_PATH = BASE_DIR / 'template' / 'tun_1.10.json'

# 确保输出目录存在
OUTPUT_FOLDER.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
            
    except requests.exceptions.RequestException as e:
        if temp_path.exists():
            temp_path.unlink()
        logger.error(f"下载订阅失败: {str(e)}")
        raise

def process_subscription(sub_path):
    """处理本地订阅文件"""
    output_path = get_unique_filepath("config", ".json")
    node_path = get_unique_filepath("node", ".json")
    
    try:
        logger.info(f"开始处理本地订阅文件: {sub_path}")
        # 1. 读取订阅数据
        with open(sub_path, 'r', encoding='utf-8') as f:
            sub_data = json.load(f)

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
                    item['up_mbps'] = 50
                    item['down_mbps'] = 300
                seen_tags.add(item['tag'])
                node_tags.append(item['tag'])
                sub_outbounds.append(item)
                logger.info(f"提取节点: {item['tag']}")

        # 保存节点标签
        with open(node_path, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(node_tags, f, indent=2, ensure_ascii=False)
        logger.info(f"保存节点标签到: {node_path}")
            
        # 3. 读取模板
        with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
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
                        keywords = []
                        raw_keywords = f.get('keywords', '')
                        if isinstance(raw_keywords, str):
                            keywords = raw_keywords.split('|')
                        elif isinstance(raw_keywords, list):
                            for k in raw_keywords:
                                keywords.extend(k.split('|'))
                                
                        if f.get('action') == 'exclude':
                            if not filtered_tags:
                                filtered_tags = set(node_tags)
                            excluded = {tag for tag in filtered_tags 
                                      if any(k.lower() in tag.lower() for k in keywords)}
                            filtered_tags -= excluded
                            if excluded:
                                logger.info(f"分组 [{group_name}] 排除节点: {excluded}")
                                
                        elif f.get('action') == 'include':
                            matched = {tag for tag in node_tags 
                                     if any(k.lower() in tag.lower() for k in keywords)}
                            filtered_tags.update(matched)
                            if matched:
                                logger.info(f"分组 [{group_name}] 包含节点: {matched}")
                    
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
        
    except Exception as e:
        if output_path.exists():
            output_path.unlink()
        if node_path.exists():
            node_path.unlink()
        raise
    finally:
        if sub_path.exists():
            sub_path.unlink()
            logger.info(f"清理临时文件: {sub_path}")

@app.route('/<path:sub_url>')
def process_subscription_url(sub_url):
    temp_files = []
    try:
        sub_url = unquote(sub_url)
        if not sub_url.startswith(('http://', 'https://')):
            sub_url = 'https://' + sub_url
            
        temp_path = fetch_subscription(sub_url)
        temp_files.append(temp_path)
        
        output_path, node_path = process_subscription(temp_path)
        temp_files.extend([output_path, node_path])
        
        response = send_file(
            output_path,
            mimetype='application/json',
            as_attachment=True,
            download_name='config.json'
        )
        
        # 延迟清理文件
        threading.Timer(60.0, cleanup_files, args=[temp_files]).start()
        return response
        
    except Exception as e:
        # 清理所有临时文件
        for file in temp_files:
            if file.exists():
                file.unlink()
        return f'处理失败: {str(e)}', 500

def cleanup_files(file_paths):
    """清理临时文件"""
    for file_path in file_paths:
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"清理临时文件: {file_path}")
        except Exception as e:
            logger.error(f"清理文件失败 {file_path}: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
