"""
任务管理 API 接口
"""

from flask import Blueprint, request, jsonify, send_from_directory
from datetime import datetime
from ..models import User, AnalysisTask, VideoData, TaskStatus, TaskStep
from .. import db
from ..services.auth.jwt_service import JWTService
from ..utils.validators import validate_douyin_url
import os

tasks_bp = Blueprint('tasks', __name__)

# 初始化 JWT 服务
jwt_service = JWTService()


def require_auth(f):
    """认证装饰器 - 已禁用，不需要网站用户认证"""
    def decorated_function(*args, **kwargs):
        # 创建一个模拟用户对象，不需要真实认证
        class MockUser:
            def __init__(self):
                self.id = 'anonymous_user'
                self.username = 'anonymous'
                self.email = 'anonymous@example.com'
                self.quota_remaining = 1000  # 给足够大的配额
            
            def consume_quota(self, amount):
                self.quota_remaining -= amount
        
        return f(MockUser(), *args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function


@tasks_bp.route('', methods=['GET'])
@require_auth
def get_tasks(user):
    """获取任务列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # 获取用户的任务列表
        tasks = AnalysisTask.query.filter_by(user_id=user.id)\
            .order_by(AnalysisTask.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'success': True,
            'data': {
                'tasks': [task.to_dict() for task in tasks.items],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': tasks.total,
                    'pages': tasks.pages,
                    'has_next': tasks.has_next,
                    'has_prev': tasks.has_prev
                }
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取任务列表失败: {str(e)}'
        }), 500


def get_current_user():
    """获取当前用户"""
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


def get_status_message(task):
    """获取任务状态消息"""
    if task.status == TaskStatus.PENDING:
        return "任务等待开始..."
    elif task.status == TaskStatus.RUNNING:
        if task.current_step == TaskStep.INITIALIZING:
            return "正在初始化任务..."
        elif task.current_step == TaskStep.SCRAPING:
            return f"正在采集视频... (已采集 {task.total_videos or 0} 个)"
        elif task.current_step == TaskStep.DOWNLOADING:
            return f"正在下载音频... (已处理 {task.videos_processed or 0}/{task.total_videos or 0})"
        elif task.current_step == TaskStep.TRANSCRIBING:
            return f"正在语音识别... (已处理 {task.videos_processed or 0}/{task.total_videos or 0})"
        elif task.current_step == TaskStep.SAVING:
            return "正在保存结果..."
        else:
            return "任务运行中..."
    elif task.status == TaskStatus.COMPLETED:
        return f"任务完成！成功处理 {task.videos_success or 0} 个视频"
    elif task.status == TaskStatus.FAILED:
        return f"任务失败: {task.error_message or '未知错误'}"
    else:
        return "未知状态"




@tasks_bp.route('', methods=['POST'])
@require_auth
def create_task(user):
    """创建分析任务"""
    try:
        data = request.get_json()
        
        # 验证必需字段
        if not data.get('target_url'):
            return jsonify({
                'success': False,
                'error': {
                    'code': 'MISSING_URL',
                    'message': '缺少目标URL'
                }
            }), 400
        
        # 验证 URL 格式
        if not validate_douyin_url(data['target_url']):
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_URL',
                    'message': '无效的抖音URL格式'
                }
            }), 400
        
        # 检查用户配额
        if user.quota_remaining <= 0:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INSUFFICIENT_QUOTA',
                    'message': '配额不足'
                }
            }), 403
        
        # 检查是否有正在运行的任务
        running_task = AnalysisTask.query.filter_by(
            user_id=user.id,
            status=TaskStatus.RUNNING
        ).first()
        
        if running_task:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'TASK_ALREADY_RUNNING',
                    'message': '已有任务正在运行'
                }
            }), 409
        
        # 创建任务
        task = AnalysisTask.create_task(
            user_id=user.id,
            target_url=data['target_url'],
            max_videos=data.get('max_videos', 50),
            enable_transcription=data.get('options', {}).get('enable_transcription', True),
            whisper_model=data.get('options', {}).get('whisper_model', 'small'),
            language=data.get('options', {}).get('language', 'zh')
        )
        
        db.session.add(task)
        db.session.commit()
        
        # 消费配额
        user.consume_quota(1)
        
        # 启动异步任务处理
        from ..services.task_manager import TaskManager
        from flask import current_app
        
        # 获取cookies（如果有的话）
        cookies = data.get('cookies', None)
        
        task_manager = TaskManager()
        if task_manager.start_analysis_task(task.id, current_app._get_current_object(), cookies):
            print(f"🚀 任务 {task.id} 已启动")
        else:
            print(f"❌ 任务 {task.id} 启动失败")
        
        return jsonify({
            'success': True,
            'message': '任务创建成功',
            'data': {
                'task_id': task.id,
                'status': task.status.value,
                'estimated_time': 1800,  # 30分钟
                'created_at': task.created_at.isoformat()
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': '创建任务失败',
                'details': str(e)
            }
        }), 500


@tasks_bp.route('/<task_id>', methods=['GET'])
@require_auth
def get_task(user, task_id):
    """获取任务详情"""
    try:
        task = AnalysisTask.query.filter_by(id=task_id, user_id=user.id).first()
        
        if not task:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'TASK_NOT_FOUND',
                    'message': '任务不存在'
                }
            }), 404
        
        # 获取任务数据
        task_data = task.to_dict()
        
        # 获取视频数据
        videos = VideoData.query.filter_by(task_id=task_id).all()
        video_data = [video.to_dict() for video in videos]
        
        # 添加额外的状态信息
        task_data.update({
            'processed_videos': task_data.get('videos_processed', 0),
            'failed_videos': task_data.get('videos_failed', 0),
            'status_message': get_status_message(task),
            'videos': video_data
        })
        
        return jsonify({
            'success': True,
            'data': task_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': '获取任务失败',
                'details': str(e)
            }
        }), 500




@tasks_bp.route('/<task_id>', methods=['DELETE'])
@require_auth
def cancel_task(user, task_id):
    """取消任务"""
    try:
        task = AnalysisTask.query.filter_by(id=task_id, user_id=user.id).first()
        
        if not task:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'TASK_NOT_FOUND',
                    'message': '任务不存在'
                }
            }), 404
        
        if not task.can_be_cancelled():
            return jsonify({
                'success': False,
                'error': {
                    'code': 'TASK_CANNOT_BE_CANCELLED',
                    'message': '任务无法取消'
                }
            }), 400
        
        # 取消任务
        from ..services.task_manager import cancel_analysis_task
        
        # 先更新数据库状态
        task.update_status(TaskStatus.FAILED, error_message="用户取消")
        
        # 然后从运行队列中移除
        if cancel_analysis_task(task_id):
            print(f"🛑 任务 {task_id} 已取消")
        else:
            print(f"⚠️ 任务 {task_id} 取消失败")
        
        return jsonify({
            'success': True,
            'message': '任务已取消'
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': '取消任务失败',
                'details': str(e)
            }
        }), 500


@tasks_bp.route('/<task_id>/download', methods=['GET'])
@require_auth
def download_task_result(user, task_id):
    """下载任务结果"""
    try:
        task = AnalysisTask.query.filter_by(id=task_id, user_id=user.id).first()
        
        if not task:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'TASK_NOT_FOUND',
                    'message': '任务不存在'
                }
            }), 404
        
        if task.status != TaskStatus.COMPLETED:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'TASK_NOT_COMPLETED',
                    'message': '任务尚未完成'
                }
            }), 400
        
        if not task.result_file:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NO_RESULT_FILE',
                    'message': '结果文件不存在'
                }
            }), 404
        
        # 检查文件是否存在
        from ..config import Config
        file_path = os.path.join(Config.OUTPUT_DIR, task.result_file)
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': {
                    'code': 'FILE_NOT_FOUND',
                    'message': '文件不存在'
                }
            }), 404
        
        return send_from_directory(
            Config.OUTPUT_DIR,
            task.result_file,
            as_attachment=True,
            download_name=f'douyin_analysis_{task.id}.json'
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': '下载失败',
                'details': str(e)
            }
        }), 500


@tasks_bp.route('/<task_id>/preview', methods=['GET'])
@require_auth
def get_task_preview(user, task_id):
    """获取任务结果预览"""
    try:
        task = AnalysisTask.query.filter_by(id=task_id, user_id=user.id).first()
        
        if not task:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'TASK_NOT_FOUND',
                    'message': '任务不存在'
                }
            }), 404
        
        # 获取预览数据
        limit = request.args.get('limit', 5, type=int)
        videos = VideoData.query.filter_by(task_id=task_id).limit(limit).all()
        
        preview_data = [video.to_dict() for video in videos]
        
        return jsonify({
            'success': True,
            'data': {
                'task_id': task.id,
                'total_videos': task.total_videos,
                'preview': preview_data
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': '获取预览失败',
                'details': str(e)
            }
        }), 500


@tasks_bp.route('/<task_id>/export', methods=['GET'])
@require_auth
def export_task_data(user, task_id):
    """导出任务数据（包含视频详情）"""
    try:
        task = AnalysisTask.query.filter_by(id=task_id, user_id=user.id).first()
        
        if not task:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'TASK_NOT_FOUND',
                    'message': '任务不存在'
                }
            }), 404
        
        # 获取视频数据
        videos = VideoData.query.filter_by(task_id=task_id).all()
        
        # 构建导出数据
        export_data = {
            'task_info': task.to_dict(),
            'videos': [video.to_dict() for video in videos],
            'summary': {
                'total_videos': len(videos),
                'successful_videos': len([v for v in videos if v.transcription_completed]),
                'failed_videos': len([v for v in videos if v.processing_status == 'failed']),
                'total_transcript_length': sum(len(v.transcript or '') for v in videos),
                'export_time': datetime.utcnow().isoformat()
            }
        }
        
        return jsonify({
            'success': True,
            'data': export_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'EXPORT_ERROR',
                'message': f'导出失败: {str(e)}'
            }
        }), 500

@tasks_bp.route('/<task_id>', methods=['DELETE'])
@require_auth
def delete_task(user, task_id):
    """删除单个任务"""
    try:
        task = AnalysisTask.query.filter_by(id=task_id, user_id=user.id).first()
        
        if not task:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'TASK_NOT_FOUND',
                    'message': '任务不存在'
                }
            }), 404
        
        # 删除相关的视频数据
        VideoData.query.filter_by(task_id=task_id).delete()
        
        # 删除任务
        db.session.delete(task)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '任务删除成功'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': {
                'code': 'DELETE_ERROR',
                'message': f'删除失败: {str(e)}'
            }
        }), 500

@tasks_bp.route('/clear', methods=['DELETE'])
@require_auth
def clear_all_tasks(user):
    """清空所有任务"""
    try:
        # 获取用户的所有任务
        tasks = AnalysisTask.query.filter_by(user_id=user.id).all()
        
        if not tasks:
            return jsonify({
                'success': True,
                'message': '没有任务需要清空'
            }), 200
        
        # 删除所有相关的视频数据
        for task in tasks:
            VideoData.query.filter_by(task_id=task.id).delete()
        
        # 删除所有任务
        for task in tasks:
            db.session.delete(task)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'已清空 {len(tasks)} 个任务'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': {
                'code': 'CLEAR_ERROR',
                'message': f'清空失败: {str(e)}'
            }
        }), 500
