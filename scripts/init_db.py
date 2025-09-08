#!/usr/bin/env python3
"""
数据库初始化脚本 - DouyinStyleAnalyzer 项目
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.douyinstyleanalyzer import create_app, db
from backend.douyinstyleanalyzer.models.user import User


def init_database():
    """初始化数据库"""
    app = create_app()
    
    with app.app_context():
        print("🔄 正在初始化数据库...")
        
        # 创建所有表
        db.create_all()
        print("✅ 数据库表创建完成")
        
        # 创建默认管理员用户
        create_admin_user()
        
        print("🎉 数据库初始化完成！")


def create_admin_user():
    """创建默认管理员用户"""
    try:
        # 检查是否已存在管理员用户
        admin_user = User.query.filter_by(user_role='SUPER_ADMIN').first()
        if admin_user:
            print("ℹ️  管理员用户已存在")
            return
        
        # 创建管理员用户
        admin_user = User(
            username='admin',
            email='admin@example.com',
            nickname='系统管理员',
            user_role='SUPER_ADMIN',
            is_active=True,
            email_verified=True,
            plan_type='PREMIUM',
            remaining_quota=999999
        )
        admin_user.set_password('admin123')
        
        db.session.add(admin_user)
        db.session.commit()
        
        print("✅ 默认管理员用户创建完成")
        print("   用户名: admin")
        print("   密码: admin123")
        print("   邮箱: admin@example.com")
        
    except Exception as e:
        print(f"❌ 创建管理员用户失败: {e}")




def create_test_data():
    """创建测试数据"""
    try:
        app = create_app()
        
        with app.app_context():
            print("🔄 正在创建测试数据...")
            
            # 创建测试用户
            test_user = User(
                username='testuser',
                email='test@example.com',
                nickname='测试用户',
                user_role='USER',
                is_active=True,
                email_verified=True,
                plan_type='TRIAL',
                remaining_quota=10
            )
            test_user.set_password('test123')
            
            db.session.add(test_user)
            db.session.commit()
            
            print("✅ 测试用户创建完成")
            print("   用户名: testuser")
            print("   密码: test123")
            print("   邮箱: test@example.com")
            
    except Exception as e:
        print(f"❌ 创建测试数据失败: {e}")


def clear_database():
    """清空数据库"""
    try:
        app = create_app()
        
        with app.app_context():
            print("🔄 正在清空数据库...")
            
            # 删除所有表
            db.drop_all()
            
            # 重新创建表
            db.create_all()
            
            print("✅ 数据库已清空并重新创建")
            
    except Exception as e:
        print(f"❌ 清空数据库失败: {e}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='数据库管理工具')
    parser.add_argument('action', choices=['init', 'test', 'clear'], 
                       help='操作类型: init(初始化), test(创建测试数据), clear(清空)')
    
    args = parser.parse_args()
    
    if args.action == 'init':
        init_database()
    elif args.action == 'test':
        create_test_data()
    elif args.action == 'clear':
        clear_database()


if __name__ == "__main__":
    main()
