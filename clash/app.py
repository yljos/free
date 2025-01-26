from flask import Flask, send_file
from ruamel.yaml import YAML
import requests
from urllib.parse import unquote
from pathlib import Path
import json
from datetime import datetime, timedelta
from filelock import FileLock
import logging
import os
import threading

app = Flask(__name__)

# 常量定义
USER_AGENT = 'clash verge'
CACHE_DURATION = 300  # 缓存时间5分钟

# 使用 Path 对象处理路径
BASE_DIR = Path(__file__).parent
OUTPUT_FOLDER = BASE_DIR / 'outputs'
TEMPLATE_PATH = BASE_DIR / 'template' / 'b.yaml'
HEADERS_CACHE_PATH = OUTPUT_FOLDER / 'headers_cache.json'
TEMP_YAML_PATH = OUTPUT_FOLDER / 'temp.yaml'  # 临时YAML文件路径
TEMP_YAML_LOCK = OUTPUT_FOLDER / 'temp.yaml.lock'

# 不应转发的 header 列表
EXCLUDED_HEADERS = {
    'Content-Length', 
    'Content-Encoding', 
    'Transfer-Encoding', 
    'Connection',
    'Server',
    'Date',
    'Set-Cookie',
    'Content-Disposition',
}

# 确保输出目录存在
OUTPUT_FOLDER.mkdir(exist_ok=True)

# YAML 配置
yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def save_headers_cache(url, headers):
    """保存请求头缓存，每个URL只保留最新的一条记录"""
    try:
        if HEADERS_CACHE_PATH.exists():
            with open(HEADERS_CACHE_PATH, 'r', encoding='utf-8') as f:
                cache = json.load(f)
        else:
            cache = {}
        
        filtered_headers = {k: v for k, v in headers.items() 
                          if k not in EXCLUDED_HEADERS}
        
        cache[url] = {
            'headers': filtered_headers,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(HEADERS_CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"保存headers缓存失败: {e}")

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
        print(f"读取headers缓存失败: {e}")
    return None

def fetch_yaml(url):
    """获取 YAML 内容并缓存到本地"""
    lock = FileLock(TEMP_YAML_LOCK)
    temp_path = TEMP_YAML_PATH.with_suffix('.tmp')
    
    try:
        with lock:
            headers = {'User-Agent': USER_AGENT}
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            save_headers_cache(url, response.headers)
            
            # 使用上下文管理器写入临时文件
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            # 验证文件写入是否成功
            if not temp_path.exists() or os.path.getsize(temp_path) == 0:
                raise IOError("临时文件写入失败")
                
            # 验证成功后重命名为最终文件
            if TEMP_YAML_PATH.exists():
                TEMP_YAML_PATH.unlink()
            temp_path.rename(TEMP_YAML_PATH)
            
            logger.info(f"成功缓存YAML文件: {url}")
            return TEMP_YAML_PATH
            
    except requests.exceptions.RequestException as e:
        logger.error(f"下载YAML失败: {str(e)}")
        raise
    except IOError as e:
        logger.error(f"文件操作失败: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"缓存YAML过程中出现未知错误: {str(e)}")
        raise
    finally:
        # 清理临时文件
        try:
            if temp_path.exists():
                temp_path.unlink()
        except Exception as e:
            logger.warning(f"清理临时文件失败: {str(e)}")
        
        if lock.is_locked:
            lock.release()

def process_yaml_content(yaml_path):
    """处理本地YAML文件"""
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            input_data = yaml.load(f)
        
        if not isinstance(input_data, dict):
            raise ValueError('YAML内容必须是有效的字典格式')
        
        proxies = input_data.get('proxies', [])
        if not proxies:
            raise ValueError('YAML文件中未找到有效的proxies配置')
        
        # 处理 hysteria2 节点
        for proxy in proxies:
            if isinstance(proxy, dict) and proxy.get('type') == 'hysteria2':
                proxy['up'] = '50'
                proxy['down'] = '300'
        
        with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
            template_data = yaml.load(f)
        
        template_data['proxies'] = proxies
        
        output_path = OUTPUT_FOLDER / 'Mitce.yaml'
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(template_data, f)
        
        return output_path
    finally:
        # 清理临时文件
        if yaml_path.exists() and yaml_path == TEMP_YAML_PATH:
            yaml_path.unlink()

def cleanup_files(yaml_path, output_path):
    """清理缓存文件和输出文件"""
    try:
        if yaml_path.exists():
            yaml_path.unlink()
        if output_path.exists():
            output_path.unlink()
        if HEADERS_CACHE_PATH.exists():
            HEADERS_CACHE_PATH.unlink()
        logger.info("已清理缓存文件")
    except Exception as e:
        logger.error(f"清理缓存文件失败: {str(e)}")

@app.route('/<path:yaml_url>')
def process_yaml(yaml_url):
    try:
        yaml_url = unquote(yaml_url)
        
        # 标准化URL
        if yaml_url.startswith('/http://'):
            yaml_url = yaml_url[1:]
        elif yaml_url.startswith('/https://'):
            yaml_url = yaml_url[1:]
        elif not yaml_url.startswith(('http://', 'https://')):
            yaml_url = 'https://' + yaml_url
            
        # 获取YAML内容并保存到临时文件
        try:
            temp_yaml_path = fetch_yaml(yaml_url)
            output_path = process_yaml_content(temp_yaml_path)
        except requests.exceptions.RequestException as e:
            return f'下载文件失败: {str(e)}', 400
        
        # 获取缓存的headers
        cached_headers = get_headers_cache(yaml_url)
        
        # 创建响应
        response = send_file(
            output_path,
            mimetype='application/yaml',
            as_attachment=True,
            download_name='Mitce.yaml'
        )
        
        # 设置基本响应头
        response.headers['Content-Type'] = 'application/yaml; charset=utf-8'
        
        # 转发缓存的headers
        if cached_headers:
            for header, value in cached_headers.items():
                if header not in EXCLUDED_HEADERS:
                    response.headers[header] = value
        
        # 设置定时器在60秒后清理文件
        timer = threading.Timer(
            60.0, 
            cleanup_files, 
            args=[temp_yaml_path, output_path]
        )
        timer.start()
        
        return response
        
    except ValueError as e:
        return f'YAML格式错误: {str(e)}', 400
    except Exception as e:
        return f'处理过程中出现错误: {str(e)}', 500

if __name__ == '__main__':
    app.run(debug=True, port=5002, host='0.0.0.0')
