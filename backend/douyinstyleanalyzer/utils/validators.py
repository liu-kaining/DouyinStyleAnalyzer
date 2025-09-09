"""
数据验证工具
"""

import re
from urllib.parse import urlparse


def validate_douyin_url(url):
    """验证抖音URL格式"""
    if not url:
        return False
    
    try:
        parsed = urlparse(url)
        
        # 检查域名
        if parsed.netloc not in ['www.douyin.com', 'douyin.com']:
            return False
        
        # 检查路径格式
        # 支持的用户主页格式：
        # https://www.douyin.com/user/MS4wLjABAAAA...
        # https://www.douyin.com/user/1234567890
        user_pattern = r'^/user/[A-Za-z0-9_-]+$'
        
        if re.match(user_pattern, parsed.path):
            return True
        
        return False
        
    except Exception:
        return False


def validate_video_url(url):
    """验证抖音视频URL格式"""
    if not url:
        return False
    
    try:
        parsed = urlparse(url)
        
        # 检查域名
        if parsed.netloc not in ['www.douyin.com', 'douyin.com']:
            return False
        
        # 检查路径格式
        # 支持的视频格式：
        # https://www.douyin.com/video/1234567890
        video_pattern = r'^/video/\d+$'
        
        if re.match(video_pattern, parsed.path):
            return True
        
        return False
        
    except Exception:
        return False


def extract_user_id_from_url(url):
    """从URL中提取用户ID"""
    if not validate_douyin_url(url):
        return None
    
    try:
        parsed = urlparse(url)
        path_parts = parsed.path.split('/')
        
        if len(path_parts) >= 3 and path_parts[1] == 'user':
            return path_parts[2]
        
        return None
        
    except Exception:
        return None


def extract_video_id_from_url(url):
    """从URL中提取视频ID"""
    if not validate_video_url(url):
        return None
    
    try:
        parsed = urlparse(url)
        path_parts = parsed.path.split('/')
        
        if len(path_parts) >= 3 and path_parts[1] == 'video':
            return path_parts[2]
        
        return None
        
    except Exception:
        return None


def validate_whisper_model(model_size):
    """验证Whisper模型大小"""
    valid_models = ['tiny', 'base', 'small', 'medium', 'large']
    return model_size in valid_models


def validate_language_code(language):
    """验证语言代码"""
    valid_languages = ['zh', 'en', 'ja', 'ko', 'auto']
    return language in valid_languages


def validate_max_videos(max_videos):
    """验证最大视频数量"""
    try:
        num = int(max_videos)
        return 1 <= num <= 1000
    except (ValueError, TypeError):
        return False


def sanitize_filename(filename):
    """清理文件名，移除非法字符"""
    # 移除或替换非法字符
    illegal_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(illegal_chars, '_', filename)
    
    # 限制长度
    if len(sanitized) > 255:
        sanitized = sanitized[:255]
    
    return sanitized.strip()


def validate_task_options(options):
    """验证任务选项"""
    if not isinstance(options, dict):
        return False, "选项必须是字典格式"
    
    # 验证enable_transcription
    if 'enable_transcription' in options:
        if not isinstance(options['enable_transcription'], bool):
            return False, "enable_transcription必须是布尔值"
    
    # 验证whisper_model
    if 'whisper_model' in options:
        if not validate_whisper_model(options['whisper_model']):
            return False, "无效的Whisper模型大小"
    
    # 验证language
    if 'language' in options:
        if not validate_language_code(options['language']):
            return False, "无效的语言代码"
    
    return True, "验证通过"
