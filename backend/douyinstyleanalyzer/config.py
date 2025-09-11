"""
DouyinStyleAnalyzer 配置文件
"""

import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.parent.parent

class Config:
    """基础配置类"""
    
    # Flask 配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-change-in-production'
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{BASE_DIR}/app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 文件存储配置
    TEMP_DIR = os.environ.get('TEMP_DIR') or str(BASE_DIR / 'temp')
    AUDIO_DIR = os.environ.get('AUDIO_DIR') or str(Path(TEMP_DIR) / 'audio')
    OUTPUT_DIR = os.environ.get('OUTPUT_DIR') or str(BASE_DIR / 'output')
    
    # Selenium 配置
    CHROME_USER_DATA_DIR = os.environ.get('CHROME_USER_DATA_DIR') or str(Path.home() / '.douyin_browser')
    MAX_SCROLL_COUNT = int(os.environ.get('MAX_SCROLL_COUNT', 15))
    
    # Whisper 配置
    WHISPER_MODEL_SIZE = os.environ.get('WHISPER_MODEL_SIZE', 'small')
    WHISPER_DEVICE = os.environ.get('WHISPER_DEVICE', 'cpu')  # 'cpu' or 'cuda'
    WHISPER_COMPUTE_TYPE = os.environ.get('WHISPER_COMPUTE_TYPE', 'float32')  # 改为float32以兼容更多设备
    
    # 任务配置
    MAX_CONCURRENT_TASKS = int(os.environ.get('MAX_CONCURRENT_TASKS', 3))
    TASK_TIMEOUT = int(os.environ.get('TASK_TIMEOUT', 3600))  # 1小时
    CLEANUP_INTERVAL = int(os.environ.get('CLEANUP_INTERVAL', 86400))  # 24小时
    
    # 重试配置
    MAX_RETRY_COUNT = int(os.environ.get('MAX_RETRY_COUNT', 10))  # 最大重试次数
    RETRY_DELAY_BASE = int(os.environ.get('RETRY_DELAY_BASE', 2))  # 基础延迟时间（秒）
    RETRY_DELAY_MAX = int(os.environ.get('RETRY_DELAY_MAX', 60))  # 最大延迟时间（秒）
    RETRY_BACKOFF_FACTOR = float(os.environ.get('RETRY_BACKOFF_FACTOR', 2.0))  # 退避因子
    
    # 用户配额配置
    DEFAULT_QUOTA = int(os.environ.get('DEFAULT_QUOTA', 100))
    PREMIUM_QUOTA = int(os.environ.get('PREMIUM_QUOTA', 1000))
    
    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE') or str(BASE_DIR / 'logs' / 'app.log')
    
    @staticmethod
    def init_app(app):
        """初始化应用配置"""
        # 创建必要的目录
        for directory in [Config.TEMP_DIR, Config.AUDIO_DIR, Config.OUTPUT_DIR]:
            os.makedirs(directory, exist_ok=True)
        
        # 创建日志目录
        log_dir = Path(Config.LOG_FILE).parent
        log_dir.mkdir(parents=True, exist_ok=True)


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    TESTING = False
    
    # 生产环境使用 PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://user:password@localhost/douyinstyleanalyzer'


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
