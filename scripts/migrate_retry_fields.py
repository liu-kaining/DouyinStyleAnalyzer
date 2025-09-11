#!/usr/bin/env python3
"""
数据库迁移脚本 - 添加重试相关字段
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.douyinstyleanalyzer import create_app, db
from backend.douyinstyleanalyzer.models.video import VideoData


def migrate_retry_fields():
    """添加重试相关字段到数据库"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔄 开始数据库迁移...")
            
            # 检查字段是否已存在
            inspector = db.inspect(db.engine)
            existing_columns = [col['name'] for col in inspector.get_columns('video_data')]
            
            # 需要添加的字段
            new_columns = {
                'last_retry_at': 'DATETIME',
                'retry_errors': 'TEXT'
            }
            
            # 添加缺失的字段
            for column_name, column_type in new_columns.items():
                if column_name not in existing_columns:
                    print(f"➕ 添加字段: {column_name}")
                    
                    if column_type == 'DATETIME':
                        with db.engine.connect() as conn:
                            conn.execute(db.text(f"ALTER TABLE video_data ADD COLUMN {column_name} DATETIME"))
                            conn.commit()
                    elif column_type == 'TEXT':
                        with db.engine.connect() as conn:
                            conn.execute(db.text(f"ALTER TABLE video_data ADD COLUMN {column_name} TEXT"))
                            conn.commit()
                    
                    print(f"✅ 字段 {column_name} 添加成功")
                else:
                    print(f"⏭️ 字段 {column_name} 已存在，跳过")
            
            print("🎉 数据库迁移完成！")
            
        except Exception as e:
            print(f"❌ 数据库迁移失败: {e}")
            return False
    
    return True


if __name__ == '__main__':
    success = migrate_retry_fields()
    if success:
        print("✅ 迁移成功完成")
        sys.exit(0)
    else:
        print("❌ 迁移失败")
        sys.exit(1)
