"""
视频采集服务 - 使用 Selenium 自动化采集抖音视频
"""

import time
import re
import json
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from ..config import Config
from ..utils.validators import extract_user_id_from_url
from ..utils.retry import retry_on_failure, RetryManager, RetryConfig


class DouyinVideoScraper:
    """抖音视频采集器"""
    
    def __init__(self, cookies=None):
        self.driver = None
        self.wait = None
        self.config = Config()
        self.cookies = cookies  # 用户登录态cookies
        
        # 初始化重试管理器
        retry_config = RetryConfig(
            max_retries=self.config.MAX_RETRY_COUNT,
            base_delay=self.config.RETRY_DELAY_BASE,
            max_delay=self.config.RETRY_DELAY_MAX,
            backoff_factor=self.config.RETRY_BACKOFF_FACTOR
        )
        self.retry_manager = RetryManager(retry_config)
    
    def _setup_driver(self):
        """设置浏览器驱动"""
        options = Options()
        
        # 反检测配置
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--start-maximized")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--remote-debugging-port=9222")
        
        # 用户数据目录
        options.add_argument(f"--user-data-dir={self.config.CHROME_USER_DATA_DIR}")
        
        # 设置用户代理
        options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
            
            # 执行反检测脚本
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # 设置等待
            self.wait = WebDriverWait(self.driver, 10)
            
            return True
            
        except Exception as e:
            print(f"❌ 浏览器驱动设置失败: {e}")
            return False
    
    def ensure_login(self) -> bool:
        """确保用户已登录"""
        try:
            # 始终进行真实的登录检查
            
            print("🌐 正在打开抖音首页...")
            self.driver.get("https://www.douyin.com/")
            time.sleep(3)
            
            # 如果有cookies，先设置cookies
            if self.cookies:
                print("🍪 正在设置用户登录态...")
                try:
                    for cookie in self.cookies:
                        self.driver.add_cookie(cookie)
                    print("✅ 登录态设置成功")
                    # 刷新页面使cookies生效
                    self.driver.refresh()
                    time.sleep(3)
                except Exception as e:
                    print(f"⚠️ 设置cookies失败: {e}")
            else:
                # 尝试从当前浏览器会话中获取cookies
                print("🍪 尝试从浏览器会话中获取登录状态...")
                try:
                    # 获取当前页面的所有cookies
                    current_cookies = self.driver.get_cookies()
                    if current_cookies:
                        print(f"✅ 获取到 {len(current_cookies)} 个cookies")
                        # 保存cookies供后续使用
                        self.cookies = current_cookies
                    else:
                        print("⚠️ 未找到有效的cookies")
                except Exception as e:
                    print(f"⚠️ 获取cookies失败: {e}")
            
            # 检查是否已登录 - 使用更准确的检测方法
            try:
                print("🔍 正在检测登录状态...")
                
                # 方法1: 检查页面中是否有登录相关的元素
                login_elements = [
                    "//button[contains(text(), '登录')]",
                    "//a[contains(text(), '登录')]",
                    "//span[contains(text(), '登录')]"
                ]
                
                has_login_button = False
                for selector in login_elements:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        for element in elements:
                            if element.is_displayed() and "登录" in element.text:
                                has_login_button = True
                                break
                        if has_login_button:
                            break
                    except:
                        continue
                
                # 方法2: 检查是否有用户相关的元素
                user_elements = [
                    "//div[contains(@class, 'avatar')]",
                    "//img[contains(@class, 'avatar')]",
                    "//div[contains(@class, 'user')]",
                    "//span[contains(@class, 'username')]"
                ]
                
                has_user_info = False
                for selector in user_elements:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        for element in elements:
                            if element.is_displayed():
                                has_user_info = True
                                break
                        if has_user_info:
                            break
                    except:
                        continue
                
                # 方法3: 检查cookies中是否有登录相关的cookie
                has_login_cookies = False
                login_cookie_names = []
                try:
                    cookies = self.driver.get_cookies()
                    for cookie in cookies:
                        if cookie['name'] in ['sessionid', 'uid', 'user_id', 'passport_csrf_token', 'ttwid', 'msToken']:
                            has_login_cookies = True
                            login_cookie_names.append(cookie['name'])
                except:
                    pass
                
                print(f"🔍 登录cookies检查: 找到 {len(login_cookie_names)} 个登录cookies: {login_cookie_names}")
                
                # 综合判断登录状态
                if has_login_cookies and not has_login_button:
                    print("✅ 检测到登录状态（基于cookies）")
                    return True
                elif has_user_info and not has_login_button:
                    print("✅ 检测到登录状态（基于用户信息）")
                    return True
                elif has_login_button:
                    print("🔐 检测到登录按钮，等待用户扫码登录...")
                    print("📱 请在浏览器中完成扫码登录，系统将等待60秒...")
                    
                    # 等待用户登录，最多等待60秒
                    for i in range(60):
                        time.sleep(1)
                        print(f"⏳ 等待登录中... ({i+1}/60)")
                        
                        # 每5秒检查一次登录状态
                        if (i + 1) % 5 == 0:
                            try:
                                # 重新检查登录状态
                                current_cookies = self.driver.get_cookies()
                                has_login_cookies_now = False
                                login_cookie_names_now = []
                                for cookie in current_cookies:
                                    if cookie['name'] in ['sessionid', 'uid', 'user_id', 'passport_csrf_token', 'ttwid', 'msToken']:
                                        has_login_cookies_now = True
                                        login_cookie_names_now.append(cookie['name'])
                                
                                print(f"🔍 当前登录cookies: {login_cookie_names_now}")
                                
                                # 检查是否还有登录按钮
                                has_login_button_now = False
                                for selector in login_elements:
                                    try:
                                        elements = self.driver.find_elements(By.XPATH, selector)
                                        for element in elements:
                                            if element.is_displayed() and "登录" in element.text:
                                                has_login_button_now = True
                                                break
                                        if has_login_button_now:
                                            break
                                    except:
                                        continue
                                
                                # 如果登录成功
                                if has_login_cookies_now and not has_login_button_now:
                                    print("✅ 登录成功！")
                                    # 保存最新的cookies
                                    self.cookies = current_cookies
                                    print(f"🍪 保存了 {len(current_cookies)} 个登录cookies")
                                    return True
                                    
                            except Exception as e:
                                print(f"⚠️ 检查登录状态时出错: {e}")
                                continue
                    
                    print("⏰ 等待超时，登录失败")
                    return False
                else:
                    # 如果无法确定，尝试访问需要登录的页面
                    print("🔍 无法确定登录状态，尝试访问用户页面...")
                    try:
                        self.driver.get("https://www.douyin.com/user/self")
                        time.sleep(3)
                        
                        # 检查是否跳转到登录页面
                        if "login" in self.driver.current_url or "登录" in self.driver.page_source:
                            print("❌ 需要登录，但无法自动登录")
                            print("💡 建议：请先在浏览器中手动登录抖音，然后重新运行任务")
                            return False
                        else:
                            print("✅ 登录状态验证成功")
                            return True
                    except Exception as e:
                        print(f"⚠️ 登录状态验证失败: {e}")
                        return False
                    
            except Exception as e:
                print(f"⚠️ 登录状态检查失败: {e}")
                return False
                
        except Exception as e:
            print(f"❌ 登录检查失败: {e}")
            return False
    
    def _check_login_status(self) -> bool:
        """检查登录状态"""
        try:
            # 尝试访问需要登录的页面
            self.driver.get("https://www.douyin.com/user/self")
            time.sleep(3)
            
            # 检查是否跳转到登录页面
            if "login" in self.driver.current_url or "登录" in self.driver.page_source:
                print("❌ 登录失败，请重试")
                return False
            else:
                print("✅ 登录成功")
                return True
                
        except Exception as e:
            print(f"❌ 登录状态验证失败: {e}")
            return False
    
    def scrape_videos(self, user_url: str, max_videos: int = 50) -> List[Dict]:
        """采集用户视频列表"""
        def _scrape_videos_internal():
            print(f"📹 开始采集视频: {user_url}")
            
            # 获取该博主已分析的视频ID列表
            from ..models.video import VideoData
            analyzed_video_ids = set(VideoData.get_analyzed_video_ids_by_blogger(user_url))
            print(f"📋 该博主已分析 {len(analyzed_video_ids)} 个视频，将跳过重复分析")
            
            # 访问用户主页
            self.driver.get(user_url)
            time.sleep(5)
            
            # 等待页面加载
            try:
                self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            except TimeoutException:
                print("⚠️ 页面加载超时")
            
            videos = []
            skipped_count = 0
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_count = 0
            
            print(f"🔄 开始滚动采集，最多滚动 {self.config.MAX_SCROLL_COUNT} 次...")
            
            while scroll_count < self.config.MAX_SCROLL_COUNT and len(videos) < max_videos:
                # 滚动到页面底部
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
                
                # 查找视频元素
                video_elements = self._find_video_elements()
                
                for element in video_elements:
                    try:
                        video_data = self._extract_video_data(element)
                        if video_data and not self._is_duplicate(video_data, videos):
                            # 检查是否已经分析过这个视频（按博主分组去重）
                            if video_data['video_id'] in analyzed_video_ids:
                                print(f"⏭️ 跳过已分析的视频: {video_data['video_id']}")
                                skipped_count += 1
                                continue
                            
                            videos.append(video_data)
                            print(f"✅ 采集到新视频: {video_data['title'][:50]}...")
                            
                            if len(videos) >= max_videos:
                                break
                                
                    except Exception as e:
                        print(f"⚠️ 提取视频数据失败: {e}")
                        continue
                
                # 检查是否到达页面底部
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    print("📄 已到达页面底部")
                    break
                
                last_height = new_height
                scroll_count += 1
                
                print(f"📊 已采集 {len(videos)} 个新视频，跳过 {skipped_count} 个已分析视频，滚动次数: {scroll_count}")
            
            print(f"🎉 采集完成，共获得 {len(videos)} 个新视频，跳过 {skipped_count} 个已分析视频")
            
            # 在返回前获取最新的cookies
            try:
                current_cookies = self.driver.get_cookies()
                if current_cookies:
                    self.cookies = current_cookies
                    print(f"🍪 保存了 {len(current_cookies)} 个cookies供下载使用")
                    
                    # 保存cookies到文件供yt-dlp使用
                    self._save_cookies_to_file(current_cookies)
            except Exception as e:
                print(f"⚠️ 获取cookies失败: {e}")
            
            return videos
        
        # 使用重试机制执行采集
        try:
            return self.retry_manager.retry(_scrape_videos_internal)
        except Exception as e:
            print(f"❌ 视频采集失败（已重试 {self.config.MAX_RETRY_COUNT} 次）: {e}")
            return []
    
    def _find_video_elements(self) -> List:
        """查找视频元素"""
        # 基于实际HTML结构更新选择器
        selectors = [
            "div[data-e2e='user-post-item']",  # 主要选择器
            "div[data-e2e='user-post-item-list'] > div",  # 备用选择器
            "div.DivItemContainer[data-e2e='user-post-item']",  # 更具体的选择器
            "a[href*='/video/']",  # 直接选择视频链接
            "div[class*='DivItemContainer']",  # 基于class的选择器
            # 备用选择器
            ".video-item",
            ".user-post-item",
            "div[class*='video']",
            "div[class*='post']",
            "div[class*='item']"
        ]
        
        elements = []
        print(f"🔍 正在查找视频元素...")
        
        for i, selector in enumerate(selectors):
            try:
                found_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                print(f"   选择器 {i+1}: '{selector}' -> 找到 {len(found_elements)} 个元素")
                if found_elements:
                    elements.extend(found_elements)
                    print(f"✅ 使用选择器: '{selector}' 找到 {len(found_elements)} 个元素")
                    break
            except Exception as e:
                print(f"   选择器 {i+1}: '{selector}' -> 错误: {e}")
                continue
        
        if not elements:
            print("⚠️ 未找到任何视频元素，尝试通用选择器...")
            # 尝试更通用的选择器
            generic_selectors = [
                "div[class*='Div']",
                "div[class*='Item']", 
                "div[class*='Card']",
                "a[href*='video']",
                "div[data-e2e]"
            ]
            
            for selector in generic_selectors:
                try:
                    found_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    print(f"   通用选择器 '{selector}' -> 找到 {len(found_elements)} 个元素")
                    if found_elements:
                        elements.extend(found_elements[:10])  # 限制数量避免太多
                except Exception:
                    continue
        
        print(f"📊 总共找到 {len(elements)} 个潜在视频元素")
        return elements
    
    def _extract_video_data(self, element) -> Optional[Dict]:
        """从元素中提取视频数据"""
        try:
            print(f"🔍 正在提取视频数据...")
            
            # 如果元素本身就是链接，直接使用
            if element.tag_name == 'a':
                href = element.get_attribute("href")
                if href and "/video/" in href:
                    video_url = href
                    print(f"✅ 元素本身就是视频链接: {video_url}")
                else:
                    video_url = None
            else:
                # 查找链接 - 基于实际HTML结构优化选择器
                link_selectors = [
                    "a[href*='/video/']",  # 主要选择器
                    "a[target='_blank'][rel*='nofollow']",  # 基于HTML中的属性
                    "a[href*='aweme_id']", 
                    "a[href*='video']",
                    "a"
                ]
                
                video_url = None
                for i, selector in enumerate(link_selectors):
                    try:
                        link_elements = element.find_elements(By.CSS_SELECTOR, selector)
                        print(f"   链接选择器 {i+1}: '{selector}' -> 找到 {len(link_elements)} 个链接")
                        
                        for link_element in link_elements:
                            href = link_element.get_attribute("href")
                            print(f"     链接: {href}")
                            if href and ("/video/" in href or "aweme_id" in href or "video" in href):
                                video_url = href
                                print(f"✅ 找到视频链接: {video_url}")
                                break
                        
                        if video_url:
                            break
                            
                    except Exception as e:
                        print(f"   链接选择器 {i+1} 错误: {e}")
                        continue
            
            if not video_url:
                print("❌ 未找到视频链接")
                return None
            
            # 提取视频ID
            video_id = self._extract_video_id(video_url)
            if not video_id:
                print("❌ 无法提取视频ID")
                return None
            
            print(f"✅ 视频ID: {video_id}")
            
            # 查找标题 - 基于实际HTML结构优化选择器
            title_selectors = [
                "span.SpanTextContainer[title]",  # 基于HTML中的实际结构
                "span[title]",  # 通用title属性
                "div[data-e2e='video-desc']",
                ".video-desc",
                ".video-title",
                "div[class*='desc']",
                "div[class*='title']",
                "span",
                "div"
            ]
            
            title = ""
            for i, selector in enumerate(title_selectors):
                try:
                    title_elements = element.find_elements(By.CSS_SELECTOR, selector)
                    print(f"   标题选择器 {i+1}: '{selector}' -> 找到 {len(title_elements)} 个元素")
                    
                    for title_element in title_elements:
                        text = title_element.text.strip()
                        title_attr = title_element.get_attribute("title").strip() if title_element.get_attribute("title") else ""
                        
                        # 优先使用title属性，然后是文本内容
                        if title_attr and len(title_attr) > 5:
                            title = title_attr
                            print(f"✅ 找到标题(属性): {title[:50]}...")
                            break
                        elif text and len(text) > 5:  # 标题应该有一定长度
                            title = text
                            print(f"✅ 找到标题: {title[:50]}...")
                            break
                    
                    if title:
                        break
                        
                except Exception as e:
                    print(f"   标题选择器 {i+1} 错误: {e}")
                    continue
            
            if not title:
                title = f"视频 {video_id}"
                print(f"⚠️ 使用默认标题: {title}")
            
            result = {
                "video_id": video_id,
                "title": title,
                "url": video_url,
                "transcript": "",
                "duration": None
            }
            
            print(f"✅ 成功提取视频数据: {result}")
            return result
            
        except Exception as e:
            print(f"❌ 提取视频数据失败: {e}")
            return None
    
    def _extract_video_id(self, url: str) -> Optional[str]:
        """从URL中提取视频ID"""
        try:
            # 匹配视频ID的正则表达式 - 基于实际URL格式
            patterns = [
                r'/video/(\d+)',  # /video/7382012345678901234
                r'video_id=(\d+)',
                r'aweme_id=(\d+)',
                r'(\d{19})',  # 19位数字的抖音视频ID
                r'(\d{18})',  # 18位数字的抖音视频ID
                r'(\d{17})',  # 17位数字的抖音视频ID
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    video_id = match.group(1)
                    print(f"✅ 使用模式 '{pattern}' 提取到视频ID: {video_id}")
                    return video_id
            
            print(f"❌ 无法从URL中提取视频ID: {url}")
            return None
            
        except Exception as e:
            print(f"❌ 提取视频ID时出错: {e}")
            return None
    
    def _is_duplicate(self, video_data: Dict, existing_videos: List[Dict]) -> bool:
        """检查视频是否重复"""
        video_id = video_data.get("video_id")
        if not video_id:
            return True
        
        for existing in existing_videos:
            if existing.get("video_id") == video_id:
                return True
        
        return False
    
    def _get_mock_videos(self, max_videos: int) -> List[Dict]:
        """获取演示视频数据（用于测试）"""
        # 使用一些公开可访问的视频URL进行演示
        demo_videos = [
            {
                "video_id": "demo_video_1",
                "title": "演示视频 1 - 公开可访问的测试视频",
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll - 经典测试视频
                "transcript": "",
                "duration": None
            },
            {
                "video_id": "demo_video_2", 
                "title": "演示视频 2 - 另一个测试视频",
                "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",  # 另一个公开视频
                "transcript": "",
                "duration": None
            }
        ]
        
        # 返回指定数量的视频
        return demo_videos[:min(max_videos, len(demo_videos))]
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            try:
                self.driver.quit()
                print("🔒 浏览器已关闭")
            except Exception as e:
                print(f"⚠️ 关闭浏览器失败: {e}")
    
    def __enter__(self):
        """上下文管理器入口"""
        if self._setup_driver():
            return self
        else:
            raise Exception("浏览器驱动设置失败")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
    
    def _save_cookies_to_file(self, cookies):
        """保存cookies到文件供yt-dlp使用"""
        try:
            import os
            cookie_file = os.path.join(os.getcwd(), 'douyin_cookies.txt')
            
            with open(cookie_file, 'w', encoding='utf-8') as f:
                f.write("# Netscape HTTP Cookie File\n")
                f.write("# This file is generated by DouyinStyleAnalyzer. Do not edit.\n\n")
                
                for cookie in cookies:
                    if isinstance(cookie, dict) and 'name' in cookie and 'value' in cookie:
                        # Netscape格式: domain, domain_specified, path, secure, expires, name, value
                        domain = cookie.get('domain', '.douyin.com')
                        path = cookie.get('path', '/')
                        secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
                        expires = str(cookie.get('expiry', 0))
                        name = cookie['name']
                        value = cookie['value']
                        
                        # 修复domain格式 - 确保以点开头
                        if not domain.startswith('.'):
                            domain = '.' + domain
                        
                        # 确保domain_specified与domain格式匹配
                        domain_specified = 'TRUE' if domain.startswith('.') else 'FALSE'
                        
                        line = f"{domain}\t{domain_specified}\t{path}\t{secure}\t{expires}\t{name}\t{value}\n"
                        f.write(line)
            
            print(f"💾 已保存cookies到文件: {cookie_file}")
            
        except Exception as e:
            print(f"⚠️ 保存cookies文件失败: {e}")


def scrape_douyin_videos(user_url: str, max_videos: int = 50) -> List[Dict]:
    """采集抖音视频的便捷函数"""
    with DouyinVideoScraper() as scraper:
        if scraper.ensure_login():
            return scraper.scrape_videos(user_url, max_videos)
        else:
            print("❌ 登录失败，无法采集视频")
            return []
