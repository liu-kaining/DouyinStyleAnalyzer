# DouyinStyleAnalyzer 部署指南

## 系统要求

### 硬件要求
- **CPU**: 4核心以上
- **内存**: 8GB以上（推荐16GB）
- **存储**: 50GB以上可用空间
- **GPU**: 可选，支持CUDA的GPU可加速语音识别

### 软件要求
- **操作系统**: Linux (Ubuntu 20.04+), macOS, Windows
- **Python**: 3.8+
- **Chrome浏览器**: 用于视频采集
- **FFmpeg**: 用于音频处理

## 安装步骤

### 1. 克隆项目
```bash
git clone <repository-url>
cd DouyinStyleAnalyzer
```

### 2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 安装系统依赖

#### Ubuntu/Debian
```bash
# 安装Chrome浏览器
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update
sudo apt install google-chrome-stable

# 安装FFmpeg
sudo apt install ffmpeg
```

#### macOS
```bash
# 使用Homebrew安装
brew install --cask google-chrome
brew install ffmpeg
```

#### Windows
- 下载并安装 [Chrome浏览器](https://www.google.com/chrome/)
- 下载并安装 [FFmpeg](https://ffmpeg.org/download.html)

### 5. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，设置必要的配置
```

### 6. 初始化数据库
```bash
python scripts/init_db.py
```

### 7. 启动应用
```bash
python run.py
```

## 配置说明

### 环境变量配置

创建 `.env` 文件并配置以下变量：

```env
# Flask配置
FLASK_ENV=production
FLASK_HOST=0.0.0.0
FLASK_PORT=5005
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here

# 数据库配置
DATABASE_URL=sqlite:///app.db
# 或使用PostgreSQL
# DATABASE_URL=postgresql://user:password@localhost/douyinstyleanalyzer

# 存储路径
AUDIO_DIR=./audio
OUTPUT_DIR=./output
TEMP_DIR=./temp
CHROME_USER_DATA_DIR=~/.douyin_browser

# Whisper配置
WHISPER_MODEL_SIZE=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8

# 任务配置
MAX_CONCURRENT_TASKS=2
TASK_STATUS_UPDATE_INTERVAL=5
MAX_SCROLL_COUNT=15

# 用户配额
DEFAULT_QUOTA=100
PREMIUM_QUOTA=1000
```

### 生产环境配置

#### 使用Gunicorn部署
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5005 run:app
```

#### 使用Nginx反向代理
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5005;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Docker部署

### 1. 构建镜像
```bash
docker build -t douyinstyleanalyzer .
```

### 2. 运行容器
```bash
docker run -d \
  --name douyinstyleanalyzer \
  -p 5005:5005 \
  -v $(pwd)/data:/app/data \
  -e FLASK_ENV=production \
  douyinstyleanalyzer
```

### 3. 使用Docker Compose
```bash
docker-compose up -d
```

## 监控和维护

### 日志查看
```bash
# 查看应用日志
tail -f logs/douyinstyleanalyzer.log

# 查看系统状态
curl http://localhost:5005/api/v1/system/status
```

### 数据库备份
```bash
# SQLite备份
cp app.db app.db.backup.$(date +%Y%m%d_%H%M%S)

# PostgreSQL备份
pg_dump douyinstyleanalyzer > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 清理临时文件
```bash
# 清理音频文件
find ./audio -name "*.mp3" -mtime +7 -delete

# 清理输出文件
find ./output -name "*.json" -mtime +30 -delete
```

## 故障排除

### 常见问题

1. **Chrome浏览器启动失败**
   - 确保Chrome已正确安装
   - 检查Chrome用户数据目录权限
   - 尝试使用无头模式

2. **语音识别失败**
   - 检查FFmpeg是否正确安装
   - 验证音频文件格式
   - 检查Whisper模型下载

3. **数据库连接失败**
   - 检查数据库URL配置
   - 确保数据库服务正在运行
   - 验证数据库权限

4. **内存不足**
   - 减少并发任务数量
   - 使用更小的Whisper模型
   - 增加系统内存

### 性能优化

1. **使用GPU加速**
   ```env
   WHISPER_DEVICE=cuda
   WHISPER_COMPUTE_TYPE=float16
   ```

2. **调整并发设置**
   ```env
   MAX_CONCURRENT_TASKS=1  # 减少并发任务
   ```

3. **使用SSD存储**
   - 将音频和输出目录放在SSD上
   - 定期清理临时文件

## 安全建议

1. **更改默认密钥**
   - 使用强密码作为SECRET_KEY和JWT_SECRET_KEY
   - 定期轮换密钥

2. **配置防火墙**
   - 只开放必要的端口
   - 使用HTTPS加密传输

3. **定期更新**
   - 保持系统和依赖包更新
   - 监控安全漏洞

4. **访问控制**
   - 配置用户认证
   - 限制API访问频率

## 支持

如有问题，请查看：
- [项目文档](docs/)
- [API文档](http://localhost:5005/api/v1/system/status)
- [GitHub Issues](https://github.com/your-repo/issues)
