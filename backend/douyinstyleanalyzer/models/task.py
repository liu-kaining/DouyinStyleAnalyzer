"""
任务模型
"""

import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
from .. import db

# 东八区时区
CHINA_TZ = timezone(timedelta(hours=8))

def china_now():
    """获取东八区当前时间"""
    return datetime.now(CHINA_TZ)


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class TaskStep(Enum):
    """任务步骤枚举"""
    INITIALIZING = 'initializing'
    SCRAPING = 'scraping'
    DOWNLOADING = 'downloading'
    TRANSCRIBING = 'transcribing'
    FINALIZING = 'finalizing'


class AnalysisTask(db.Model):
    """分析任务模型"""
    
    __tablename__ = 'analysis_tasks'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # 任务基本信息
    target_url = db.Column(db.Text, nullable=False)
    target_username = db.Column(db.String(100), nullable=True)  # 从URL解析出的用户名
    
    # 任务配置
    max_videos = db.Column(db.Integer, default=50, nullable=False)
    enable_transcription = db.Column(db.Boolean, default=True, nullable=False)
    whisper_model = db.Column(db.String(20), default='small', nullable=False)
    language = db.Column(db.String(10), default='zh', nullable=False)
    
    # 任务状态
    status = db.Column(db.Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True)
    current_step = db.Column(db.Enum(TaskStep), default=TaskStep.INITIALIZING, nullable=False)
    progress = db.Column(db.Integer, default=0, nullable=False)  # 0-100
    
    # 任务统计
    total_videos = db.Column(db.Integer, default=0, nullable=False)
    videos_processed = db.Column(db.Integer, default=0, nullable=False)
    videos_success = db.Column(db.Integer, default=0, nullable=False)
    videos_failed = db.Column(db.Integer, default=0, nullable=False)
    
    # 时间信息
    created_at = db.Column(db.DateTime, default=china_now, nullable=False, index=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=china_now, onupdate=china_now)
    
    # 结果信息
    result_file = db.Column(db.String(255), nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    estimated_remaining = db.Column(db.Integer, nullable=True)  # 预计剩余时间（秒）
    
    # 关联关系
    videos = db.relationship('VideoData', backref='task', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<AnalysisTask {self.id}>'
    
    def to_dict(self):
        """转换为字典"""
        def format_time_with_tz(dt):
            """格式化时间，确保包含时区信息"""
            if not dt:
                return None
            # 如果没有时区信息，假设是东八区时间
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=CHINA_TZ)
            return dt.isoformat()
        
        return {
            'id': self.id,
            'user_id': self.user_id,
            'target_url': self.target_url,
            'target_username': self.target_username,
            'max_videos': self.max_videos,
            'enable_transcription': self.enable_transcription,
            'whisper_model': self.whisper_model,
            'language': self.language,
            'status': self.status.value if self.status else None,
            'current_step': self.current_step.value if self.current_step else None,
            'progress': self.progress,
            'total_videos': self.total_videos,
            'videos_processed': self.videos_processed,
            'videos_success': self.videos_success,
            'videos_failed': self.videos_failed,
            'created_at': format_time_with_tz(self.created_at),
            'started_at': format_time_with_tz(self.started_at),
            'completed_at': format_time_with_tz(self.completed_at),
            'updated_at': format_time_with_tz(self.updated_at),
            'result_file': self.result_file,
            'error_message': self.error_message,
            'estimated_remaining': self.estimated_remaining
        }
    
    def update_status(self, status, step=None, progress=None, error_message=None):
        """更新任务状态"""
        self.status = status
        if step:
            self.current_step = step
        if progress is not None:
            self.progress = progress
        if error_message:
            self.error_message = error_message
        
        # 更新时间戳
        if status == TaskStatus.RUNNING and not self.started_at:
            self.started_at = china_now()
        elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            self.completed_at = china_now()
        
        self.updated_at = china_now()
        db.session.commit()
    
    def update_progress(self, videos_processed, videos_success, videos_failed):
        """更新进度"""
        self.videos_processed = videos_processed
        self.videos_success = videos_success
        self.videos_failed = videos_failed
        
        if self.total_videos > 0:
            self.progress = int((videos_processed / self.total_videos) * 100)
        
        # 计算预计剩余时间
        if self.started_at and videos_processed > 0:
            # 确保started_at有时区信息
            started_at_with_tz = self.started_at
            if started_at_with_tz.tzinfo is None:
                started_at_with_tz = started_at_with_tz.replace(tzinfo=CHINA_TZ)
            elapsed = (china_now() - started_at_with_tz).total_seconds()
            avg_time_per_video = elapsed / videos_processed
            remaining_videos = self.total_videos - videos_processed
            self.estimated_remaining = int(avg_time_per_video * remaining_videos)
        
        self.updated_at = china_now()
        db.session.commit()
    
    def set_result_file(self, filename):
        """设置结果文件"""
        self.result_file = filename
        self.updated_at = china_now()
        db.session.commit()
    
    @classmethod
    def create_task(cls, user_id, target_url, **kwargs):
        """创建任务"""
        task = cls(
            user_id=user_id,
            target_url=target_url,
            **kwargs
        )
        return task
    
    def is_running(self):
        """检查任务是否正在运行"""
        return self.status in [TaskStatus.PENDING, TaskStatus.RUNNING]
    
    def can_be_cancelled(self):
        """检查任务是否可以取消"""
        return self.status in [TaskStatus.PENDING, TaskStatus.RUNNING]
