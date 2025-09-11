#!/usr/bin/env python3
"""
测试重试机制脚本
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.douyinstyleanalyzer import create_app, db
from backend.douyinstyleanalyzer.models.video import VideoData
from backend.douyinstyleanalyzer.utils.retry import RetryManager, RetryConfig


def test_retry_mechanism():
    """测试重试机制"""
    print("🧪 开始测试重试机制...")
    
    # 测试重试配置
    config = RetryConfig(max_retries=3, base_delay=1.0, max_delay=10.0)
    retry_manager = RetryManager(config)
    
    # 测试失败函数
    attempt_count = 0
    def failing_function():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise Exception(f"模拟失败 (第 {attempt_count} 次)")
        return "成功！"
    
    try:
        result = retry_manager.retry(failing_function)
        print(f"✅ 重试测试成功: {result}")
        print(f"📊 总共尝试了 {attempt_count} 次")
    except Exception as e:
        print(f"❌ 重试测试失败: {e}")
    
    # 测试数据库重试字段
    app = create_app()
    with app.app_context():
        try:
            # 创建一个测试视频记录
            test_video = VideoData.create_video(
                task_id="test_task",
                video_id="test_video_123",
                title="测试视频",
                url="https://test.com/video/123"
            )
            db.session.add(test_video)
            db.session.commit()
            
            # 测试重试错误记录
            test_video.add_retry_error("网络连接失败")
            test_video.add_retry_error("超时错误")
            
            # 获取重试错误历史
            errors = test_video.get_retry_errors()
            print(f"📝 重试错误历史: {len(errors)} 条记录")
            for error in errors:
                print(f"   - 第 {error['retry_count']} 次: {error['error_message']}")
            
            # 测试重试检查
            can_retry = test_video.can_retry(max_retries=5)
            print(f"🔄 是否可以重试: {can_retry}")
            
            # 清理测试数据
            db.session.delete(test_video)
            db.session.commit()
            
            print("✅ 数据库重试字段测试成功")
            
        except Exception as e:
            print(f"❌ 数据库测试失败: {e}")
            db.session.rollback()


if __name__ == '__main__':
    test_retry_mechanism()
    print("🎉 重试机制测试完成")
