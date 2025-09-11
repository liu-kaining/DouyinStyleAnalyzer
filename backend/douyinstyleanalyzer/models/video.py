"""
视频数据模型
"""

from datetime import datetime, timezone, timedelta
from .. import db

# 东八区时区
CHINA_TZ = timezone(timedelta(hours=8))

def china_now():
    """获取东八区当前时间"""
    return datetime.now(CHINA_TZ)


class VideoData(db.Model):
    """视频数据模型"""
    
    __tablename__ = 'video_data'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(36), db.ForeignKey('analysis_tasks.id'), nullable=False, index=True)
    
    # 视频基本信息
    video_id = db.Column(db.String(50), nullable=False, index=True)  # 抖音视频ID
    title = db.Column(db.Text, nullable=False)
    url = db.Column(db.Text, nullable=False)
    duration = db.Column(db.Integer, nullable=True)  # 视频时长（秒）
    
    # 处理状态
    audio_downloaded = db.Column(db.Boolean, default=False, nullable=False)
    transcription_completed = db.Column(db.Boolean, default=False, nullable=False)
    processing_status = db.Column(db.String(20), default='pending', nullable=False)  # pending, processing, completed, failed
    
    # 转录结果
    transcript = db.Column(db.Text, nullable=True)
    transcript_confidence = db.Column(db.Float, nullable=True)  # 转录置信度
    language_detected = db.Column(db.String(10), nullable=True)  # 检测到的语言
    
    # 文件信息
    audio_file_path = db.Column(db.String(255), nullable=True)
    audio_file_size = db.Column(db.Integer, nullable=True)  # 音频文件大小（字节）
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=china_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=china_now, onupdate=china_now)
    processed_at = db.Column(db.DateTime, nullable=True)
    
    # 错误信息
    error_message = db.Column(db.Text, nullable=True)
    retry_count = db.Column(db.Integer, default=0, nullable=False)
    last_retry_at = db.Column(db.DateTime, nullable=True)  # 最后重试时间
    retry_errors = db.Column(db.Text, nullable=True)  # 重试错误历史（JSON格式）
    
    def __repr__(self):
        return f'<VideoData {self.video_id}>'
    
    @classmethod
    def get_video_by_url(cls, video_url):
        """根据视频URL查找已存在的视频记录"""
        return cls.query.filter_by(url=video_url).first()
    
    @classmethod
    def get_downloaded_count(cls):
        """获取已下载的视频数量"""
        return cls.query.filter_by(audio_downloaded=True).count()
    
    @classmethod
    def get_transcribed_count(cls):
        """获取已转录的视频数量"""
        return cls.query.filter_by(transcription_completed=True).count()
    
    @classmethod
    def clear_all_downloaded_files(cls):
        """清除所有已下载的音频文件"""
        import os
        from .. import config
        
        # 获取所有已下载的视频记录
        downloaded_videos = cls.query.filter_by(audio_downloaded=True).all()
        deleted_count = 0
        
        for video in downloaded_videos:
            if video.audio_file_path and os.path.exists(video.audio_file_path):
                try:
                    os.remove(video.audio_file_path)
                    deleted_count += 1
                except Exception as e:
                    print(f"删除文件失败 {video.audio_file_path}: {e}")
            
            # 重置下载状态
            video.audio_downloaded = False
            video.audio_file_path = None
            video.audio_file_size = None
        
        return deleted_count
    
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
            'task_id': self.task_id,
            'video_id': self.video_id,
            'title': self.title,
            'url': self.url,
            'duration': self.duration,
            'audio_downloaded': self.audio_downloaded,
            'transcription_completed': self.transcription_completed,
            'processing_status': self.processing_status,
            'transcript': self.transcript,
            'transcript_confidence': self.transcript_confidence,
            'language_detected': self.language_detected,
            'audio_file_path': self.audio_file_path,
            'audio_file_size': self.audio_file_size,
            'created_at': format_time_with_tz(self.created_at),
            'updated_at': format_time_with_tz(self.updated_at),
            'processed_at': format_time_with_tz(self.processed_at),
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'last_retry_at': format_time_with_tz(self.last_retry_at),
            'retry_errors': self.retry_errors
        }
    
    def update_status(self, status, error_message=None):
        """更新处理状态"""
        self.processing_status = status
        if error_message:
            self.error_message = error_message
            self.retry_count += 1
        
        if status == 'completed':
            self.processed_at = china_now()
        
        self.updated_at = china_now()
        db.session.commit()
    
    def set_audio_info(self, file_path, file_size):
        """设置音频文件信息"""
        self.audio_file_path = file_path
        self.audio_file_size = file_size
        self.audio_downloaded = True
        self.updated_at = china_now()
        db.session.commit()
    
    def set_transcription_result(self, transcript, confidence=None, language=None):
        """设置转录结果"""
        self.transcript = transcript
        self.transcript_confidence = confidence
        self.language_detected = language
        self.transcription_completed = True
        self.processing_status = 'completed'
        self.processed_at = china_now()
        self.updated_at = china_now()
        db.session.commit()
    
    @classmethod
    def create_video(cls, task_id, video_id, title, url, duration=None):
        """创建视频数据"""
        video = cls(
            task_id=task_id,
            video_id=video_id,
            title=title,
            url=url,
            duration=duration
        )
        return video
    
    def is_processed(self):
        """检查是否已处理完成"""
        return self.processing_status == 'completed'
    
    def can_retry(self, max_retries=10):
        """检查是否可以重试"""
        return self.retry_count < max_retries and self.processing_status == 'failed'
    
    def add_retry_error(self, error_message):
        """添加重试错误记录"""
        import json
        
        try:
            # 解析现有的错误历史
            if self.retry_errors:
                error_history = json.loads(self.retry_errors)
            else:
                error_history = []
            
            # 添加新的错误记录
            error_record = {
                'retry_count': self.retry_count,
                'error_message': error_message,
                'timestamp': china_now().isoformat()
            }
            error_history.append(error_record)
            
            # 保存错误历史（最多保留最近20条）
            if len(error_history) > 20:
                error_history = error_history[-20:]
            
            self.retry_errors = json.dumps(error_history, ensure_ascii=False)
            self.last_retry_at = china_now()
            
        except Exception as e:
            print(f"⚠️ 保存重试错误历史失败: {e}")
    
    def get_retry_errors(self):
        """获取重试错误历史"""
        import json
        
        try:
            if self.retry_errors:
                return json.loads(self.retry_errors)
            return []
        except Exception as e:
            print(f"⚠️ 解析重试错误历史失败: {e}")
            return []
