"""
主页面路由
"""

from flask import render_template, Blueprint

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """主页"""
    return render_template('index.html')

@main_bp.route('/dashboard')
def dashboard():
    """任务管理页面"""
    return render_template('dashboard.html')


@main_bp.route('/auth')
def auth():
    """认证页面"""
    return render_template('auth.html')
