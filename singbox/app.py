from flask import Flask, send_file
import requests
from urllib.parse import unquote
from pathlib import Path
import json
import logging
import threading

app = Flask(__name__)

# 常量定义
USER_AGENT = 'sing-box'

# 使用 Path 对象处理路径
BASE_DIR = Path(__file__).parent
OUTPUT_FOLDER = BASE_DIR / 'outputs'
TEMPLATE_PATH = BASE_DIR / 'template' / 'tun_1.10.json'
TEMP_JSON_PATH = OUTPUT_FOLDER / 'temp.json'
NODE_PATH = OUTPUT_FOLDER / 'node.json'

# 确保输出目录存在
OUTPUT_FOLDER.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_subscription(url):
    """获取订阅内容并缓存到本地outputs目录"""
    try:
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        temp_path = OUTPUT_FOLDER / 'temp.json'
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        logger.info(f"成功获取订阅内容并保存到: {temp_path}")
        return temp_path
            
    except requests.exceptions.RequestException as e:
        logger.error(f"下载订阅失败: {str(e)}")
        raise

def process_subscription(sub_path):
    """处理本地订阅文件"""
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
                seen_tags.add(item['tag'])
                node_tags.append(item['tag'])
                sub_outbounds.append(item)
                logger.info(f"提取节点: {item['tag']}")

        # 保存节点标签 (使用 LF 换行符)
        with open(NODE_PATH, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(node_tags, f, indent=2, ensure_ascii=False)
        logger.info(f"保存节点标签到: {NODE_PATH}")
            
        # 3. 读取模板
        with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
            template_data = json.load(f)

        # 4. 处理代理组中的节点分配
        for outbound in template_data['outbounds']:
            if isinstance(outbound.get('outbounds'), list) and '{all}' in outbound['outbounds']:
                fixed_outbounds = [o for o in outbound['outbounds'] if o != '{all}']
                group_name = outbound.get('tag', '未知分组')
                
                if 'filter' in outbound:
                    # 初始化过滤后的节点集合
                    filtered_tags = set()
                    
                    # 打印过滤规则内容
                    logger.info(f"分组 [{group_name}] 过滤规则: {json.dumps(outbound['filter'], ensure_ascii=False)}")
                    
                    for f in outbound['filter']:
                        # 处理关键词
                        keywords = []
                        raw_keywords = f.get('keywords', '')
                        if isinstance(raw_keywords, str):
                            keywords = raw_keywords.split('|')
                        elif isinstance(raw_keywords, list):
                            for k in raw_keywords:
                                keywords.extend(k.split('|'))
                                
                        if f.get('action') == 'exclude':
                            # exclude 模式: 先包含所有,再排除匹配的
                            if not filtered_tags:  # 如果还未初始化
                                filtered_tags = set(node_tags)
                            
                            # 排除匹配关键词的节点
                            excluded = {tag for tag in filtered_tags 
                                      if any(k.lower() in tag.lower() for k in keywords)}
                            filtered_tags -= excluded
                            
                            if excluded:
                                logger.info(f"分组 [{group_name}] 排除节点: {excluded}")
                                
                        elif f.get('action') == 'include':
                            # include 模式: 只添加匹配的节点
                            matched = {tag for tag in node_tags 
                                     if any(k.lower() in tag.lower() for k in keywords)}
                            filtered_tags.update(matched)
                            
                            if matched:
                                logger.info(f"分组 [{group_name}] 包含节点: {matched}")
                    
                    # 添加排序
                    outbound['outbounds'] = fixed_outbounds + sorted(list(filtered_tags))
                    logger.info(f"分组 [{group_name}] 过滤后节点数: {len(filtered_tags)}, 节点列表: {sorted(list(filtered_tags))}")
                else:
                    # 添加排序
                    outbound['outbounds'] = fixed_outbounds + sorted(node_tags)
                    logger.info(f"分组 [{group_name}] 使用全部节点: {len(node_tags)}")
                
                # 删除filter配置
                if 'filter' in outbound:
                    del outbound['filter']

        # 5. 重新组合配置
        basic_outbounds = [o for o in template_data['outbounds'] if o.get('type') in ['direct', 'block', 'dns']]
        template_outbounds = [o for o in template_data['outbounds'] if o.get('type') not in ['direct', 'block', 'dns']]
        template_data['outbounds'] = basic_outbounds + sub_outbounds + template_outbounds

        # 6. 保存最终配置 (使用 LF 换行符)
        output_path = OUTPUT_FOLDER / 'config.json'
        with open(output_path, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(template_data, f, indent=2, ensure_ascii=False)
        logger.info(f"保存最终配置到: {output_path}")
        
        return output_path
        
    finally:
        if Path(sub_path).exists():
            Path(sub_path).unlink()
            logger.info(f"清理临时文件: {sub_path}")

@app.route('/<path:sub_url>')
def process_subscription_url(sub_url):
    try:
        sub_url = unquote(sub_url)
        if not sub_url.startswith(('http://', 'https://')):
            sub_url = 'https://' + sub_url
            
        temp_path = fetch_subscription(sub_url)
        output_path = process_subscription(temp_path)
        
        response = send_file(
            output_path,
            mimetype='application/json',
            as_attachment=True,
            download_name='config.json'
        )
        
        threading.Timer(60.0, cleanup_files, args=[output_path]).start()
        return response
        
    except Exception as e:
        return f'处理失败: {str(e)}', 500

def cleanup_files(output_path):
    """清理输出文件和节点文件"""
    # 清理 config.json
    if output_path.exists():
        output_path.unlink()
        logger.info(f"清理配置文件: {output_path}")
    
    # 清理 node.json 
    node_path = output_path.parent / 'node.json'
    if node_path.exists():
        node_path.unlink()
        logger.info(f"清理节点文件: {node_path}")

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
