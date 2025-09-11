"""
任务管理服务 - 管理分析任务的执行和状态
"""

import os
import json
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional
from ..models import AnalysisTask, VideoData, TaskStatus, TaskStep
from .. import db
from .scraper import DouyinVideoScraper
from .transcriber import VideoTranscriber
from ..config import Config


class TaskManager:
    """任务管理器 - 简化版本，专注于任务调度"""
    
    def __init__(self):
        self.config = Config()
        self.running_tasks = {}  # 存储正在运行的任务
        self.task_lock = threading.Lock()
    
    def start_analysis_task(self, task_id: str, app, cookies=None) -> bool:
        """启动分析任务"""
        try:
            with self.task_lock:
                if task_id in self.running_tasks:
                    print(f"⚠️ 任务 {task_id} 已在运行")
                    return False
                
                # 标记任务为运行中
                self.running_tasks[task_id] = {
                    "thread": None,
                    "start_time": datetime.utcnow(),
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
                
                print(f"🚀 任务 {task_id} 已启动")
                return True
                
        except Exception as e:
            print(f"❌ 启动任务失败: {e}")
            return False
    
    def _execute_task_with_app(self, task_id: str, app, cookies=None):
        """在Flask应用上下文中执行任务"""
        with app.app_context():
            try:
                task = AnalysisTask.query.get(task_id)
                if not task:
                    print(f"❌ 任务 {task_id} 不存在")
                    return
                
                print(f"🎯 开始执行任务: {task_id}")
                
                # 更新任务状态为运行中
                task.update_status(TaskStatus.RUNNING, TaskStep.INITIALIZING)
                
                # 步骤1: 视频采集
                videos, scraper_cookies = self._scrape_videos(task, cookies)
                if not videos:
                    task.update_status(TaskStatus.FAILED, error_message="视频采集失败")
                    return
                
                # 使用采集时获取的cookies
                if scraper_cookies:
                    cookies = scraper_cookies
                    print(f"🍪 使用采集时的cookies: {len(cookies)} 个")
                
                # 更新任务统计
                task.total_videos = len(videos)
                task.update_status(TaskStatus.RUNNING, TaskStep.DOWNLOADING)
                
                # 步骤2: 语音识别
                if task.enable_transcription:
                    videos = self._transcribe_videos(task, videos, cookies)
                
                # 步骤3: 保存结果
                result_file = self._save_results(task, videos)
                if result_file:
                    task.set_result_file(result_file)
                    task.update_status(TaskStatus.COMPLETED)
                    print(f"✅ 任务 {task_id} 执行完成")
                else:
                    task.update_status(TaskStatus.FAILED, error_message="结果保存失败")
                
            except Exception as e:
                print(f"❌ 任务执行失败: {e}")
                task = AnalysisTask.query.get(task_id)
                if task:
                    task.update_status(TaskStatus.FAILED, error_message=str(e))
            finally:
                # 清理运行中的任务
                with self.task_lock:
                    if task_id in self.running_tasks:
                        del self.running_tasks[task_id]
    
    def _scrape_videos(self, task: AnalysisTask, cookies=None) -> tuple[List[Dict], List[Dict]]:
        """采集视频，返回(videos, cookies)"""
        try:
            print(f"📹 开始采集视频: {task.target_url}")
            task.update_status(TaskStatus.RUNNING, TaskStep.SCRAPING)
            
            with DouyinVideoScraper(cookies=cookies) as scraper:
                if not scraper.ensure_login():
                    raise Exception("登录失败")
                
                videos = scraper.scrape_videos(task.target_url, task.max_videos)
                
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
                
                print(f"✅ 视频采集完成: {len(videos)} 个视频")
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
            
            # 准备结果数据
            result_data = {
                "task_info": {
                    "task_id": task.id,
                    "target_url": task.target_url,
                    "target_username": task.target_username,
                    "created_at": task.created_at.isoformat(),
                    "completed_at": datetime.utcnow().isoformat(),
                    "total_videos": len(videos),
                    "whisper_model": task.whisper_model,
                    "language": task.language
                },
                "videos": videos
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
