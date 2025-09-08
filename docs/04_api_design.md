# API 接口设计文档

## 4.1 接口规范

### 基础信息
- **Base URL**: `http://localhost:5000/api/v1`
- **认证方式**: JWT Bearer Token
- **数据格式**: JSON
- **字符编码**: UTF-8

### 通用响应格式
```json
{
  "success": true,
  "message": "操作成功",
  "data": {},
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 错误响应格式
```json
{
  "success": false,
  "error": {
    "code": "INVALID_URL",
    "message": "无效的URL格式",
    "details": "请提供有效的抖音博主主页链接"
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## 4.2 认证接口

### 用户登录
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "password123"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "expires_in": 3600,
    "user": {
      "id": 1,
      "username": "user@example.com",
      "quota_remaining": 100
    }
  }
}
```

### 用户注册
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "password123",
  "nickname": "用户昵称"
}
```

## 4.3 任务管理接口

### 创建分析任务
```http
POST /api/v1/tasks
Authorization: Bearer <token>
Content-Type: application/json

{
  "target_url": "https://www.douyin.com/user/MS4wLjABAAAA...",
  "max_videos": 50,
  "options": {
    "enable_transcription": true,
    "whisper_model": "small",
    "language": "zh"
  }
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "task_id": "task_1234567890",
    "status": "pending",
    "estimated_time": 1800,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

### 查询任务状态
```http
GET /api/v1/tasks/{task_id}
Authorization: Bearer <token>
```

**响应**:
```json
{
  "success": true,
  "data": {
    "task_id": "task_1234567890",
    "status": "running",
    "progress": 65,
    "current_step": "transcribing",
    "videos_processed": 13,
    "total_videos": 20,
    "estimated_remaining": 600,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:15:00Z"
  }
}
```

### 获取任务列表
```http
GET /api/v1/tasks?page=1&limit=10&status=completed
Authorization: Bearer <token>
```

**响应**:
```json
{
  "success": true,
  "data": {
    "tasks": [
      {
        "task_id": "task_1234567890",
        "target_url": "https://www.douyin.com/user/...",
        "status": "completed",
        "progress": 100,
        "videos_count": 25,
        "created_at": "2024-01-01T00:00:00Z",
        "completed_at": "2024-01-01T00:30:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 10,
      "total": 5,
      "pages": 1
    }
  }
}
```

### 取消任务
```http
DELETE /api/v1/tasks/{task_id}
Authorization: Bearer <token>
```

## 4.4 数据下载接口

### 下载任务结果
```http
GET /api/v1/tasks/{task_id}/download
Authorization: Bearer <token>
```

**响应**: 直接返回 JSON 文件下载

### 获取任务结果预览
```http
GET /api/v1/tasks/{task_id}/preview?limit=5
Authorization: Bearer <token>
```

**响应**:
```json
{
  "success": true,
  "data": {
    "task_id": "task_1234567890",
    "total_videos": 25,
    "preview": [
      {
        "video_id": "1234567890",
        "title": "凌晨三点的便利店美食...",
        "url": "https://www.douyin.com/video/1234567890",
        "transcript": "谁说深夜没好吃的？这家便利店的关东煮...",
        "duration": 45,
        "created_at": "2024-01-01T00:00:00Z"
      }
    ]
  }
}
```

## 4.5 系统状态接口

### 获取系统状态
```http
GET /api/v1/system/status
Authorization: Bearer <token>
```

**响应**:
```json
{
  "success": true,
  "data": {
    "system_status": "healthy",
    "active_tasks": 2,
    "queue_size": 5,
    "disk_usage": {
      "total": "100GB",
      "used": "45GB",
      "available": "55GB"
    },
    "gpu_available": true,
    "last_updated": "2024-01-01T00:00:00Z"
  }
}
```

### 获取用户配额信息
```http
GET /api/v1/user/quota
Authorization: Bearer <token>
```

**响应**:
```json
{
  "success": true,
  "data": {
    "quota_remaining": 85,
    "quota_total": 100,
    "quota_reset_date": "2024-02-01T00:00:00Z",
    "usage_this_month": 15
  }
}
```

## 4.6 错误码定义

| 错误码 | HTTP状态码 | 说明 |
|--------|------------|------|
| INVALID_TOKEN | 401 | 无效的认证令牌 |
| INSUFFICIENT_QUOTA | 403 | 配额不足 |
| INVALID_URL | 400 | 无效的URL格式 |
| TASK_NOT_FOUND | 404 | 任务不存在 |
| TASK_ALREADY_RUNNING | 409 | 任务已在运行 |
| SYSTEM_BUSY | 503 | 系统繁忙 |
| INTERNAL_ERROR | 500 | 内部服务器错误 |

## 4.7 接口测试

### 测试用例
1. **正常流程测试**
   - 用户登录
   - 创建任务
   - 查询状态
   - 下载结果

2. **异常流程测试**
   - 无效URL
   - 配额不足
   - 任务取消
   - 系统错误

3. **性能测试**
   - 并发请求
   - 大数据量
   - 长时间运行

### 测试工具
- Postman/Insomnia
- pytest + requests
- 自动化测试脚本
