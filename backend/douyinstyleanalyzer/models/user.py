"""
用户模型
"""

from datetime import datetime, timezone, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from .. import db


class User(db.Model):
    """用户模型"""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    nickname = db.Column(db.String(100), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # 用户状态
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    
    # 用户角色和配额
    user_role = db.Column(db.String(20), default='USER', nullable=False)  # USER, ADMIN, SUPER_ADMIN
    plan_type = db.Column(db.String(20), default='TRIAL', nullable=False)  # TRIAL, BASIC, PREMIUM
    quota_remaining = db.Column(db.Integer, default=100, nullable=False)
    quota_total = db.Column(db.Integer, default=100, nullable=False)
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone(timedelta(hours=8))), nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone(timedelta(hours=8))), onupdate=lambda: datetime.now(timezone(timedelta(hours=8))))
    
    # 关联关系
    tasks = db.relationship('AnalysisTask', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        """设置密码"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'nickname': self.nickname,
            'is_active': self.is_active,
            'email_verified': self.email_verified,
            'user_role': self.user_role,
            'plan_type': self.plan_type,
            'quota_remaining': self.quota_remaining,
            'quota_total': self.quota_total,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def create_user(cls, username, email, password, nickname=None, **kwargs):
        """创建用户"""
        user = cls(
            username=username,
            email=email,
            nickname=nickname or username,
            **kwargs
        )
        user.set_password(password)
        return user
    
    def update_last_login(self):
        """更新最后登录时间"""
        self.last_login = datetime.now(timezone(timedelta(hours=8)))
        db.session.commit()
    
    def consume_quota(self, amount=1):
        """消费配额"""
        if self.quota_remaining >= amount:
            self.quota_remaining -= amount
            db.session.commit()
            return True
        return False
    
    def reset_quota(self):
        """重置配额"""
        from ..config import Config
        if self.plan_type == 'PREMIUM':
            self.quota_total = Config.PREMIUM_QUOTA
        else:
            self.quota_total = Config.DEFAULT_QUOTA
        self.quota_remaining = self.quota_total
        db.session.commit()
