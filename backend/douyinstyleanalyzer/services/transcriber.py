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


class VideoTranscriber:
    """视频语音识别器"""
    
    def __init__(self):
        self.config = Config()
        self.model = None
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
        """下载音频文件（使用Selenium直接获取video src）"""
        try:
            print(f"📥 正在下载音频: {output_name}")
            
            # 确保输出目录存在
            import os
            os.makedirs(self.config.AUDIO_DIR, exist_ok=True)
            
            # 检查是否已存在音频文件
            audio_file = os.path.join(self.config.AUDIO_DIR, f"{output_name}.m4a")
            if os.path.exists(audio_file):
                print(f"📁 {output_name}.m4a 已存在，跳过下载")
                return audio_file
            
            # 使用Selenium直接获取video src
            return self._download_with_selenium(video_url, output_name)
                    
        except Exception as e:
            print(f"❌ 音频下载过程出错: {e}")
            return None
    
    def _download_with_selenium(self, video_url: str, output_name: str) -> Optional[str]:
        """使用Selenium直接获取video src并下载"""
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
            print("🚀 启动Selenium浏览器...")
            
            # 设置Chrome选项
            options = Options()
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument("--start-maximized")
            options.add_argument("--mute-audio")
            
            # 使用用户数据目录保持登录状态
            user_data_dir = os.path.expanduser("~/.douyin_browser")
            options.add_argument(f"--user-data-dir={user_data_dir}")
            
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print(f"🌐 打开视频页: {video_url}")
            driver.get(video_url)
            time.sleep(5)
            
            # 获取video src
            video_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "video"))
            )
            
            video_src = video_element.get_attribute("src")
            video_current_src = video_element.get_attribute("currentSrc")
            final_src = video_src or video_current_src
            
            if not final_src:
                print("❌ 未找到video src")
                return None
            
            print(f"✅ 获取到视频源: {final_src[:100]}...")
            
            # 下载音频流
            audio_file = os.path.join(self.config.AUDIO_DIR, f"{output_name}.m4a")
            
            print("⏬ 开始下载原始音频流...")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
                'Referer': 'https://www.douyin.com/',
            }
            
            response = requests.get(final_src, headers=headers, stream=True)
            response.raise_for_status()
            
            with open(audio_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            file_size = os.path.getsize(audio_file)
            print(f"🎉 音频下载成功: {audio_file} ({file_size} bytes)")
            return audio_file
            
        except Exception as e:
            print(f"❌ Selenium下载失败: {e}")
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
            
            # 执行转录
            segments, info = self.model.transcribe(
                video_path,
                language=language if language != "auto" else None,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=400
                ),
                word_timestamps=True
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
        try:
            print(f"🎬 开始处理视频: {video_id}")
            
            # 下载视频
            video_path = self.download_video(video_url, video_id, cookies)
            if not video_path:
                return {
                    "success": False,
                    "error": "视频下载失败",
                    "transcript": "",
                    "confidence": 0.0,
                    "language": language,
                    "video_file": None
                }
            
            # 转录视频
            transcription_result = self.transcribe_video(video_path, language)
            
            # 添加视频文件信息
            transcription_result["video_file"] = video_path
            transcription_result["video_file_size"] = os.path.getsize(video_path) if os.path.exists(video_path) else 0
            
            return transcription_result
            
        except Exception as e:
            print(f"❌ 视频处理失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "transcript": "",
                "confidence": 0.0,
                "language": language,
                "audio_file": None
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
