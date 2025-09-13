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


@tasks_bp.route('/queue-status', methods=['GET'])
@require_auth
def get_queue_status(user):
    """获取任务队列状态"""
    try:
        from ..services.task_manager import TaskManager
        task_manager = TaskManager()
        queue_status = task_manager.get_queue_status()
        
        return jsonify({
            'success': True,
            'data': queue_status
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取队列状态失败: {str(e)}'
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
        elif task.current_step == TaskStep.FINALIZING:
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
        
        # 检查是否已存在该博主的任务（去重检查）
        existing_task = AnalysisTask.query.filter_by(
            user_id=user.id,
            target_url=data['target_url']
        ).filter(
            AnalysisTask.status.in_(['PENDING', 'RUNNING'])
        ).first()
        
        if existing_task:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'DUPLICATE_TASK',
                    'message': f'该博主已有任务正在处理中（任务ID: {existing_task.id[:8]}...）'
                }
            }), 409
        
        # 检查用户配额
        if user.quota_remaining <= 0:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INSUFFICIENT_QUOTA',
                    'message': '配额不足'
                }
            }), 403
        
        # 检查并发任务限制（最多5个并发任务）
        running_tasks_count = AnalysisTask.query.filter_by(
            user_id=user.id,
            status=TaskStatus.RUNNING
        ).count()
        
        MAX_CONCURRENT_TASKS = 5
        if running_tasks_count >= MAX_CONCURRENT_TASKS:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'TOO_MANY_CONCURRENT_TASKS',
                    'message': f'最多只能同时运行 {MAX_CONCURRENT_TASKS} 个任务，当前已有 {running_tasks_count} 个任务在运行'
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
        
        # 获取分析报告
        analysis_report = task.get_analysis_report()
        
        # 添加额外的状态信息
        task_data.update({
            'processed_videos': task_data.get('videos_processed', 0),
            'failed_videos': task_data.get('videos_failed', 0),
            'status_message': get_status_message(task),
            'videos': video_data,
            'analysis_report': analysis_report
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
    """导出任务数据（支持CSV和PDF格式）"""
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
        
        # 获取导出格式
        export_format = request.args.get('format', 'csv').lower()
        
        if export_format == 'csv':
            return export_to_csv(task, videos)
        elif export_format == 'pdf':
            return export_to_pdf(task, videos)
        else:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_FORMAT',
                    'message': '不支持的导出格式'
                }
            }), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'EXPORT_ERROR',
                'message': f'导出失败: {str(e)}'
            }
        }), 500

@tasks_bp.route('/<task_id>/delete', methods=['DELETE'])
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
        
        # 删除对应的输出文件
        if task.result_file:
            from ..config import Config
            import os
            output_file_path = os.path.join(Config.OUTPUT_DIR, task.result_file)
            if os.path.exists(output_file_path):
                try:
                    os.remove(output_file_path)
                    print(f"删除任务输出文件: {output_file_path}")
                except Exception as e:
                    print(f"删除输出文件失败 {output_file_path}: {e}")
        
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
    """清空所有任务、文件和数据库数据"""
    try:
        from ..config import Config
        import os
        import glob
        
        # 获取用户的所有任务
        tasks = AnalysisTask.query.filter_by(user_id=user.id).all()
        
        # 如果用户是管理员，清空所有任务
        if user.id == 'anonymous_user' or user.id == 'dev_user':
            print(f"管理员用户 {user.id} 执行完全清空操作")
            # 清空所有任务和视频数据
            VideoData.query.delete()
            AnalysisTask.query.delete()
            tasks = []  # 重置任务列表，因为已经全部删除
        
        deleted_files = 0
        deleted_audio_files = 0
        
        # 删除所有相关的视频数据和文件
        for task in tasks:
            # 删除相关的视频数据
            VideoData.query.filter_by(task_id=task.id).delete()
            
            # 删除对应的输出文件
            if task.result_file:
                output_file_path = os.path.join(Config.OUTPUT_DIR, task.result_file)
                if os.path.exists(output_file_path):
                    try:
                        os.remove(output_file_path)
                        deleted_files += 1
                        print(f"删除任务输出文件: {output_file_path}")
                    except Exception as e:
                        print(f"删除输出文件失败 {output_file_path}: {e}")
        
        # 删除所有任务
        for task in tasks:
            db.session.delete(task)
        
        # 清空所有输出文件（包括JSON文件）
        output_dir = Config.OUTPUT_DIR
        if os.path.exists(output_dir):
            json_files = glob.glob(os.path.join(output_dir, "*.json"))
            for json_file in json_files:
                try:
                    os.remove(json_file)
                    deleted_files += 1
                    print(f"删除输出文件: {json_file}")
                except Exception as e:
                    print(f"删除输出文件失败 {json_file}: {e}")
        
        # 清空所有音频文件
        audio_dir = Config.AUDIO_DIR
        if os.path.exists(audio_dir):
            audio_files = glob.glob(os.path.join(audio_dir, "*.mp4"))
            for audio_file in audio_files:
                try:
                    os.remove(audio_file)
                    deleted_audio_files += 1
                    print(f"删除音频文件: {audio_file}")
                except Exception as e:
                    print(f"删除音频文件失败 {audio_file}: {e}")
        
        # 清空cookies文件
        temp_dir = Config.TEMP_DIR
        if os.path.exists(temp_dir):
            cookie_files = glob.glob(os.path.join(temp_dir, "cookies_*.txt"))
            for cookie_file in cookie_files:
                try:
                    os.remove(cookie_file)
                    print(f"删除cookies文件: {cookie_file}")
                except Exception as e:
                    print(f"删除cookies文件失败 {cookie_file}: {e}")
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'已完全清空：{len(tasks)} 个任务，{deleted_files} 个输出文件，{deleted_audio_files} 个音频文件'
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

@tasks_bp.route('/<task_id>/videos/<video_id>/download', methods=['GET'])
@require_auth
def download_video(user, task_id, video_id):
    """下载视频文件"""
    try:
        # 验证任务是否存在且属于当前用户
        task = AnalysisTask.query.filter_by(id=task_id, user_id=user.id).first()
        if not task:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'TASK_NOT_FOUND',
                    'message': '任务不存在'
                }
            }), 404
        
        # 查找视频记录
        video_record = VideoData.query.filter_by(
            task_id=task_id, 
            video_id=video_id
        ).first()
        
        if not video_record:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'VIDEO_NOT_FOUND',
                    'message': '视频不存在'
                }
            }), 404
        
        # 检查视频文件是否存在
        if not video_record.audio_file_path or not os.path.exists(video_record.audio_file_path):
            return jsonify({
                'success': False,
                'error': {
                    'code': 'FILE_NOT_FOUND',
                    'message': '视频文件不存在或已被清理'
                }
            }), 404
        
        # 生成下载文件名
        safe_title = "".join(c for c in video_record.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        if not safe_title or safe_title == "视频":
            safe_title = f"video_{video_id}"
        
        download_filename = f"{safe_title}_{video_id}.mp4"
        
        # 返回文件下载
        return send_from_directory(
            directory=os.path.dirname(video_record.audio_file_path),
            path=os.path.basename(video_record.audio_file_path),
            as_attachment=True,
            download_name=download_filename
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'DOWNLOAD_ERROR',
                'message': f'下载失败: {str(e)}'
            }
        }), 500

def export_to_csv(task, videos):
    """导出为CSV格式"""
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入标题行
    writer.writerow([
        '视频ID', '标题', 'URL', '处理状态', '转录完成', 
        '置信度', '转录文本', '音频文件大小', '创建时间'
    ])
    
    # 写入数据行
    for video in videos:
        writer.writerow([
            video.video_id,
            video.title or '',
            video.url or '',
            video.processing_status or '',
            '是' if video.transcription_completed else '否',
            f"{video.transcript_confidence * 100:.1f}%" if video.transcript_confidence else '',
            video.transcript or '',
            f"{video.audio_file_size} bytes" if video.audio_file_size else '',
            video.created_at.strftime('%Y-%m-%d %H:%M:%S') if video.created_at else ''
        ])
    
    # 准备响应
    csv_content = output.getvalue()
    output.close()
    
    # 生成文件名 - 使用东八区时间
    from datetime import timezone, timedelta
    china_tz = timezone(timedelta(hours=8))
    china_time = datetime.now(china_tz)
    filename = f"douyin_analysis_{task.id}_{china_time.strftime('%Y%m%d_%H%M%S')}.csv"
    
    from flask import Response
    response = Response(
        csv_content,
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type': 'text/csv; charset=utf-8'
        }
    )
    
    return response

def export_to_pdf(task, videos):
    """导出为PDF格式 - 支持中文，逐个视频显示"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import io
        import time
        import os
        
        start_time = time.time()
        
        # 创建PDF文档
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4, 
            topMargin=0.8*inch, 
            bottomMargin=0.8*inch,
            leftMargin=0.8*inch,
            rightMargin=0.8*inch
        )
        
        # 注册中文字体 - 使用系统默认字体
        try:
            # 尝试注册系统中文字体
            if os.path.exists('/System/Library/Fonts/PingFang.ttc'):
                pdfmetrics.registerFont(TTFont('PingFang', '/System/Library/Fonts/PingFang.ttc'))
                chinese_font = 'PingFang'
            elif os.path.exists('/System/Library/Fonts/STHeiti Light.ttc'):
                pdfmetrics.registerFont(TTFont('STHeiti', '/System/Library/Fonts/STHeiti Light.ttc'))
                chinese_font = 'STHeiti'
            else:
                # 使用默认字体，但设置编码
                chinese_font = 'Helvetica'
        except:
            chinese_font = 'Helvetica'
        
        # 创建自定义样式
        styles = getSampleStyleSheet()
        
        # 标题样式
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName=chinese_font,
            fontSize=20,
            spaceAfter=30,
            alignment=1,  # 居中
            textColor=colors.darkblue,
            leading=24
        )
        
        # 章节标题样式
        section_style = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading2'],
            fontName=chinese_font,
            fontSize=14,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.darkblue,
            leading=18
        )
        
        # 视频标题样式
        video_title_style = ParagraphStyle(
            'VideoTitle',
            parent=styles['Heading3'],
            fontName=chinese_font,
            fontSize=12,
            spaceAfter=8,
            spaceBefore=15,
            textColor=colors.darkgreen,
            leading=16
        )
        
        # 正文样式
        normal_style = ParagraphStyle(
            'ChineseNormal',
            parent=styles['Normal'],
            fontName=chinese_font,
            fontSize=10,
            spaceAfter=6,
            leading=14
        )
        
        # 转录文本样式
        transcript_style = ParagraphStyle(
            'Transcript',
            parent=styles['Normal'],
            fontName=chinese_font,
            fontSize=10,
            spaceAfter=8,
            spaceBefore=8,
            leftIndent=20,
            rightIndent=20,
            leading=16,
            backColor=colors.lightgrey,
            borderColor=colors.grey,
            borderWidth=1,
            borderPadding=8
        )
        
        # 构建PDF内容
        story = []
        
        # 标题
        story.append(Paragraph("抖音视频分析报告", title_style))
        story.append(Spacer(1, 20))
        
        # 任务信息
        story.append(Paragraph("任务信息", section_style))
        story.append(Paragraph(f"<b>任务ID:</b> {task.id}", normal_style))
        story.append(Paragraph(f"<b>目标URL:</b> {task.target_url}", normal_style))
        story.append(Paragraph(f"<b>创建时间:</b> {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
        story.append(Paragraph(f"<b>总视频数:</b> {len(videos)}", normal_style))
        story.append(Spacer(1, 20))
        
        # 逐个显示视频信息
        if videos:
            story.append(Paragraph("视频详情", section_style))
            
            for i, video in enumerate(videos, 1):
                # 每5个视频分页，避免页面过长
                if i > 1 and (i - 1) % 5 == 0:
                    story.append(PageBreak())
                    story.append(Paragraph(f"视频详情 (第 {((i-1)//5) + 1} 页)", section_style))
                
                # 视频标题
                video_title = f"视频 {i}: {video.video_id}"
                story.append(Paragraph(video_title, video_title_style))
                
                # 视频基本信息
                story.append(Paragraph(f"<b>视频ID:</b> {video.video_id}", normal_style))
                story.append(Paragraph(f"<b>标题:</b> {video.title or '无标题'}", normal_style))
                story.append(Paragraph(f"<b>状态:</b> {video.processing_status or '未知'}", normal_style))
                
                if video.transcript_confidence:
                    story.append(Paragraph(f"<b>转录置信度:</b> {video.transcript_confidence * 100:.1f}%", normal_style))
                
                if video.language_detected:
                    story.append(Paragraph(f"<b>检测语言:</b> {video.language_detected}", normal_style))
                
                if video.duration:
                    story.append(Paragraph(f"<b>视频时长:</b> {video.duration}秒", normal_style))
                
                # 转录文本
                if video.transcript:
                    story.append(Paragraph("<b>转录文本:</b>", normal_style))
                    # 处理长文本，自动换行
                    transcript_text = video.transcript.replace('\n', '<br/>')
                    story.append(Paragraph(transcript_text, transcript_style))
                else:
                    story.append(Paragraph("<b>转录文本:</b> 无转录内容", normal_style))
                
                # 添加分隔线
                if i < len(videos):
                    story.append(Spacer(1, 10))
                    story.append(Paragraph("─" * 50, normal_style))
                    story.append(Spacer(1, 10))
        
        # 添加AI分析报告
        analysis_report = task.get_analysis_report()
        if analysis_report and analysis_report.get('markdown'):
            story.append(Spacer(1, 20))
            story.append(Paragraph("竞品风格与策略深度解构报告", section_style))
            
            # 处理Markdown格式的分析报告
            markdown_content = analysis_report.get('markdown', '')
            if markdown_content:
                # 将Markdown转换为适合PDF的格式
                pdf_content = _convert_markdown_to_pdf(markdown_content, normal_style, transcript_style)
                story.extend(pdf_content)
            else:
                story.append(Paragraph("分析报告暂无内容", normal_style))
        elif analysis_report and analysis_report.get('analysis_status') == 'pending':
            story.append(Spacer(1, 20))
            story.append(Paragraph("竞品风格与策略深度解构报告", section_style))
            story.append(Paragraph("分析报告尚未生成", normal_style))
        elif analysis_report and analysis_report.get('analysis_status') == 'failed':
            story.append(Spacer(1, 20))
            story.append(Paragraph("竞品风格与策略深度解构报告", section_style))
            story.append(Paragraph("分析报告生成失败", normal_style))
        
        # 添加统计信息
        story.append(Spacer(1, 20))
        story.append(Paragraph("统计信息", section_style))
        
        success_count = sum(1 for v in videos if v.processing_status == 'completed')
        failed_count = sum(1 for v in videos if v.processing_status == 'failed')
        transcribed_count = sum(1 for v in videos if v.transcription_completed)
        
        story.append(Paragraph(f"<b>总视频数:</b> {len(videos)}", normal_style))
        story.append(Paragraph(f"<b>成功处理:</b> {success_count}", normal_style))
        story.append(Paragraph(f"<b>处理失败:</b> {failed_count}", normal_style))
        story.append(Paragraph(f"<b>已转录:</b> {transcribed_count}", normal_style))
        
        # 添加生成时间信息
        story.append(Spacer(1, 20))
        generation_time = time.time() - start_time
        # 使用东八区时间
        from datetime import timezone, timedelta
        china_tz = timezone(timedelta(hours=8))
        china_time = datetime.now(china_tz)
        story.append(Paragraph(f"<i>报告生成时间: {china_time.strftime('%Y-%m-%d %H:%M:%S')} (耗时: {generation_time:.2f}秒)</i>", normal_style))
        
        # 生成PDF
        doc.build(story)
        buffer.seek(0)
        
        # 生成文件名
        filename = f"douyin_analysis_{task.id}_{china_time.strftime('%Y%m%d_%H%M%S')}.pdf"
        
        from flask import Response
        response = Response(
            buffer.getvalue(),
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Length': str(len(buffer.getvalue()))
            }
        )
        
        return response
        
    except ImportError:
        return jsonify({
            'success': False,
            'error': {
                'code': 'PDF_LIBRARY_MISSING',
                'message': 'PDF导出功能需要安装reportlab库'
            }
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'PDF_GENERATION_ERROR',
                'message': f'PDF生成失败: {str(e)}'
            }
        }), 500


@tasks_bp.route('/<task_id>/regenerate-report', methods=['POST'])
@require_auth
def regenerate_report(user, task_id):
    """重新生成AI分析报告"""
    try:
        # 验证任务是否存在且属于当前用户
        task = AnalysisTask.query.filter_by(id=task_id, user_id=user.id).first()
        if not task:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'TASK_NOT_FOUND',
                    'message': '任务不存在或无权限访问'
                }
            }), 404

        # 检查任务状态 - 允许运行中和已完成的任务重新生成报告
        if task.status not in [TaskStatus.COMPLETED, TaskStatus.RUNNING]:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'TASK_NOT_READY',
                    'message': '只有运行中或已完成的任务才能重新生成报告'
                }
            }), 400

        # 检查是否有视频数据
        videos = VideoData.query.filter_by(task_id=task_id).all()
        if not videos:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NO_VIDEO_DATA',
                    'message': '没有找到视频数据，无法生成报告'
                }
            }), 400

        # 准备视频数据
        videos_data = []
        for video in videos:
            if video.transcript:  # 只包含有转录文本的视频
                videos_data.append({
                    'title': video.title or f'视频 {video.video_id}',
                    'transcript': video.transcript  # 修正字段名
                })

        if not videos_data:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NO_TRANSCRIPTION_DATA',
                    'message': '没有找到转录数据，无法生成报告'
                }
            }), 400

        # 调用AI分析服务
        from ..services.ai.deepseek_analyzer import DeepSeekAnalyzer
        analyzer = DeepSeekAnalyzer()
        
        # 获取博主名称
        blogger_name = task.name or '未知博主'
        
        print(f"🔄 重新生成报告 - 任务: {task_id}, 博主: {blogger_name}, 视频数: {len(videos_data)}")
        
        # 执行AI分析
        analysis_result = analyzer.analyze_blogger_style(blogger_name, videos_data)
        
        if analysis_result:
            # 保存分析结果到数据库
            task.set_analysis_report(analysis_result, 'completed')
            db.session.commit()
            
            print(f"✅ 报告重新生成成功 - 任务: {task_id}")
            
            return jsonify({
                'success': True,
                'message': '报告重新生成成功',
                'data': {
                    'task_id': task_id,
                    'analysis_report': analysis_result
                }
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'ANALYSIS_FAILED',
                    'message': 'AI分析失败，请稍后重试'
                }
            }), 500

    except Exception as e:
        print(f"❌ 重新生成报告失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'REGENERATE_REPORT_ERROR',
                'message': f'重新生成报告失败: {str(e)}'
            }
        }), 500


def _convert_markdown_to_pdf(markdown_content, normal_style, transcript_style):
    """将Markdown内容转换为PDF格式的段落列表"""
    from reportlab.platypus import Paragraph, Spacer
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    import re
    
    story = []
    lines = markdown_content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 6))
            continue
            
        # 处理标题
        if line.startswith('# '):
            # 一级标题
            title_style = ParagraphStyle(
                'MarkdownH1',
                parent=normal_style,
                fontSize=16,
                spaceAfter=12,
                spaceBefore=16,
                textColor=colors.darkblue,
                fontName=normal_style.fontName
            )
            story.append(Paragraph(line[2:], title_style))
        elif line.startswith('## '):
            # 二级标题
            title_style = ParagraphStyle(
                'MarkdownH2',
                parent=normal_style,
                fontSize=14,
                spaceAfter=10,
                spaceBefore=12,
                textColor=colors.darkblue,
                fontName=normal_style.fontName
            )
            story.append(Paragraph(line[3:], title_style))
        elif line.startswith('### '):
            # 三级标题
            title_style = ParagraphStyle(
                'MarkdownH3',
                parent=normal_style,
                fontSize=12,
                spaceAfter=8,
                spaceBefore=10,
                textColor=colors.darkgreen,
                fontName=normal_style.fontName
            )
            story.append(Paragraph(line[4:], title_style))
        elif line.startswith('**') and line.endswith('**') and line.count('**') == 2:
            # 整行粗体文本
            bold_style = ParagraphStyle(
                'MarkdownBold',
                parent=normal_style,
                fontSize=normal_style.fontSize,
                fontName=normal_style.fontName
            )
            story.append(Paragraph(f"<b>{line[2:-2]}</b>", bold_style))
        elif line.startswith('- ') or line.startswith('* '):
            # 列表项
            list_style = ParagraphStyle(
                'MarkdownList',
                parent=normal_style,
                fontSize=normal_style.fontSize,
                leftIndent=20,
                fontName=normal_style.fontName
            )
            story.append(Paragraph(f"• {line[2:]}", list_style))
        elif line.startswith('---'):
            # 分隔线
            story.append(Spacer(1, 10))
            story.append(Paragraph("─" * 50, normal_style))
            story.append(Spacer(1, 10))
        else:
            # 普通段落 - 安全地处理Markdown格式
            formatted_line = _safe_convert_markdown_to_html(line)
            story.append(Paragraph(formatted_line, transcript_style))
    
    return story


def _safe_convert_markdown_to_html(text):
    """安全地将Markdown格式转换为HTML，避免标签嵌套问题"""
    import re
    
    # 转义HTML特殊字符
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    
    # 处理粗体 **text**
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    
    # 处理斜体 *text*
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    
    # 处理行内代码 `code`
    text = re.sub(r'`(.*?)`', r'<font name="Courier"><b>\1</b></font>', text)
    
    return text
