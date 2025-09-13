"""
任务管理服务 - 管理分析任务的执行和状态
"""

import os
import json
import time
import threading
import traceback
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from ..models import AnalysisTask, VideoData, TaskStatus, TaskStep
from .. import db
from .scraper import DouyinVideoScraper
from .transcriber import VideoTranscriber
from ..config import Config
from ..utils.retry import retry_on_failure


class TaskManager:
    """任务管理器 - 支持并发任务和队列管理"""
    
    def __init__(self):
        self.config = Config()
        self.running_tasks = {}  # 存储正在运行的任务
        self.task_queue = []  # 任务队列
        self.task_lock = threading.Lock()
        self.max_concurrent_tasks = 5  # 最大并发任务数
    
    def start_analysis_task(self, task_id: str, app, cookies=None) -> bool:
        """启动分析任务，支持队列管理"""
        try:
            with self.task_lock:
                if task_id in self.running_tasks:
                    print(f"⚠️ 任务 {task_id} 已在运行")
                    return False
                
                # 检查是否达到最大并发数
                if len(self.running_tasks) >= self.max_concurrent_tasks:
                    # 添加到队列
                    self.task_queue.append({
                        "task_id": task_id,
                        "app": app,
                        "cookies": cookies,
                        "queued_at": datetime.now(timezone(timedelta(hours=8)))
                    })
                    print(f"📋 任务 {task_id} 已加入队列，当前队列长度: {len(self.task_queue)}")
                    return True
                
                # 直接启动任务
                return self._start_task_immediately(task_id, app, cookies)
                
        except Exception as e:
            print(f"❌ 启动任务失败: {e}")
            return False
    
    def _start_task_immediately(self, task_id: str, app, cookies=None) -> bool:
        """立即启动任务"""
        try:
            # 标记任务为运行中
            self.running_tasks[task_id] = {
                "thread": None,
                "start_time": datetime.now(timezone(timedelta(hours=8))),
                "cookies": cookies
            }
            
            # 启动后台线程，传递Flask应用实例和cookies
            thread = threading.Thread(
                target=self._execute_task_with_app,
                args=(task_id, app, cookies),
                daemon=True
            )
            thread.start()
            
            self.running_tasks[task_id]["thread"] = thread
            
            print(f"🚀 任务 {task_id} 已启动 (并发数: {len(self.running_tasks)}/{self.max_concurrent_tasks})")
            return True
            
        except Exception as e:
            print(f"❌ 立即启动任务失败: {e}")
            return False
    
    def _execute_task_with_app(self, task_id: str, app, cookies=None):
        """在Flask应用上下文中执行任务，支持重试和容错"""
        with app.app_context():
            max_retries = 3
            retry_count = 0
            
            while retry_count <= max_retries:
                try:
                    task = AnalysisTask.query.get(task_id)
                    if not task:
                        print(f"❌ 任务 {task_id} 不存在")
                        return
                    
                    if retry_count > 0:
                        print(f"🔄 任务 {task_id} 第 {retry_count} 次重试")
                        task.update_status(TaskStatus.RUNNING, TaskStep.INITIALIZING, 
                                         error_message=f"第 {retry_count} 次重试")
                    else:
                        print(f"🎯 开始执行任务: {task_id}")
                    
                    # 更新任务状态为运行中
                    task.update_status(TaskStatus.RUNNING, TaskStep.INITIALIZING)
                    
                    # 步骤1: 视频采集（带重试）
                    videos, scraper_cookies = self._scrape_videos_with_retry(task, cookies)
                    if not videos:
                        raise Exception("视频采集失败")
                    
                    # 使用采集时获取的cookies
                    if scraper_cookies:
                        cookies = scraper_cookies
                        print(f"🍪 使用采集时的cookies: {len(cookies)} 个")
                    
                    # 更新任务统计
                    task.total_videos = len(videos)
                    task.update_status(TaskStatus.RUNNING, TaskStep.DOWNLOADING)
                    
                    # 步骤2: 语音识别（带重试）
                    if task.enable_transcription:
                        videos = self._transcribe_videos_with_retry(task, videos, cookies)
                    
                    # 步骤3: 保存结果
                    result_file = self._save_results(task, videos)
                    if result_file:
                        task.set_result_file(result_file)
                        task.update_status(TaskStatus.COMPLETED)
                        print(f"✅ 任务 {task_id} 执行完成")
                        break  # 成功完成，退出重试循环
                    else:
                        raise Exception("结果保存失败")
                    
                except Exception as e:
                    retry_count += 1
                    error_msg = f"任务执行失败: {str(e)}"
                    print(f"❌ {error_msg}")
                    
                    if retry_count <= max_retries:
                        print(f"⏳ {max_retries - retry_count + 1} 次重试机会剩余，等待 {retry_count * 10} 秒后重试...")
                        time.sleep(retry_count * 10)  # 递增等待时间
                    else:
                        # 所有重试都失败了
                        task = AnalysisTask.query.get(task_id)
                        if task:
                            task.update_status(TaskStatus.FAILED, error_message=f"{error_msg} (已重试 {max_retries} 次)")
                        print(f"💥 任务 {task_id} 最终失败，已重试 {max_retries} 次")
                        break
                        
                finally:
                    # 清理运行中的任务并启动队列中的下一个任务
                    with self.task_lock:
                        if task_id in self.running_tasks:
                            del self.running_tasks[task_id]
                            print(f"🧹 任务 {task_id} 已清理，当前并发数: {len(self.running_tasks)}/{self.max_concurrent_tasks}")
                        
                        # 启动队列中的下一个任务
                        self._start_next_queued_task()
    
    def _start_next_queued_task(self):
        """启动队列中的下一个任务"""
        if self.task_queue and len(self.running_tasks) < self.max_concurrent_tasks:
            queued_task = self.task_queue.pop(0)
            task_id = queued_task["task_id"]
            app = queued_task["app"]
            cookies = queued_task["cookies"]
            queued_at = queued_task["queued_at"]
            
            wait_time = (datetime.now(timezone(timedelta(hours=8))) - queued_at).total_seconds()
            print(f"📤 从队列启动任务 {task_id} (等待了 {wait_time:.1f} 秒)")
            
            # 启动任务
            self._start_task_immediately(task_id, app, cookies)
    
    def get_queue_status(self) -> Dict:
        """获取队列状态"""
        with self.task_lock:
            return {
                "running_tasks": len(self.running_tasks),
                "queued_tasks": len(self.task_queue),
                "max_concurrent": self.max_concurrent_tasks,
                "running_task_ids": list(self.running_tasks.keys()),
                "queued_task_ids": [task["task_id"] for task in self.task_queue]
            }
    
    def _scrape_videos_with_retry(self, task: AnalysisTask, cookies=None) -> tuple[List[Dict], List[Dict]]:
        """带重试的视频采集"""
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                return self._scrape_videos(task, cookies)
            except Exception as e:
                if attempt < max_retries:
                    print(f"⚠️ 视频采集失败，第 {attempt + 1} 次重试: {e}")
                    time.sleep(5)  # 等待5秒后重试
                else:
                    print(f"❌ 视频采集最终失败: {e}")
                    raise
    
    def _transcribe_videos_with_retry(self, task: AnalysisTask, videos: List[Dict], cookies=None) -> List[Dict]:
        """带重试的视频转录"""
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                return self._transcribe_videos(task, videos, cookies)
            except Exception as e:
                if attempt < max_retries:
                    print(f"⚠️ 视频转录失败，第 {attempt + 1} 次重试: {e}")
                    time.sleep(5)  # 等待5秒后重试
                else:
                    print(f"❌ 视频转录最终失败: {e}")
                    raise

    def _scrape_videos(self, task: AnalysisTask, cookies=None) -> tuple[List[Dict], List[Dict]]:
        """采集视频，返回(videos, cookies)"""
        try:
            print(f"📹 开始采集视频: {task.target_url}")
            task.update_status(TaskStatus.RUNNING, TaskStep.SCRAPING)
            
            with DouyinVideoScraper(cookies=cookies) as scraper:
                if not scraper.ensure_login():
                    raise Exception("登录失败")
                
                scrape_result = scraper.scrape_videos(task.target_url, task.max_videos)
                
                # 处理新的返回格式
                if isinstance(scrape_result, dict):
                    videos = scrape_result.get('videos', [])
                    blogger_name = scrape_result.get('blogger_name', '')
                    # 更新任务名称
                    if blogger_name:
                        task.name = f"{blogger_name}的分析任务"
                        print(f"📝 更新任务名称为: {task.name}")
                    else:
                        # 如果无法获取博主名字，使用URL生成默认名称
                        from urllib.parse import urlparse
                        parsed_url = urlparse(task.target_url)
                        if 'user' in parsed_url.path:
                            user_id = parsed_url.path.split('/user/')[-1].split('?')[0]
                            task.name = f"博主_{user_id[:8]}...的分析任务"
                        else:
                            task.name = "未知博主的分析任务"
                        print(f"📝 设置默认任务名称: {task.name}")
                else:
                    # 兼容旧格式
                    videos = scrape_result
                    blogger_name = ''
                    # 设置默认任务名称
                    from urllib.parse import urlparse
                    parsed_url = urlparse(task.target_url)
                    if 'user' in parsed_url.path:
                        user_id = parsed_url.path.split('/user/')[-1].split('?')[0]
                        task.name = f"博主_{user_id[:8]}...的分析任务"
                    else:
                        task.name = "未知博主的分析任务"
                    print(f"📝 设置默认任务名称: {task.name}")
                
                # 获取cookies
                scraper_cookies = scraper.cookies or []
                
                # 实时保存视频数据到数据库
                for i, video_data in enumerate(videos):
                    try:
                        video = VideoData.create_video(
                            task_id=task.id,
                            video_id=video_data["video_id"],
                            title=video_data["title"],
                            url=video_data["url"]
                        )
                        db.session.add(video)
                        
                        # 每10个视频提交一次，或者最后一个视频时提交
                        if (i + 1) % 10 == 0 or i == len(videos) - 1:
                            db.session.commit()
                            print(f"💾 已保存 {i + 1}/{len(videos)} 个视频到数据库")
                            
                    except Exception as e:
                        print(f"⚠️ 保存视频 {video_data.get('video_id')} 到数据库失败: {e}")
                        db.session.rollback()
                        continue
                
                # 更新任务统计信息
                task.total_videos = len(videos)
                task.update_progress(0, 0, 0)  # 重置进度
                db.session.commit()
                
                print(f"✅ 视频采集完成: {len(videos)} 个新视频")
                return videos, scraper_cookies
                
        except Exception as e:
            print(f"❌ 视频采集失败: {e}")
            db.session.rollback()
            return [], []
    
    def _transcribe_videos(self, task: AnalysisTask, videos: List[Dict], cookies=None) -> List[Dict]:
        """转录音频"""
        try:
            print(f"🎤 开始语音识别: {len(videos)} 个视频")
            task.update_status(TaskStatus.RUNNING, TaskStep.TRANSCRIBING)
            
            transcriber = VideoTranscriber()
            processed_count = 0
            success_count = 0
            failed_count = 0
            
            for i, video_data in enumerate(videos):
                try:
                    video_id = video_data["video_id"]
                    video_url = video_data["url"]
                    
                    print(f"🎬 处理视频 {i+1}/{len(videos)}: {video_id}")
                    
                    # 获取数据库中的视频记录
                    video_record = VideoData.query.filter_by(
                        task_id=task.id,
                        video_id=video_id
                    ).first()
                    
                    if not video_record:
                        print(f"⚠️ 未找到视频记录: {video_id}")
                        failed_count += 1
                        processed_count += 1
                        task.update_progress(processed_count, success_count, failed_count)
                        continue
                    
                    # 检查是否可以重试
                    if video_record.processing_status == 'failed' and not video_record.can_retry():
                        print(f"⏭️ 视频 {video_id} 已达到最大重试次数，跳过")
                        failed_count += 1
                        processed_count += 1
                        task.update_progress(processed_count, success_count, failed_count)
                        continue
                    
                    # 转录音频
                    result = transcriber.process_video(
                        video_url, 
                        video_id, 
                        task.language,
                        cookies
                    )
                    
                    # 更新视频数据
                    video_data["transcript"] = result.get("transcript", "")
                    video_data["transcript_confidence"] = result.get("confidence", 0.0)
                    video_data["language_detected"] = result.get("language", task.language)
                    
                    # 实时更新数据库中的视频记录
                    try:
                        if result.get("success"):
                            video_record.set_transcription_result(
                                result["transcript"],
                                result.get("confidence"),
                                result.get("language")
                            )
                            # 设置音频文件信息
                            if result.get("video_file"):
                                video_record.set_audio_info(
                                    result["video_file"],
                                    result.get("video_file_size", 0)
                                )
                            success_count += 1
                            print(f"✅ 视频 {video_id} 处理成功")
                        else:
                            # 记录重试错误
                            error_msg = result.get("error", "转录失败")
                            video_record.add_retry_error(error_msg)
                            video_record.update_status("failed", error_msg)
                            failed_count += 1
                            print(f"❌ 视频 {video_id} 处理失败: {error_msg}")
                    except Exception as db_error:
                        print(f"⚠️ 更新数据库记录失败: {db_error}")
                        # 回滚数据库事务
                        db.session.rollback()
                        # 继续处理，不影响整体流程
                        if result.get("success"):
                            success_count += 1
                        else:
                            failed_count += 1
                    
                    processed_count += 1
                    
                    # 实时更新任务进度
                    task.update_progress(processed_count, success_count, failed_count)
                    
                    # 不立即清理音频文件，保留供用户下载
                    # 文件将在任务完成后统一清理或由用户手动清理
                    # if result.get("video_file"):
                    #     transcriber.cleanup_audio_file(result["video_file"])
                    
                except Exception as e:
                    print(f"⚠️ 视频 {video_data.get('video_id')} 处理异常: {e}")
                    
                    # 记录异常到数据库
                    try:
                        if 'video_record' in locals() and video_record:
                            video_record.add_retry_error(str(e))
                            video_record.update_status("failed", str(e))
                    except Exception as db_error:
                        print(f"⚠️ 记录异常到数据库失败: {db_error}")
                        db.session.rollback()
                    
                    failed_count += 1
                    processed_count += 1
                    task.update_progress(processed_count, success_count, failed_count)
                    continue
            
            print(f"✅ 语音识别完成: 成功 {success_count}, 失败 {failed_count}")
            return videos
            
        except Exception as e:
            print(f"❌ 语音识别失败: {e}")
            return videos
    
    def _perform_ai_analysis(self, task: AnalysisTask, videos: List[Dict]) -> Dict:
        """进行AI分析"""
        try:
            from .ai.deepseek_analyzer import analyze_blogger_with_deepseek
            
            # 获取博主名字
            blogger_name = task.name.replace('的分析任务', '') if task.name else '未知博主'
            
            # 准备视频数据
            videos_data = []
            for video in videos:
                videos_data.append({
                    'title': video.get('title', ''),
                    'transcript': video.get('transcript', ''),
                    'video_id': video.get('video_id', '')
                })
            
            # 调用DeepSeek分析
            analysis_result = analyze_blogger_with_deepseek(blogger_name, videos_data)
            
            # 保存分析结果到数据库
            task.set_analysis_report(analysis_result, 'completed')
            
            print(f"✅ AI分析完成")
            return analysis_result
            
        except Exception as e:
            print(f"❌ AI分析失败: {e}")
            # 设置失败状态
            error_result = {
                "strategic_positioning": "分析失败",
                "content_architecture": "分析失败",
                "language_rhetoric": "分析失败",
                "theoretical_foundation": "分析失败",
                "strategic_recommendations": "分析失败",
                "overall_summary": f"AI分析失败: {str(e)}",
                "analysis_status": "failed"
            }
            task.set_analysis_report(error_result, 'failed')
            return error_result
    
    def _save_results(self, task: AnalysisTask, videos: List[Dict]) -> Optional[str]:
        """保存结果"""
        try:
            print("💾 正在保存结果...")
            task.update_status(TaskStatus.RUNNING, TaskStep.FINALIZING)
            
            # 确保输出目录存在
            os.makedirs(self.config.OUTPUT_DIR, exist_ok=True)
            
            # 生成文件名
            timestamp = int(time.time())
            filename = f"douyin_analysis_{task.id}_{timestamp}.json"
            filepath = os.path.join(self.config.OUTPUT_DIR, filename)
            
            # 进行AI分析
            print("🤖 开始AI分析...")
            analysis_result = self._perform_ai_analysis(task, videos)
            
            # 准备结果数据
            result_data = {
                "task_info": {
                    "task_id": task.id,
                    "target_url": task.target_url,
                    "target_username": task.target_username,
                    "created_at": task.created_at.isoformat(),
                    "completed_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
                    "total_videos": len(videos),
                    "whisper_model": task.whisper_model,
                    "language": task.language
                },
                "videos": videos,
                "analysis_report": analysis_result
            }
            
            # 保存到文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 结果已保存: {filename}")
            return filename
            
        except Exception as e:
            print(f"❌ 保存结果失败: {e}")
            return None
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        try:
            with self.task_lock:
                if task_id in self.running_tasks:
                    # 清理运行中的任务
                    del self.running_tasks[task_id]
                    print(f"🛑 任务 {task_id} 已从运行队列中移除")
                    return True
                else:
                    print(f"⚠️ 任务 {task_id} 未在运行队列中")
                    return False
                    
        except Exception as e:
            print(f"❌ 取消任务失败: {e}")
            return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        try:
            task = AnalysisTask.query.get(task_id)
            if not task:
                return None
            
            return task.to_dict()
            
        except Exception as e:
            print(f"❌ 获取任务状态失败: {e}")
            return None
    
    def get_running_tasks(self) -> List[str]:
        """获取正在运行的任务ID列表"""
        with self.task_lock:
            return list(self.running_tasks.keys())


# 全局任务管理器实例
task_manager = TaskManager()


def start_analysis_task(task_id: str, app) -> bool:
    """启动分析任务的便捷函数"""
    return task_manager.start_analysis_task(task_id, app)


def cancel_analysis_task(task_id: str) -> bool:
    """取消分析任务的便捷函数"""
    return task_manager.cancel_task(task_id)
