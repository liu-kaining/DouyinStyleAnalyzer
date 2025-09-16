# DouyinStyleAnalyzer - 抖音博主风格分析系统

一个基于AI的抖音博主内容分析系统，能够自动采集抖音博主的视频，进行语音识别转写，并生成风格分析报告。

## 🚀 功能特性

### 核心功能
- **智能视频采集**: 自动采集抖音博主的视频列表，支持批量处理，智能去重避免重复分析
- **语音识别转写**: 基于 Faster-Whisper 模型，高精度转写视频语音内容，支持多语言识别，准确率高达95%以上
- **AI风格分析**: 集成 DeepSeek AI，深度分析博主的创作风格、语言特点，生成专业的分析报告

### 技术特点
- **现代化UI**: 响应式设计，美观的用户界面，支持移动端访问
- **异步处理**: 支持后台任务处理，实时进度显示，多任务并发执行
- **智能文件管理**: 自动文件管理，支持一键清理临时文件，磁盘空间优化
- **多格式导出**: 支持分析结果导出为JSON、PDF格式，便于进一步分析
- **安全可靠**: JWT认证，数据加密存储，完善的错误处理机制

## 🛠️ 技术栈

### 后端技术
- **Web框架**: Flask 2.0+ (轻量级、高性能)
- **数据库**: SQLAlchemy ORM + SQLite
- **认证**: JWT (JSON Web Token)
- **任务队列**: 自定义异步任务管理器
- **AI集成**: DeepSeek API (风格分析)

### 前端技术
- **UI框架**: Bootstrap 5 (响应式设计)
- **交互**: 原生JavaScript ES6+
- **兼容性**: 支持现代浏览器和移动端

### AI & 自动化
- **语音识别**: Faster-Whisper (OpenAI Whisper优化版)
- **浏览器自动化**: Selenium + Chrome/ChromeDriver
- **视频下载**: yt-dlp (YouTube-DL增强版)
- **内容分析**: DeepSeek AI (大语言模型)

## 📋 系统要求

### 最低配置
- **操作系统**: Linux (Ubuntu 20.04+), macOS 10.15+, Windows 10+
- **Python**: 3.11+
- **内存**: 4GB RAM
- **存储**: 10GB 可用空间
- **网络**: 稳定的互联网连接

### 推荐配置
- **内存**: 8GB+ RAM (处理大量视频时)
- **存储**: 50GB+ 可用空间 (存储音频和分析结果)
- **CPU**: 4核心+ (加速语音识别)
- **GPU**: NVIDIA GPU (可选，加速Whisper模型)

## 🚀 快速开始

1. **克隆项目**
```bash
git clone https://github.com/liu-kaining/DouyinStyleAnalyzer.git
cd DouyinStyleAnalyzer
```

2. **创建虚拟环境**
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

3. **安装依赖**
```bash
# 升级pip
pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt
```

4. **配置环境**
```bash
# 复制环境变量模板
cp env.example .env

# 编辑配置文件 (重要：修改默认密钥)
nano .env
```

**必须配置的变量**:
```bash
# 安全密钥 (必须修改)
SECRET_KEY=your-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production

# DeepSeek API密钥 (必需)
DEEPSEEK_API_KEY=your-deepseek-api-key-here
```

5. **初始化数据库**
```bash
python scripts/init_db.py init
```

6. **启动应用**
```bash
python run.py
```

7. **访问应用**
```
Web界面: http://localhost:5005
健康检查: http://localhost:5005/api/v1/system/health
```

> **💡 提示**: 本地开发需要手动安装Chrome浏览器和ChromeDriver。

## 📖 使用指南

### 🎯 快速上手

#### 1. 🔐 抖音登录
1. 打开应用首页
2. 点击 **"抖音登录"** 按钮
3. 在新窗口中扫码登录抖音账号
4. 登录成功后关闭窗口，系统自动保存登录状态

> **⚠️ 注意**: 需要有效的抖音账号才能采集视频内容。

#### 2. 📝 创建分析任务
1. 在首页输入 **抖音博主主页链接**
   ```
   示例: https://www.douyin.com/user/MS4wLjABAAAA...
   ```
2. 设置分析参数：
   - **视频数量**: 1-100个 (推荐10-20个)
   - **识别语言**: 中文/英文/自动检测
   - **模型大小**: small/medium/large (影响识别精度和速度)
3. 点击 **"开始分析"** 按钮

#### 3. 📊 监控任务进度
1. 自动跳转到 **"任务管理"** 页面
2. 实时查看任务执行状态：
   - 🟡 **运行中**: 正在处理
   - 🟢 **已完成**: 分析完成
   - 🔴 **失败**: 处理出错
3. 查看详细统计信息：
   - 总视频数、已处理、成功/失败数量
   - 实时进度条和预计剩余时间

#### 4. 📋 查看分析结果
1. 点击任务卡片上的 **"查看详情"** 按钮
2. 浏览完整的分析报告：
   - 📊 **任务信息**: 基本信息统计
   - 🎬 **视频列表**: 每个视频的转录内容
   - 🤖 **AI分析报告**: 深度风格分析
3. 支持的功能：
   - 📤 **导出PDF**: 生成完整的分析报告
   - 📋 **复制文案**: 快速复制转录文本
   - 🔄 **重新生成**: 重新生成AI分析报告

### 💡 使用技巧

1. **🎯 选择合适的视频数量**
   - 新手博主: 5-10个视频
   - 成熟博主: 15-30个视频
   - 深度分析: 50+个视频

2. **⚡ 优化处理速度**
   - 使用 `small` 模型快速处理
   - 避免同时运行多个任务
   - 确保网络连接稳定

3. **📊 分析报告解读**
   - **战略定位**: 博主的角色定位和价值主张
   - **内容架构**: 内容创作的结构化分析
   - **语言修辞**: 语言风格和表达技巧
   - **理论支撑**: 背后的心理学和营销理论
   - **战略建议**: 可操作的内容优化建议

## 🔧 配置说明

### 📝 环境变量配置

项目使用环境变量进行配置管理，所有配置项都在 `env.example` 文件中有详细说明。

#### 🔐 安全配置 (必须修改)
| 变量名 | 说明 | 示例 |
|--------|------|------|
| `SECRET_KEY` | Flask应用密钥，用于会话加密 | `your-secret-key-here` |
| `JWT_SECRET_KEY` | JWT认证密钥，用于用户认证 | `your-jwt-secret-key-here` |

#### 🤖 AI服务配置
| 变量名 | 说明 | 默认值 | 获取方式 |
|--------|------|--------|----------|
| `DEEPSEEK_API_KEY` | DeepSeek API密钥，用于AI分析 | - | [DeepSeek平台](https://platform.deepseek.com/) |

#### 🎤 语音识别配置
| 变量名 | 说明 | 可选值 | 推荐值 |
|--------|------|--------|--------|
| `WHISPER_MODEL_SIZE` | Whisper模型大小 | tiny, base, small, medium, large | small |
| `WHISPER_DEVICE` | 计算设备 | cpu, cuda | cpu |

#### ⚙️ 任务处理配置
| 变量名 | 说明 | 默认值 | 建议范围 |
|--------|------|--------|----------|
| `MAX_CONCURRENT_TASKS` | 最大并发任务数 | 3 | 1-5 |
| `TASK_TIMEOUT` | 任务超时时间(秒) | 3600 | 1800-7200 |

#### 🌐 应用运行配置
| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `FLASK_ENV` | 运行环境 | production |
| `FLASK_HOST` | 监听地址 | 0.0.0.0 |
| `FLASK_PORT` | 监听端口 | 5005 |

### 📋 配置步骤

1. **复制配置文件**
```bash
cp env.example .env
```

2. **编辑配置文件**
```bash
nano .env  # 或使用其他编辑器
```

3. **必须修改的配置**
   - `SECRET_KEY`: 生成一个强随机密钥
   - `JWT_SECRET_KEY`: 生成另一个强随机密钥
   - `DEEPSEEK_API_KEY`: 填入您的DeepSeek API密钥

4. **可选优化配置**
   - 根据服务器性能调整 `MAX_CONCURRENT_TASKS`
   - 根据网络情况调整 `TASK_TIMEOUT`
   - 根据硬件配置选择 `WHISPER_MODEL_SIZE` 和 `WHISPER_DEVICE`

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
   - 确保Chrome浏览器版本与ChromeDriver版本匹配

2. **语音识别失败**
   - 检查音频文件是否存在
   - 确认 Whisper 模型已正确下载
   - 检查磁盘空间是否充足

3. **数据库连接失败**
   - 检查数据库配置
   - 确认数据库文件权限正确
   - 运行 `python scripts/init_db.py init` 重新初始化

4. **任务执行超时**
   - 增加 `TASK_TIMEOUT` 配置
   - 检查网络连接状态
   - 减少并发任务数量

5. **视频下载失败**
   - 检查网络连接
   - 确认抖音登录状态有效
   - 尝试重新登录抖音账号

6. **AI分析失败**
   - 检查 `DEEPSEEK_API_KEY` 配置
   - 确认API密钥有效且有足够额度
   - 检查网络连接

### 日志查看
```bash
# 查看应用日志
tail -f logs/app.log

# 查看实时日志
python run.py  # 在终端中查看实时输出
```

### 快速修复
```bash
# 重新初始化数据库
python scripts/init_db.py init

# 清理临时文件
rm -rf temp/audio/*
rm -rf output/*

# 重新安装依赖
pip install -r requirements.txt --force-reinstall
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