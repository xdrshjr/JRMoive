"""Concurrency control utilities"""
import asyncio
import time
from typing import Callable, List, Any, Optional
from dataclasses import dataclass
import logging


class ConcurrencyLimiter:
    """并发限制器 - 控制同时执行的任务数量"""

    def __init__(self, max_concurrent: int = 5):
        """
        初始化并发限制器

        Args:
            max_concurrent: 最大并发数
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.logger = logging.getLogger(__name__)

    async def run(self, func: Callable, *args, **kwargs) -> Any:
        """
        在并发限制下执行单个任务

        Args:
            func: 异步函数
            *args, **kwargs: 函数参数

        Returns:
            函数执行结果
        """
        async with self.semaphore:
            return await func(*args, **kwargs)

    async def run_batch(
        self,
        func: Callable,
        items: List[Any],
        show_progress: bool = False
    ) -> List[Any]:
        """
        批量执行任务（带并发控制）

        Args:
            func: 异步函数
            items: 要处理的项目列表
            show_progress: 是否显示进度

        Returns:
            结果列表
        """
        total = len(items)
        completed = 0

        async def run_with_progress(item):
            nonlocal completed
            result = await self.run(func, item)
            completed += 1

            if show_progress:
                self.logger.info(f"Progress: {completed}/{total} ({completed/total*100:.1f}%)")

            return result

        tasks = [run_with_progress(item) for item in items]
        return await asyncio.gather(*tasks)


class RateLimiter:
    """速率限制器 - 控制请求速率"""

    def __init__(self, max_requests: int = 10, time_window: float = 1.0):
        """
        初始化速率限制器

        Args:
            max_requests: 时间窗口内的最大请求数
            time_window: 时间窗口（秒）
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self.lock = asyncio.Lock()
        self.logger = logging.getLogger(__name__)

    async def acquire(self):
        """获取请求许可（如果超过速率限制会等待）"""
        async with self.lock:
            now = time.time()

            # 清理过期的请求记录
            self.requests = [req_time for req_time in self.requests
                           if now - req_time < self.time_window]

            # 如果达到速率限制，计算需要等待的时间
            if len(self.requests) >= self.max_requests:
                oldest_request = min(self.requests)
                wait_time = self.time_window - (now - oldest_request)

                if wait_time > 0:
                    self.logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)

                    # 等待后重新清理
                    now = time.time()
                    self.requests = [req_time for req_time in self.requests
                                   if now - req_time < self.time_window]

            # 记录本次请求
            self.requests.append(now)

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@dataclass
class TaskStats:
    """任务统计信息"""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    @property
    def duration(self) -> Optional[float]:
        """总耗时"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_tasks == 0:
            return 0.0
        return self.completed_tasks / self.total_tasks

    def __str__(self):
        return (
            f"TaskStats(total={self.total_tasks}, "
            f"completed={self.completed_tasks}, "
            f"failed={self.failed_tasks}, "
            f"success_rate={self.success_rate:.2%}, "
            f"duration={self.duration:.2f}s)"
        )
