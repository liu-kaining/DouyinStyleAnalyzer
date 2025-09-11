# 重试机制和可靠性改进

## 概述

本次更新大幅提升了抖音视频抓取和分析系统的可靠性和稳定性，主要实现了以下功能：

## 🚀 主要改进

### 1. 重试机制 (Retry Mechanism)

#### 功能特性
- **最大重试次数**: 10次（可配置）
- **指数退避算法**: 避免雷群效应
- **随机抖动**: 防止同时重试
- **智能重试判断**: 根据异常类型决定是否重试

#### 配置参数
```python
MAX_RETRY_COUNT = 10          # 最大重试次数
RETRY_DELAY_BASE = 2          # 基础延迟时间（秒）
RETRY_DELAY_MAX = 60          # 最大延迟时间（秒）
RETRY_BACKOFF_FACTOR = 2.0    # 退避因子
```

#### 重试策略
- 第1次重试: 等待 2-3 秒
- 第2次重试: 等待 4-6 秒
- 第3次重试: 等待 8-12 秒
- 以此类推，最大不超过60秒

### 2. 语音识别置信度提升

#### 优化参数
```python
beam_size=10                    # 增加beam size提高准确性
best_of=5                       # 生成多个候选结果
temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0]  # 多温度采样
condition_on_previous_text=True # 基于前文条件
initial_prompt="以下是普通话的句子。"  # 中文提示
```

#### 改进效果
- 提高转录准确性
- 更好的中文识别效果
- 减少转录错误

### 3. 实时持久化

#### 数据保存策略
- **视频采集**: 每10个视频保存一次到数据库
- **转录处理**: 每个视频处理完成后立即保存
- **进度更新**: 实时更新任务进度和状态

#### 优势
- 避免数据丢失
- 实时查看进度
- 支持任务中断恢复

### 4. 错误处理和日志

#### 新增字段
```sql
last_retry_at DATETIME    -- 最后重试时间
retry_errors TEXT         -- 重试错误历史（JSON格式）
```

#### 错误记录
- 记录每次重试的详细信息
- 保存错误时间戳
- 最多保留最近20条错误记录

## 🔧 技术实现

### 重试工具类 (`utils/retry.py`)

```python
class RetryManager:
    def retry(self, func, *args, **kwargs):
        # 执行带重试的函数
        
@retry_on_failure(max_retries=10)
def some_function():
    # 自动重试装饰器
```

### 抓取器改进 (`services/scraper.py`)

- 集成重试管理器
- 包装核心采集逻辑
- 智能错误处理

### 转录器改进 (`services/transcriber.py`)

- 提高转录参数质量
- 添加重试机制
- 优化错误处理

### 任务管理器改进 (`services/task_manager.py`)

- 实时数据库更新
- 重试状态跟踪
- 详细进度报告

## 📊 使用示例

### 查看重试信息

```python
# 获取视频记录
video = VideoData.query.filter_by(video_id="123").first()

# 查看重试次数
print(f"重试次数: {video.retry_count}")

# 查看重试错误历史
errors = video.get_retry_errors()
for error in errors:
    print(f"第 {error['retry_count']} 次重试失败: {error['error_message']}")

# 检查是否可以重试
can_retry = video.can_retry(max_retries=10)
```

### 配置重试参数

```bash
# 环境变量配置
export MAX_RETRY_COUNT=15
export RETRY_DELAY_BASE=3
export RETRY_DELAY_MAX=120
export RETRY_BACKOFF_FACTOR=1.5
```

## 🎯 效果对比

### 改进前
- ❌ 失败后直接结束
- ❌ 无重试机制
- ❌ 批量保存数据
- ❌ 错误信息不详细

### 改进后
- ✅ 智能重试机制
- ✅ 最大10次重试
- ✅ 实时数据持久化
- ✅ 详细错误记录
- ✅ 高置信度转录
- ✅ 指数退避算法

## 🚀 部署说明

### 1. 数据库迁移
```bash
python scripts/migrate_retry_fields.py
```

### 2. 测试重试机制
```bash
python scripts/test_retry_mechanism.py
```

### 3. 重启应用
```bash
python run.py
```

## 📈 监控和调试

### 日志输出示例
```
🔄 第 1 次重试失败: 网络连接超时
⏳ 等待 2.3 秒后重试...
🔄 第 2 次重试失败: 页面加载失败
⏳ 等待 4.7 秒后重试...
✅ 视频采集成功
💾 已保存 10/50 个视频到数据库
```

### 数据库查询
```sql
-- 查看重试统计
SELECT 
    retry_count,
    COUNT(*) as count
FROM video_data 
GROUP BY retry_count;

-- 查看失败原因
SELECT 
    video_id,
    retry_count,
    error_message,
    last_retry_at
FROM video_data 
WHERE processing_status = 'failed'
ORDER BY last_retry_at DESC;
```

## 🔮 未来优化

1. **动态重试策略**: 根据错误类型调整重试间隔
2. **重试队列**: 实现异步重试队列
3. **监控面板**: 可视化重试统计和成功率
4. **智能降级**: 在多次失败后自动降低处理要求

---

通过这些改进，系统的可靠性和稳定性得到了显著提升，能够更好地处理网络波动、服务器异常等临时性问题，确保任务能够最大程度地成功完成。
