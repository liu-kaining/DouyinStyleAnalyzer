#!/usr/bin/env python3
"""
DouyinStyleAnalyzer 应用启动文件
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    env_path = project_root / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ 已加载环境变量文件: {env_path}")
    else:
        print(f"⚠️ 未找到 .env 文件: {env_path}")
except ImportError:
    print("⚠️ 未安装 python-dotenv，无法自动加载 .env 文件")

from backend.douyinstyleanalyzer import create_app

# 创建 Flask 应用
app = create_app()

if __name__ == '__main__':
    # 获取配置
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', 5005))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"🚀 启动 DouyinStyleAnalyzer 服务...")
    print(f"📍 访问地址: http://{host}:{port}")
    print(f"🔧 调试模式: {debug}")
    
    # 启动应用
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True
    )
