"""
系统状态 API 接口
"""

from flask import Blueprint, jsonify
from datetime import datetime
from ..models import User, AnalysisTask, TaskStatus
from .. import db
from ..services.auth.jwt_service import JWTService
import psutil
import os

system_bp = Blueprint('system', __name__)

# 初始化 JWT 服务
jwt_service = JWTService()


def get_current_user():
    """获取当前用户"""
    from flask import request
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None
    
    try:
        token = auth_header.split(' ')[1]  # Bearer <token>
    except IndexError:
        return None
    
    payload = jwt_service.verify_token(token)
    if not payload:
        return None
    
    return User.query.get(payload['user_id'])


def require_auth(f):
    """认证装饰器"""
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNAUTHORIZED',
                    'message': '需要认证'
                }
            }), 401
        return f(user, *args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function


@system_bp.route('/status', methods=['GET'])
def get_system_status():
    """获取系统状态"""
    try:
        # 获取活跃任务数量
        active_tasks = AnalysisTask.query.filter(
            AnalysisTask.status.in_([TaskStatus.PENDING, TaskStatus.RUNNING])
        ).count()
        
        # 获取队列大小（这里暂时返回活跃任务数）
        queue_size = active_tasks
        
        # 获取磁盘使用情况
        disk_usage = psutil.disk_usage('/')
        disk_total = disk_usage.total
        disk_used = disk_usage.used
        disk_available = disk_usage.free
        
        # 检查 GPU 是否可用
        gpu_available = False
        try:
            import torch
            gpu_available = torch.cuda.is_available()
        except ImportError:
            pass
        
        # 获取系统资源使用情况
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # 获取视频统计
        from ..models import VideoData
        total_videos = VideoData.query.count()
        downloaded_videos = VideoData.get_downloaded_count()
        transcribed_videos = VideoData.get_transcribed_count()
        
        return jsonify({
            'success': True,
            'data': {
                'system_status': 'healthy',
                'active_tasks': active_tasks,
                'queue_size': queue_size,
                'disk_usage': {
                    'total': f"{disk_total // (1024**3)}GB",
                    'used': f"{disk_used // (1024**3)}GB",
                    'available': f"{disk_available // (1024**3)}GB",
                    'percent': round((disk_used / disk_total) * 100, 2)
                },
                'system_resources': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_available': f"{memory.available // (1024**3)}GB"
                },
                'gpu_available': gpu_available,
                'video_stats': {
                    'total_videos': total_videos,
                    'downloaded_videos': downloaded_videos,
                    'transcribed_videos': transcribed_videos
                },
                'last_updated': datetime.utcnow().isoformat()
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': '获取系统状态失败',
                'details': str(e)
            }
        }), 500


@system_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    try:
        # 检查数据库连接
        db.session.execute('SELECT 1')
        db_status = 'healthy'
    except Exception:
        db_status = 'unhealthy'
    
    overall_status = 'healthy' if db_status == 'healthy' else 'unhealthy'
    
    return jsonify({
        'success': True,
        'data': {
            'status': overall_status,
            'services': {
                'database': db_status
            },
            'timestamp': datetime.utcnow().isoformat()
        }
    }), 200 if overall_status == 'healthy' else 503


@system_bp.route('/info', methods=['GET'])
def get_system_info():
    """获取系统信息"""
    try:
        from ..config import Config
        
        return jsonify({
            'success': True,
            'data': {
                'app_name': 'DouyinStyleAnalyzer',
                'version': '1.0.0',
                'environment': os.environ.get('FLASK_ENV', 'development'),
                'config': {
                    'max_concurrent_tasks': Config.MAX_CONCURRENT_TASKS,
                    'task_timeout': Config.TASK_TIMEOUT,
                    'whisper_model_size': Config.WHISPER_MODEL_SIZE,
                    'whisper_device': Config.WHISPER_DEVICE,
                    'default_quota': Config.DEFAULT_QUOTA,
                    'premium_quota': Config.PREMIUM_QUOTA
                },
                'timestamp': datetime.utcnow().isoformat()
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': '获取系统信息失败',
                'details': str(e)
            }
        }), 500


@system_bp.route('/clear-files', methods=['DELETE'])
def clear_downloaded_files():
    """清除所有已下载的音频文件"""
    try:
        from ..models import VideoData
        from ..config import Config
        import os
        import glob
        
        # 方法1：删除audio目录下的所有文件
        audio_dir = Config.AUDIO_DIR
        audio_files = glob.glob(os.path.join(audio_dir, '*.m4a'))
        deleted_count = 0
        
        for file_path in audio_files:
            try:
                os.remove(file_path)
                deleted_count += 1
                print(f"删除文件: {file_path}")
            except Exception as e:
                print(f"删除文件失败 {file_path}: {e}")
        
        # 方法2：更新数据库中的记录
        downloaded_videos = VideoData.query.filter_by(audio_downloaded=True).all()
        for video in downloaded_videos:
            video.audio_downloaded = False
            video.audio_file_path = None
            video.audio_file_size = None
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'已清除 {deleted_count} 个音频文件'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'清除文件失败: {str(e)}'
        }), 500
