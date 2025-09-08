# DouyinStyleAnalyzer 项目

这是一个抖音风格分析器项目，包含用户认证、AI代理、异步任务、前端组件等核心功能。

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 初始化数据库
```bash
python scripts/init_db.py init
```

### 3. 启动项目
```bash
python run.py
```

## 📁 项目结构

```
DouyinStyleAnalyzer/
├── backend/                    # 后端代码
│   └── douyinstyleanalyzer/
│       ├── services/          # 核心服务
│       │   ├── auth/         # 认证服务
│       │   └── ai/           # AI 服务
│       ├── templates/        # 前端模板
│       └── static/           # 静态资源
├── scripts/                    # 工具脚本
├── requirements.txt           # Python 依赖
├── Dockerfile                 # Docker 配置
├── docker-compose.yml         # Docker Compose 配置
└── README.md                  # 项目说明
```

## 🔧 核心功能

### 1. 用户认证系统
- JWT Token 管理
- 邮箱验证码登录
- 权限控制系统
- Session 管理

### 2. AI 代理系统
- 多模型支持（Qwen、DeepSeek、OpenAI）
- 重试机制和故障转移
- 配置管理

### 3. 异步任务系统
- 任务生命周期管理
- 状态跟踪和监控

### 4. 前端组件
- Markdown 渲染器
- 确认弹窗系统
- 响应式设计

## 🎨 自定义指南

### 添加新功能
1. 在 `backend/douyinstyleanalyzer/services/` 下创建新的服务模块
2. 在 `backend/douyinstyleanalyzer/api/` 下添加新的 API 接口
3. 在 `backend/douyinstyleanalyzer/templates/` 下创建新的页面模板

### 修改数据库
1. 在 `backend/douyinstyleanalyzer/models/` 下修改或添加数据模型
2. 运行 `python scripts/init_db.py init` 更新数据库

## 📚 使用示例

### 认证功能
```python
from backend.douyinstyleanalyzer.services.auth import AuthService
from backend.douyinstyleanalyzer.services.auth.jwt_service import JWTService

# 初始化服务
auth_service = AuthService()
jwt_service = JWTService()

# 用户注册
user = auth_service.register_user("user@example.com", "password")

# 用户登录
token = auth_service.login_user("user@example.com", "password")
```

### AI 功能
```python
from backend.douyinstyleanalyzer.services.ai import LLMProviderFactory

# 创建 AI 提供商
provider = LLMProviderFactory.create_provider('qwen', {
    'api_key': 'your-api-key',
    'model': 'qwen-turbo'
})

# 生成分析
result = provider.generate_analysis("分析提示", {"content": "分析内容"})
```

### 前端组件
```html
<!-- 使用确认弹窗 -->
<button onclick="confirmAction('确认删除', '确定要删除吗？', deleteFunction)">
    删除
</button>

<!-- 使用 Markdown 渲染 -->
<div class="markdown-content">
    {{ markdown_content | safe }}
</div>
```

## 🔒 安全配置

### 环境变量
```bash
# .env 文件
JWT_SECRET_KEY=your-secret-key
QWEN_API_KEY=your-qwen-api-key
DEEPSEEK_API_KEY=your-deepseek-api-key
DATABASE_URL=sqlite:///app.db
```

### 生产环境配置
```python
# config/production.py
class ProductionConfig:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    DEBUG = False
```

## 🚀 部署

### Docker 部署
```bash
# 构建镜像
docker build -t my-new-project .

# 运行容器
docker run -p 5000:5000 my-new-project
```

### 传统部署
```bash
# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python scripts/init_db.py init

# 启动应用
python run.py
```

## 📝 开发指南

### 添加新功能
1. 在相应的服务模块中添加功能
2. 创建对应的 API 接口
3. 添加前端页面和交互
4. 编写测试用例

### 代码规范
- 使用 Black 格式化代码
- 使用 Flake8 检查代码质量
- 编写完整的文档字符串
- 添加类型注解

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进这个模板！

## 📄 许可证

MIT License
