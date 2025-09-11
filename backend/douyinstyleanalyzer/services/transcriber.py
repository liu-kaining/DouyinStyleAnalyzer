"""
语音识别服务 - 使用 yt-dlp 和 Faster-Whisper 进行语音转文字
"""

import os
import time
import json
from typing import Optional, Dict, Any
import yt_dlp
from faster_whisper import WhisperModel
from ..config import Config
from ..utils.retry import retry_on_failure, RetryManager, RetryConfig


class VideoTranscriber:
    """视频语音识别器"""
    
    def __init__(self):
        self.config = Config()
        self.model = None
        
        # 初始化重试管理器
        retry_config = RetryConfig(
            max_retries=self.config.MAX_RETRY_COUNT,
            base_delay=self.config.RETRY_DELAY_BASE,
            max_delay=self.config.RETRY_DELAY_MAX,
            backoff_factor=self.config.RETRY_BACKOFF_FACTOR
        )
        self.retry_manager = RetryManager(retry_config)
        
        self._initialize_model()
    
    def _initialize_model(self):
        """初始化 Whisper 模型"""
        try:
            print(f"🤖 正在初始化 Whisper 模型: {self.config.WHISPER_MODEL_SIZE}")
            
            self.model = WhisperModel(
                self.config.WHISPER_MODEL_SIZE,
                device=self.config.WHISPER_DEVICE,
                compute_type=self.config.WHISPER_COMPUTE_TYPE
            )
            
            print("✅ Whisper 模型初始化成功")
            
        except Exception as e:
            print(f"❌ Whisper 模型初始化失败: {e}")
            self.model = None
    
    def download_video(self, video_url: str, output_name: str, cookies=None) -> Optional[str]:
        """下载音频文件（使用yt-dlp）"""
        try:
            print(f"📥 正在下载音频: {output_name}")
            
            # 确保输出目录存在
            import os
            os.makedirs(self.config.AUDIO_DIR, exist_ok=True)
            
            # 检查是否已存在音频文件
            possible_files = [
                os.path.join(self.config.AUDIO_DIR, f"{output_name}.mp3"),
                os.path.join(self.config.AUDIO_DIR, f"{output_name}.m4a"),
                os.path.join(self.config.AUDIO_DIR, f"{output_name}.webm"),
                os.path.join(self.config.AUDIO_DIR, f"{output_name}.ogg"),
            ]
            
            for audio_file in possible_files:
                if os.path.exists(audio_file):
                    print(f"📁 {os.path.basename(audio_file)} 已存在，跳过下载")
                    return audio_file
            
            # 尝试多种下载方法
            # 方法1: 使用yt-dlp下载
            result = self._download_with_ytdlp(video_url, output_name, cookies)
            if result:
                return result
            
            # 方法2: 如果yt-dlp失败，尝试使用Selenium获取真实URL
            print("⚠️ yt-dlp下载失败，尝试使用Selenium获取真实URL...")
            return self._download_with_selenium_fallback(video_url, output_name, cookies)
                    
        except Exception as e:
            print(f"❌ 音频下载过程出错: {e}")
            return None
    
    def _download_with_ytdlp(self, video_url: str, output_name: str, cookies=None) -> Optional[str]:
        """使用yt-dlp下载视频音频"""
        try:
            print("📥 使用yt-dlp下载视频...")
            
            # 准备输出文件路径
            audio_file = os.path.join(self.config.AUDIO_DIR, f"{output_name}.%(ext)s")
            
            # yt-dlp配置
            ydl_opts = {
                'format': 'bestaudio/best',  # 优先选择最佳音频
                'outtmpl': audio_file,
                'extractaudio': True,
                'audioformat': 'mp3',
                'audioquality': '192K',
                'noplaylist': True,
                'quiet': False,
                'no_warnings': False,
                'extract_flat': False,
                'writethumbnail': False,
                'writeinfojson': False,
                'ignoreerrors': False,
                'no_check_certificate': True,
                'prefer_insecure': False,
                'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'referer': 'https://www.douyin.com/',
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': 'https://www.douyin.com/',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
            }
            
            # 如果有cookies，添加cookies配置
            if cookies:
                # 保存cookies到临时文件
                cookie_file = os.path.join(self.config.TEMP_DIR, f"cookies_{output_name}.txt")
                self._save_cookies_for_ytdlp(cookies, cookie_file)
                ydl_opts['cookiefile'] = cookie_file
                print(f"🍪 使用cookies文件: {cookie_file}")
            
            # 执行下载
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"🎬 开始下载: {video_url}")
                ydl.download([video_url])
            
            # 查找下载的文件
            possible_files = [
                os.path.join(self.config.AUDIO_DIR, f"{output_name}.mp3"),
                os.path.join(self.config.AUDIO_DIR, f"{output_name}.m4a"),
                os.path.join(self.config.AUDIO_DIR, f"{output_name}.webm"),
                os.path.join(self.config.AUDIO_DIR, f"{output_name}.ogg"),
            ]
            
            for file_path in possible_files:
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    print(f"🎉 音频下载成功: {file_path} ({file_size} bytes)")
                    
                    # 清理临时cookies文件
                    if cookies and 'cookiefile' in ydl_opts:
                        try:
                            os.remove(ydl_opts['cookiefile'])
                        except:
                            pass
                    
                    return file_path
            
            print("❌ 未找到下载的音频文件")
            return None
            
        except Exception as e:
            print(f"❌ yt-dlp下载失败: {e}")
            return None
    
    def _save_cookies_for_ytdlp(self, cookies, cookie_file):
        """保存cookies为yt-dlp格式"""
        try:
            with open(cookie_file, 'w', encoding='utf-8') as f:
                f.write("# Netscape HTTP Cookie File\n")
                f.write("# This file is generated by DouyinStyleAnalyzer for yt-dlp. Do not edit.\n\n")
                
                for cookie in cookies:
                    if isinstance(cookie, dict) and 'name' in cookie and 'value' in cookie:
                        # Netscape格式: domain, domain_specified, path, secure, expires, name, value
                        domain = cookie.get('domain', '.douyin.com')
                        path = cookie.get('path', '/')
                        secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
                        expires = str(cookie.get('expiry', 0))
                        name = cookie['name']
                        value = cookie['value']
                        
                        # 修复domain格式
                        if not domain.startswith('.'):
                            domain = '.' + domain
                        
                        domain_specified = 'TRUE' if domain.startswith('.') else 'FALSE'
                        
                        line = f"{domain}\t{domain_specified}\t{path}\t{secure}\t{expires}\t{name}\t{value}\n"
                        f.write(line)
            
            print(f"💾 已保存cookies到文件: {cookie_file}")
            
        except Exception as e:
            print(f"⚠️ 保存cookies文件失败: {e}")
    
    def _download_with_selenium_fallback(self, video_url: str, output_name: str, cookies=None) -> Optional[str]:
        """Selenium备用下载方法 - 获取真实视频URL"""
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import requests
        import os
        import time
        
        driver = None
        try:
            print("🚀 启动Selenium浏览器（备用方法）...")
            
            # 设置Chrome选项
            options = Options()
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument("--start-maximized")
            options.add_argument("--mute-audio")
            options.add_argument("--headless")  # 无头模式
            
            # 使用用户数据目录保持登录状态，添加时间戳避免冲突
            import time
            user_data_dir = os.path.expanduser(f"~/.douyin_browser_{int(time.time())}")
            options.add_argument(f"--user-data-dir={user_data_dir}")
            
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print(f"🌐 打开视频页: {video_url}")
            driver.get(video_url)
            time.sleep(5)
            
            # 尝试多种方法获取视频源
            video_src = None
            
            # 方法1: 直接获取video标签的src
            try:
                video_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "video"))
                )
                video_src = video_element.get_attribute("src")
                video_current_src = video_element.get_attribute("currentSrc")
                video_src = video_src or video_current_src
                print(f"📹 方法1获取到视频源: {video_src[:100] if video_src else 'None'}...")
            except Exception as e:
                print(f"⚠️ 方法1失败: {e}")
            
            # 方法2: 从网络请求中获取
            if not video_src or video_src.startswith('blob:'):
                try:
                    print("🔍 尝试从网络请求中获取视频源...")
                    # 等待页面加载完成
                    time.sleep(3)
                    
                    # 执行JavaScript获取所有网络请求，更宽松地过滤视频URL
                    network_logs = driver.execute_script("""
                        const entries = performance.getEntriesByType('resource');
                        console.log('所有网络请求:', entries.map(e => e.name));
                        
                        const videoEntries = entries.filter(entry => {
                            const url = entry.name;
                            const isVideo = url.includes('.mp4') || url.includes('.m3u8') || url.includes('.webm') || url.includes('.flv');
                            const isNotEmoji = !url.includes('emoji');
                            const isNotApi = !url.includes('/api/');
                            const isNotJson = !url.includes('.json');
                            const isVideoDomain = url.includes('douyinvod.com') || url.includes('video') || url.includes('aweme') || url.includes('douyin');
                            
                            console.log('URL:', url, 'isVideo:', isVideo, 'isNotEmoji:', isNotEmoji, 'isNotApi:', isNotApi, 'isNotJson:', isNotJson, 'isVideoDomain:', isVideoDomain);
                            
                            return isVideo && isNotEmoji && isNotApi && isNotJson && isVideoDomain;
                        });
                        
                        console.log('过滤后的视频URL:', videoEntries.map(e => e.name));
                        return videoEntries.map(entry => entry.name);
                    """)
                    
                    if network_logs:
                        video_src = network_logs[0]
                        print(f"📹 方法2获取到视频源: {video_src[:100]}...")
                except Exception as e:
                    print(f"⚠️ 方法2失败: {e}")
            
            # 方法3: 尝试获取m3u8播放列表
            if not video_src or video_src.startswith('blob:'):
                try:
                    print("🔍 尝试获取m3u8播放列表...")
                    # 查找包含m3u8的链接
                    m3u8_elements = driver.find_elements(By.XPATH, "//*[contains(@src, '.m3u8') or contains(@href, '.m3u8')]")
                    if m3u8_elements:
                        video_src = m3u8_elements[0].get_attribute("src") or m3u8_elements[0].get_attribute("href")
                        print(f"📹 方法3获取到视频源: {video_src[:100]}...")
                except Exception as e:
                    print(f"⚠️ 方法3失败: {e}")
            
            # 方法4: 等待更长时间并重新尝试获取网络请求
            if not video_src or video_src.startswith('blob:'):
                try:
                    print("🔍 方法4: 等待更长时间并重新分析网络请求...")
                    time.sleep(5)  # 等待更长时间
                    
                    # 尝试点击播放按钮或滚动页面触发视频加载
                    try:
                        # 查找并点击播放按钮
                        play_buttons = driver.find_elements(By.XPATH, "//button[contains(@class, 'play') or contains(@class, 'Play')]")
                        if play_buttons:
                            play_buttons[0].click()
                            time.sleep(2)
                    except:
                        pass
                    
                    # 重新获取网络请求
                    network_logs = driver.execute_script("""
                        const entries = performance.getEntriesByType('resource');
                        console.log('方法4 - 所有网络请求:', entries.map(e => e.name));
                        
                        // 更宽松的过滤条件
                        const videoEntries = entries.filter(entry => {
                            const url = entry.name;
                            return (url.includes('.mp4') || url.includes('.m3u8') || url.includes('.webm') || url.includes('.flv')) &&
                                   !url.includes('emoji') &&
                                   !url.includes('/api/') &&
                                   !url.includes('.json') &&
                                   (url.includes('douyinvod.com') || url.includes('video') || url.includes('aweme') || url.includes('douyin') || url.includes('amemv'));
                        });
                        
                        console.log('方法4 - 过滤后的视频URL:', videoEntries.map(e => e.name));
                        return videoEntries.map(entry => entry.name);
                    """)
                    
                    if network_logs:
                        video_src = network_logs[0]
                        print(f"📹 方法4获取到视频源: {video_src[:100]}...")
                except Exception as e:
                    print(f"⚠️ 方法4失败: {e}")
            
            if not video_src or video_src.startswith('blob:'):
                print("❌ 无法获取有效的视频源")
                return None
            
            # 下载视频
            audio_file = os.path.join(self.config.AUDIO_DIR, f"{output_name}.mp4")
            
            print("⏬ 开始下载视频文件...")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.douyin.com/',
            }
            
            response = requests.get(video_src, headers=headers, stream=True)
            response.raise_for_status()
            
            with open(audio_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            file_size = os.path.getsize(audio_file)
            print(f"🎉 视频下载成功: {audio_file} ({file_size} bytes)")
            return audio_file
            
        except Exception as e:
            print(f"❌ Selenium备用下载失败: {e}")
            return None
        finally:
            if driver:
                print("🔒 关闭浏览器...")
                driver.quit()
    
    def transcribe_video(self, video_path: str, language: str = "zh") -> Dict[str, Any]:
        """转录音频文件"""
        try:
            import os
            
            if not self.model:
                return {
                    "success": False,
                    "error": "Whisper 模型未初始化",
                    "transcript": "",
                    "confidence": 0.0,
                    "language": language
                }
            
            if not os.path.exists(video_path):
                return {
                    "success": False,
                    "error": f"视频文件不存在: {video_path}",
                    "transcript": "",
                    "confidence": 0.0,
                    "language": language
                }
            
            print(f"🎤 正在转录音频: {os.path.basename(video_path)}")
            
            # 执行转录 - 使用更高质量的参数提高置信度
            segments, info = self.model.transcribe(
                video_path,
                language=language if language != "auto" else None,
                beam_size=10,  # 增加beam size提高准确性
                best_of=5,     # 生成多个候选结果
                temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],  # 多温度采样
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=300,  # 减少静音阈值
                    speech_pad_ms=200             # 减少语音填充
                ),
                word_timestamps=True,
                condition_on_previous_text=True,  # 基于前文条件
                initial_prompt="以下是普通话的句子。" if language == "zh" else None  # 中文提示
            )
            
            # 合并所有片段
            transcript_parts = []
            total_confidence = 0.0
            segment_count = 0
            
            for segment in segments:
                if segment.text.strip():
                    transcript_parts.append(segment.text.strip())
                    total_confidence += getattr(segment, 'avg_logprob', 0.0)
                    segment_count += 1
            
            # 计算平均置信度
            avg_confidence = total_confidence / segment_count if segment_count > 0 else 0.0
            
            # 合并转录文本
            transcript = " ".join(transcript_parts).strip()
            
            # 检测到的语言
            detected_language = getattr(info, 'language', language)
            
            result = {
                "success": True,
                "transcript": transcript,
                "confidence": abs(avg_confidence),  # 转换为正数
                "language": detected_language,
                "segment_count": segment_count,
                "duration": getattr(info, 'duration', 0.0)
            }
            
            print(f"✅ 转录完成: {len(transcript)} 字符, 置信度: {result['confidence']:.2f}")
            return result
            
        except Exception as e:
            print(f"❌ 音频转录失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "transcript": "",
                "confidence": 0.0,
                "language": language
            }
    
    def process_video(self, video_url: str, video_id: str, language: str = "zh", cookies=None) -> Dict[str, Any]:
        """处理单个视频：下载视频并转录"""
        def _process_video_internal():
            print(f"🎬 开始处理视频: {video_id}")
            
            # 下载视频
            video_path = self.download_video(video_url, video_id, cookies)
            if not video_path:
                raise Exception("视频下载失败")
            
            # 转录视频
            transcription_result = self.transcribe_video(video_path, language)
            
            # 添加视频文件信息
            transcription_result["video_file"] = video_path
            transcription_result["video_file_size"] = os.path.getsize(video_path) if os.path.exists(video_path) else 0
            
            return transcription_result
        
        # 使用重试机制执行处理
        try:
            return self.retry_manager.retry(_process_video_internal)
        except Exception as e:
            print(f"❌ 视频处理失败（已重试 {self.config.MAX_RETRY_COUNT} 次）: {e}")
            return {
                "success": False,
                "error": str(e),
                "transcript": "",
                "confidence": 0.0,
                "language": language,
                "video_file": None
            }
    
    def cleanup_audio_file(self, audio_path: str):
        """清理音频文件"""
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
                print(f"🗑️ 已清理音频文件: {os.path.basename(audio_path)}")
        except Exception as e:
            print(f"⚠️ 清理音频文件失败: {e}")
    
    def batch_process_videos(self, videos: list, language: str = "zh") -> list:
        """批量处理视频"""
        results = []
        
        for i, video in enumerate(videos, 1):
            print(f"\n📹 处理进度: {i}/{len(videos)}")
            
            video_id = video.get("video_id")
            video_url = video.get("url")
            
            if not video_id or not video_url:
                print(f"⚠️ 跳过无效视频: {video}")
                continue
            
            # 处理视频
            result = self.process_video(video_url, video_id, language)
            
            # 更新视频数据
            video.update({
                "transcript": result.get("transcript", ""),
                "transcript_confidence": result.get("confidence", 0.0),
                "language_detected": result.get("language", language),
                "processing_success": result.get("success", False),
                "processing_error": result.get("error", "")
            })
            
            results.append(video)
            
            # 添加延迟避免过载
            if i < len(videos):
                time.sleep(1)
        
        return results


def transcribe_video(video_url: str, video_id: str, language: str = "zh") -> Dict[str, Any]:
    """转录音频的便捷函数"""
    transcriber = VideoTranscriber()
    return transcriber.process_video(video_url, video_id, language)
