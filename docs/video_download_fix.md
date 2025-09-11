# 视频下载问题修复

## 问题描述

在运行抖音视频分析任务时，发现视频下载失败的问题：

```
❌ Selenium下载失败: No connection adapters were found for 'blob:https://www.douyin.com/c58df085-fce2-4c24-a694-d86af044e3d7'
```

## 问题分析

### 根本原因
1. **Blob URL问题**: 抖音使用 `blob:` URL，这是浏览器内部的媒体流，无法直接用HTTP请求下载
2. **yt-dlp限制**: yt-dlp需要有效的cookies才能下载抖音视频
3. **单一下载策略**: 原来只使用Selenium直接获取video src，遇到blob URL就失败

### 错误日志分析
```
✅ 获取到视频源: blob:https://www.douyin.com/c58df085-fce2-4c24-a694-d86af044e3d7...
⏬ 开始下载原始音频流...
❌ Selenium下载失败: No connection adapters were found for 'blob:...'
```

## 解决方案

### 1. 多重下载策略

实现了三种下载方法的组合：

#### 方法1: yt-dlp下载
```python
def _download_with_ytdlp(self, video_url: str, output_name: str, cookies=None):
    # 使用yt-dlp下载，支持多种格式
    ydl_opts = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'cookiefile': cookie_file  # 使用cookies
    }
```

#### 方法2: Selenium备用下载
```python
def _download_with_selenium_fallback(self, video_url: str, output_name: str, cookies=None):
    # 多种方法获取真实视频URL
    # 方法1: 直接获取video标签的src
    # 方法2: 从网络请求中获取
    # 方法3: 获取m3u8播放列表
```

#### 方法3: 智能回退机制
```python
# 尝试多种下载方法
result = self._download_with_ytdlp(video_url, output_name, cookies)
if result:
    return result

# 如果yt-dlp失败，尝试使用Selenium获取真实URL
return self._download_with_selenium_fallback(video_url, output_name, cookies)
```

### 2. 改进的URL获取策略

#### 网络请求分析
```javascript
// 执行JavaScript获取所有网络请求
network_logs = driver.execute_script("""
    return performance.getEntriesByType('resource')
        .filter(entry => entry.name.includes('.mp4') || entry.name.includes('.m3u8') || entry.name.includes('video'))
        .map(entry => entry.name);
""")
```

#### 多种视频源检测
- 直接video标签src属性
- 网络请求中的视频资源
- m3u8播放列表链接
- 避免blob URL

### 3. Cookies管理优化

#### 动态cookies处理
```python
def _save_cookies_for_ytdlp(self, cookies, cookie_file):
    # 保存cookies为yt-dlp格式
    # Netscape HTTP Cookie File格式
    # 自动清理临时cookies文件
```

#### 多格式支持
- 支持多种音频格式：mp3, m4a, webm, ogg
- 自动检测已下载文件
- 智能文件清理

## 技术实现

### 下载流程
```
1. 检查是否已存在音频文件
2. 尝试yt-dlp下载（优先）
3. 如果失败，使用Selenium备用方法
4. 多种方法获取真实视频URL
5. 下载并返回文件路径
```

### 错误处理
- 每种方法都有独立的异常处理
- 详细的日志输出
- 自动重试机制（继承之前的重试系统）

### 性能优化
- 无头模式运行Selenium
- 智能文件检测，避免重复下载
- 临时文件自动清理

## 测试验证

### 测试脚本
```bash
python scripts/test_ytdlp_download.py
```

### 预期结果
- yt-dlp成功下载（需要有效cookies）
- 或Selenium备用方法成功获取真实URL
- 支持多种音频格式
- 完整的错误日志

## 配置参数

### yt-dlp配置
```python
ydl_opts = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'audioquality': '192K',
    'noplaylist': True,
    'user_agent': 'Mozilla/5.0...',
    'referer': 'https://www.douyin.com/',
}
```

### Selenium配置
```python
options = Options()
options.add_argument("--headless")  # 无头模式
options.add_argument("--mute-audio")
options.add_argument("--disable-blink-features=AutomationControlled")
```

## 使用效果

### 改进前
- ❌ 遇到blob URL直接失败
- ❌ 无备用下载方法
- ❌ 重试机制无效（因为根本问题没解决）

### 改进后
- ✅ 多重下载策略
- ✅ 智能URL获取
- ✅ 支持多种音频格式
- ✅ 完整的错误处理
- ✅ 与重试机制完美配合

## 部署说明

1. **无需额外依赖**: 使用现有的yt-dlp和Selenium
2. **向后兼容**: 不影响现有功能
3. **自动回退**: 如果一种方法失败，自动尝试其他方法
4. **日志完整**: 详细的下载过程日志

## 监控建议

### 关键指标
- 下载成功率
- 各种下载方法的使用频率
- 平均下载时间
- 错误类型分布

### 日志关键词
- `yt-dlp下载成功`
- `Selenium备用下载成功`
- `无法获取有效的视频源`
- `Fresh cookies are needed`

---

通过这个修复，系统现在能够更好地处理抖音视频下载的各种情况，大大提高了下载成功率和系统的稳定性。
