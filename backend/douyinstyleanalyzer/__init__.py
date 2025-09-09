"""
DouyinStyleAnalyzer - 抖音博主风格分析系统
"""

import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# 初始化扩展
db = SQLAlchemy()

def create_app(config_name=None):
    """应用工厂函数"""
    
    # 创建 Flask 应用
    app = Flask(__name__)
    
    # 配置 CORS
    CORS(app)
    
    # 加载配置
    config_name = config_name or os.environ.get('FLASK_ENV', 'development')
    from .config import config
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # 初始化扩展
    db.init_app(app)
    
    # 配置日志
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = logging.FileHandler(app.config['LOG_FILE'])
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('DouyinStyleAnalyzer startup')
    
    # 注册蓝图
    from .api.auth import auth_bp
    from .api.tasks import tasks_bp
    from .api.system import system_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
    app.register_blueprint(tasks_bp, url_prefix='/api/v1/tasks')
    app.register_blueprint(system_bp, url_prefix='/api/v1/system')
    
    # 注册主页面路由
    from .routes import main_bp
    app.register_blueprint(main_bp)
    
    # 创建数据库表
    with app.app_context():
        db.create_all()
    
    return app


