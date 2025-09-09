"""
认证 API 接口
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from ..models import User
from .. import db
from ..services.auth.jwt_service import JWTService

auth_bp = Blueprint('auth', __name__)

# 初始化 JWT 服务
jwt_service = JWTService()

@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    try:
        data = request.get_json()
        
        # 验证必需字段
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'MISSING_FIELD',
                        'message': f'缺少必需字段: {field}'
                    }
                }), 400
        
        # 检查用户名和邮箱是否已存在
        if User.query.filter_by(username=data['username']).first():
            return jsonify({
                'success': False,
                'error': {
                    'code': 'USERNAME_EXISTS',
                    'message': '用户名已存在'
                }
            }), 409
        
        if User.query.filter_by(email=data['email']).first():
            return jsonify({
                'success': False,
                'error': {
                    'code': 'EMAIL_EXISTS',
                    'message': '邮箱已存在'
                }
            }), 409
        
        # 创建用户
        user = User.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            nickname=data.get('nickname', data['username'])
        )
        
        db.session.add(user)
        db.session.commit()
        
        # 生成 JWT Token
        token_data = jwt_service.generate_token(
            user_id=user.id,
            user_data={'username': user.username, 'role': user.user_role}
        )
        
        return jsonify({
            'success': True,
            'message': '注册成功',
            'data': {
                'token': token_data['token'],
                'expires_in': token_data['expires_in'],
                'user': user.to_dict()
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': '注册失败',
                'details': str(e)
            }
        }), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.get_json()
        
        # 验证必需字段
        username_or_email = data.get('username') or data.get('email')
        if not username_or_email or not data.get('password'):
            return jsonify({
                'success': False,
                'error': {
                    'code': 'MISSING_CREDENTIALS',
                    'message': '用户名/邮箱和密码不能为空'
                }
            }), 400
        
        # 查找用户
        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()
        
        if not user or not user.check_password(data['password']):
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_CREDENTIALS',
                    'message': '用户名或密码错误'
                }
            }), 401
        
        if not user.is_active:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'ACCOUNT_DISABLED',
                    'message': '账户已被禁用'
                }
            }), 403
        
        # 更新最后登录时间
        user.update_last_login()
        
        # 生成 JWT Token
        token_data = jwt_service.generate_token(
            user_id=user.id,
            user_data={'username': user.username, 'role': user.user_role}
        )
        
        return jsonify({
            'success': True,
            'message': '登录成功',
            'data': {
                'token': token_data['token'],
                'expires_in': token_data['expires_in'],
                'user': user.to_dict()
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': '登录失败',
                'details': str(e)
            }
        }), 500


@auth_bp.route('/refresh', methods=['POST'])
def refresh_token():
    """刷新 Token"""
    try:
        data = request.get_json()
        refresh_token = data.get('refresh_token')
        
        if not refresh_token:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'MISSING_TOKEN',
                    'message': '缺少刷新令牌'
                }
            }), 400
        
        # 验证刷新令牌
        new_token_data = jwt_service.refresh_token(refresh_token)
        
        if not new_token_data:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_TOKEN',
                    'message': '无效的刷新令牌'
                }
            }), 401
        
        return jsonify({
            'success': True,
            'message': '令牌刷新成功',
            'data': new_token_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': '令牌刷新失败',
                'details': str(e)
            }
        }), 500


@auth_bp.route('/profile', methods=['GET'])
def get_profile():
    """获取用户信息"""
    try:
        # 从请求头获取 Token
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'MISSING_TOKEN',
                    'message': '缺少认证令牌'
                }
            }), 401
        
        try:
            token = auth_header.split(' ')[1]  # Bearer <token>
        except IndexError:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_TOKEN_FORMAT',
                    'message': '令牌格式错误'
                }
            }), 401
        
        # 验证 Token
        payload = jwt_service.verify_token(token)
        if not payload:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_TOKEN',
                    'message': '无效的认证令牌'
                }
            }), 401
        
        # 获取用户信息
        user = User.query.get(payload['user_id'])
        if not user:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'USER_NOT_FOUND',
                    'message': '用户不存在'
                }
            }), 404
        
        return jsonify({
            'success': True,
            'data': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': '获取用户信息失败',
                'details': str(e)
            }
        }), 500


@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    """获取当前用户信息（/profile 的别名）"""
    return get_profile()
