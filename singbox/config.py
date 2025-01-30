from pathlib import Path

# 常量定义
USER_AGENT = 'sing-box'

# 使用 Path 对象处理路径 
BASE_DIR = Path(__file__).parent
OUTPUT_FOLDER = BASE_DIR / 'outputs'
TEMPLATE_PATH = BASE_DIR / 'template' / 'tun_1.11.json'