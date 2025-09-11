#!/usr/bin/env python3
"""
测试yt-dlp下载功能
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.douyinstyleanalyzer import create_app
from backend.douyinstyleanalyzer.services.transcriber import VideoTranscriber


def test_ytdlp_download():
    """测试yt-dlp下载功能"""
    print("🧪 开始测试yt-dlp下载功能...")
    
    app = create_app()
    with app.app_context():
        try:
            # 创建转录器实例
            transcriber = VideoTranscriber()
            
            # 测试视频URL（使用一个公开的抖音视频）
            test_video_url = "https://www.douyin.com/video/7543994141248687395"
            test_output_name = "test_download"
            
            print(f"🎬 测试下载视频: {test_video_url}")
            
            # 尝试从文件读取cookies
            cookies = None
            cookie_file = "douyin_cookies.txt"
            if os.path.exists(cookie_file):
                print(f"🍪 找到cookies文件: {cookie_file}")
                # 这里可以添加读取cookies的逻辑
                # 暂时使用None，让系统使用默认的cookies处理
            
            # 尝试下载
            result = transcriber.download_video(test_video_url, test_output_name, cookies)
            
            if result:
                print(f"✅ 下载成功: {result}")
                
                # 检查文件是否存在
                if os.path.exists(result):
                    file_size = os.path.getsize(result)
                    print(f"📁 文件大小: {file_size} bytes")
                    
                    # 清理测试文件
                    try:
                        os.remove(result)
                        print("🗑️ 已清理测试文件")
                    except Exception as e:
                        print(f"⚠️ 清理文件失败: {e}")
                else:
                    print("❌ 文件不存在")
            else:
                print("❌ 下载失败")
                
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    test_ytdlp_download()
    print("🎉 yt-dlp下载测试完成")
