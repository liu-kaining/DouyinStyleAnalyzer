"""
重试工具类 - 提供通用的重试机制
"""

import time
import random
from typing import Callable, Any, Optional, Dict
from functools import wraps
from ..config import Config


class RetryConfig:
    """重试配置类"""
    
    def __init__(self, max_retries: int = 10, base_delay: float = 2.0, 
                 max_delay: float = 60.0, backoff_factor: float = 2.0,
                 jitter: bool = True):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter


class RetryManager:
    """重试管理器"""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
    
    def calculate_delay(self, attempt: int) -> float:
        """计算重试延迟时间"""
        # 指数退避算法
        delay = self.config.base_delay * (self.config.backoff_factor ** attempt)
        
        # 限制最大延迟时间
        delay = min(delay, self.config.max_delay)
        
        # 添加随机抖动，避免雷群效应
        if self.config.jitter:
            jitter = random.uniform(0.1, 0.3) * delay
            delay += jitter
        
        return delay
    
    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """判断是否应该重试"""
        if attempt >= self.config.max_retries:
            return False
        
        # 可以根据异常类型决定是否重试
        retryable_exceptions = (
            ConnectionError,
            TimeoutError,
            OSError,
            Exception  # 默认所有异常都重试
        )
        
        return isinstance(exception, retryable_exceptions)
    
    def retry(self, func: Callable, *args, **kwargs) -> Any:
        """执行带重试的函数"""
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if not self.should_retry(attempt, e):
                    break
                
                if attempt < self.config.max_retries:
                    delay = self.calculate_delay(attempt)
                    print(f"🔄 第 {attempt + 1} 次重试失败: {e}")
                    print(f"⏳ 等待 {delay:.1f} 秒后重试...")
                    time.sleep(delay)
                else:
                    print(f"❌ 达到最大重试次数 {self.config.max_retries}，放弃重试")
        
        # 如果所有重试都失败了，抛出最后一个异常
        raise last_exception


def retry_on_failure(max_retries: int = 10, base_delay: float = 2.0, 
                    max_delay: float = 60.0, backoff_factor: float = 2.0,
                    jitter: bool = True):
    """重试装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            config = RetryConfig(
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                backoff_factor=backoff_factor,
                jitter=jitter
            )
            retry_manager = RetryManager(config)
            return retry_manager.retry(func, *args, **kwargs)
        return wrapper
    return decorator


def retry_with_callback(callback: Callable[[int, Exception], None], 
                       max_retries: int = 10, base_delay: float = 2.0,
                       max_delay: float = 60.0, backoff_factor: float = 2.0):
    """带回调的重试装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            config = RetryConfig(
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                backoff_factor=backoff_factor
            )
            retry_manager = RetryManager(config)
            
            last_exception = None
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # 调用回调函数
                    try:
                        callback(attempt, e)
                    except Exception as callback_error:
                        print(f"⚠️ 重试回调函数执行失败: {callback_error}")
                    
                    if not retry_manager.should_retry(attempt, e):
                        break
                    
                    if attempt < config.max_retries:
                        delay = retry_manager.calculate_delay(attempt)
                        time.sleep(delay)
            
            raise last_exception
        return wrapper
    return decorator


# 全局重试管理器实例
default_retry_manager = RetryManager(RetryConfig(
    max_retries=Config().MAX_RETRY_COUNT,
    base_delay=Config().RETRY_DELAY_BASE,
    max_delay=Config().RETRY_DELAY_MAX,
    backoff_factor=Config().RETRY_BACKOFF_FACTOR
))
