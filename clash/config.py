from dataclasses import dataclass
from pathlib import Path
from typing import Set

@dataclass
class Config:
    # 基础配置
    USER_AGENT: str = 'clash verge'
    CACHE_DURATION: int = 300  # 缓存时间5分钟
    
    # 目录配置
    BASE_DIR: Path = Path(__file__).parent
    OUTPUT_FOLDER: Path = BASE_DIR / 'outputs'
    TEMPLATE_PATH: Path = BASE_DIR / 'template' / 'b.yaml'
    HEADERS_CACHE_PATH: Path = OUTPUT_FOLDER / 'headers_cache.json'
    TEMP_YAML_PATH: Path = OUTPUT_FOLDER / 'temp.yaml'
    TEMP_YAML_LOCK: Path = OUTPUT_FOLDER / 'temp.yaml.lock'
    
    # Headers配置
    INCLUDED_HEADERS: Set[str] = frozenset({'Subscription-Userinfo'})
    
    def __post_init__(self):
        # 确保输出目录存在
        self.OUTPUT_FOLDER.mkdir(exist_ok=True)
        
        # 验证必要文件存在
        if not self.TEMPLATE_PATH.exists():
            raise FileNotFoundError(f"模板文件不存在: {self.TEMPLATE_PATH}")
    
    @property
    def ports_path(self) -> Path:
        return self.BASE_DIR / 'template' / 'ports.yaml'