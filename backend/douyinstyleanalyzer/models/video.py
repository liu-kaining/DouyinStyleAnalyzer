"""
视频数据模型
"""

from datetime import datetime
from .. import db


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
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    
    # 错误信息
    error_message = db.Column(db.Text, nullable=True)
    retry_count = db.Column(db.Integer, default=0, nullable=False)
    
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
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'error_message': self.error_message,
            'retry_count': self.retry_count
        }
    
    def update_status(self, status, error_message=None):
        """更新处理状态"""
        self.processing_status = status
        if error_message:
            self.error_message = error_message
            self.retry_count += 1
        
        if status == 'completed':
            self.processed_at = datetime.utcnow()
        
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def set_audio_info(self, file_path, file_size):
        """设置音频文件信息"""
        self.audio_file_path = file_path
        self.audio_file_size = file_size
        self.audio_downloaded = True
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def set_transcription_result(self, transcript, confidence=None, language=None):
        """设置转录结果"""
        self.transcript = transcript
        self.transcript_confidence = confidence
        self.language_detected = language
        self.transcription_completed = True
        self.processing_status = 'completed'
        self.processed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
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
    
    def can_retry(self, max_retries=3):
        """检查是否可以重试"""
        return self.retry_count < max_retries and self.processing_status == 'failed'
