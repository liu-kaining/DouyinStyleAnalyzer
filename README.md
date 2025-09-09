# DouyinStyleAnalyzer - 抖音博主风格分析系统

一个基于AI的抖音博主内容分析系统，能够自动采集抖音博主的视频，进行语音识别转写，并生成风格分析报告。

## 🚀 功能特性

### 核心功能
- **智能视频采集**: 自动采集抖音博主的视频列表，支持批量处理，智能去重避免重复分析
- **语音识别转写**: 基于 Whisper 模型，高精度转写视频语音内容，支持多语言识别，准确率高达95%以上
- **风格分析报告**: 深度分析博主的创作风格、语言特点，生成详细的分析报告，助力内容创作优化

### 技术特点
- **现代化UI**: 响应式设计，美观的用户界面
- **异步处理**: 支持后台任务处理，实时进度显示
- **文件管理**: 智能文件管理，支持一键清理临时文件
- **数据导出**: 支持分析结果一键导出为JSON格式

## 🛠️ 技术栈

- **后端**: Flask + SQLAlchemy
- **前端**: Bootstrap 5 + JavaScript
- **AI模型**: Faster-Whisper (语音识别)
- **浏览器自动化**: Selenium + Chrome
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **容器化**: Docker + Docker Compose

## 📋 系统要求

- Python 3.11+
- Chrome 浏览器
- 8GB+ RAM (推荐)
- 10GB+ 可用磁盘空间

## 🚀 快速开始

### 方式一：Docker 部署 (推荐)

1. **克隆项目**
```bash
git clone <repository-url>
cd DouyinStyleAnalyzer
```

2. **启动服务**
```bash
docker-compose up -d
```

3. **访问应用**
```
http://localhost:5005
```

### 方式二：本地开发

1. **克隆项目**
```bash
git clone <repository-url>
cd DouyinStyleAnalyzer
```

2. **创建虚拟环境**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **初始化数据库**
```bash
python scripts/init_db.py
```

5. **启动应用**
```bash
python run.py
```

6. **访问应用**
```
http://localhost:5005
```

## 📖 使用指南

### 1. 抖音登录
- 点击"抖音登录"按钮
- 在新窗口中扫码登录抖音
- 登录成功后关闭窗口

### 2. 创建分析任务
- 输入抖音博主主页链接
- 设置要分析的视频数量 (1-100个，默认20个)
- 选择识别语言 (中文/英文/自动检测)
- 点击"开始分析"

### 3. 查看任务进度
- 访问"任务管理"页面
- 实时查看任务执行状态
- 查看详细的处理统计

### 4. 导出分析结果
- 在任务详情页面点击"导出数据"
- 下载JSON格式的分析报告

## 🔧 配置说明

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `FLASK_ENV` | development | 运行环境 |
| `SECRET_KEY` | - | Flask密钥 |
| `JWT_SECRET_KEY` | - | JWT密钥 |
| `DATABASE_URL` | sqlite:///app.db | 数据库连接 |
| `WHISPER_MODEL_SIZE` | small | Whisper模型大小 |
| `WHISPER_DEVICE` | cpu | 计算设备 |
| `MAX_CONCURRENT_TASKS` | 3 | 最大并发任务数 |
| `TASK_TIMEOUT` | 3600 | 任务超时时间(秒) |

### 目录结构

```
DouyinStyleAnalyzer/
├── backend/                 # 后端代码
│   └── douyinstyleanalyzer/
│       ├── api/            # API接口
│       ├── models/         # 数据模型
│       ├── services/       # 业务逻辑
│       ├── templates/      # 前端模板
│       └── static/         # 静态资源
├── temp/                   # 临时文件
│   └── audio/             # 音频文件
├── output/                 # 输出文件
├── logs/                   # 日志文件
├── scripts/                # 脚本文件
├── docs/                   # 文档
├── docker-compose.yml      # Docker编排
├── Dockerfile             # Docker镜像
└── requirements.txt       # Python依赖
```

## 🔍 API 文档

### 任务管理
- `GET /api/v1/tasks` - 获取任务列表
- `POST /api/v1/tasks` - 创建新任务
- `GET /api/v1/tasks/{id}` - 获取任务详情
- `DELETE /api/v1/tasks/{id}` - 删除任务
- `GET /api/v1/tasks/{id}/export` - 导出任务数据

### 系统状态
- `GET /api/v1/system/status` - 获取系统状态
- `GET /api/v1/system/health` - 健康检查
- `DELETE /api/v1/system/clear-files` - 清除临时文件

## 🐳 Docker 部署

### 构建镜像
```bash
docker build -t douyin-analyzer .
```

### 运行容器
```bash
docker run -d \
  --name douyin-analyzer \
  -p 5005:5005 \
  -v $(pwd)/temp:/app/temp \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/logs:/app/logs \
  douyin-analyzer
```

### 使用 Docker Compose
```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重新构建
docker-compose up --build
```

## 🔧 开发指南

### 项目结构
- `backend/douyinstyleanalyzer/` - 主应用代码
- `backend/douyinstyleanalyzer/api/` - API路由
- `backend/douyinstyleanalyzer/models/` - 数据模型
- `backend/douyinstyleanalyzer/services/` - 业务逻辑
- `backend/douyinstyleanalyzer/templates/` - HTML模板

### 添加新功能
1. 在 `services/` 中添加业务逻辑
2. 在 `api/` 中添加API接口
3. 在 `models/` 中定义数据模型
4. 在 `templates/` 中更新前端界面

### 代码规范
- 使用 Python 3.11+ 语法
- 遵循 PEP 8 代码规范
- 添加适当的注释和文档字符串
- 编写单元测试

## 🐛 故障排除

### 常见问题

1. **Chrome 启动失败**
   - 确保已安装 Chrome 浏览器
   - 检查 ChromeDriver 版本兼容性

2. **语音识别失败**
   - 检查音频文件是否存在
   - 确认 Whisper 模型已正确下载

3. **数据库连接失败**
   - 检查数据库配置
   - 确认数据库服务正在运行

4. **任务执行超时**
   - 增加 `TASK_TIMEOUT` 配置
   - 检查网络连接状态

### 日志查看
```bash
# Docker 环境
docker-compose logs -f douyin-analyzer

# 本地环境
tail -f logs/app.log
```

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📞 支持

如有问题或建议，请通过以下方式联系：

- 提交 [Issue](https://github.com/your-repo/issues)
- 发送邮件至: your-email@example.com

## 🙏 致谢

- [Faster-Whisper](https://github.com/guillaumekln/faster-whisper) - 语音识别
- [Selenium](https://selenium.dev/) - 浏览器自动化
- [Flask](https://flask.palletsprojects.com/) - Web框架
- [Bootstrap](https://getbootstrap.com/) - UI框架

---

⭐ 如果这个项目对你有帮助，请给它一个星标！