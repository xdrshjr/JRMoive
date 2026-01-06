"""
Progress Monitor - 进度监控器
"""

from typing import Callable, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import logging


@dataclass
class ProgressInfo:
    """进度信息"""
    percent: float
    message: str
    timestamp: datetime
    eta: Optional[float] = None  # 预计剩余时间（秒）
    current_step: Optional[int] = None
    total_steps: Optional[int] = None

    def to_dict(self):
        """转换为字典"""
        return {
            'percent': self.percent,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'eta': self.eta,
            'current_step': self.current_step,
            'total_steps': self.total_steps
        }

    def __str__(self):
        """字符串表示"""
        eta_str = f", ETA: {self.eta:.1f}s" if self.eta else ""
        step_str = f" [{self.current_step}/{self.total_steps}]" if self.current_step and self.total_steps else ""
        return f"{self.percent:.1f}%{step_str} - {self.message}{eta_str}"


class ProgressMonitor:
    """进度监控器"""

    def __init__(self, total_steps: int = 100):
        """
        初始化进度监控器

        Args:
            total_steps: 总步骤数
        """
        self.total_steps = total_steps
        self.current_step = 0
        self.start_time = datetime.now()
        self.callbacks: List[Callable] = []
        self.history: List[ProgressInfo] = []
        self.logger = logging.getLogger(__name__)

        # 进度历史保留最大条数
        self.max_history = 100

    def register_callback(self, callback: Callable):
        """
        注册进度回调

        Args:
            callback: 回调函数，接收ProgressInfo参数
        """
        self.callbacks.append(callback)
        self.logger.info(f"Progress callback registered: {callback.__name__}")

    def unregister_callback(self, callback: Callable):
        """
        取消注册回调

        Args:
            callback: 回调函数
        """
        if callback in self.callbacks:
            self.callbacks.remove(callback)
            self.logger.info(f"Progress callback unregistered: {callback.__name__}")

    async def update(
        self,
        step: int,
        message: str,
        force_notify: bool = False
    ):
        """
        更新进度

        Args:
            step: 当前步骤
            message: 进度消息
            force_notify: 强制通知所有回调（即使进度未变化）
        """
        # 更新当前步骤
        old_step = self.current_step
        self.current_step = step

        # 计算百分比
        percent = (step / self.total_steps) * 100

        # 计算ETA
        eta = self._calculate_eta()

        # 创建进度信息
        progress_info = ProgressInfo(
            percent=percent,
            message=message,
            timestamp=datetime.now(),
            eta=eta,
            current_step=step,
            total_steps=self.total_steps
        )

        # 添加到历史记录
        self._add_to_history(progress_info)

        # 只在步骤变化或强制通知时触发回调
        if old_step != step or force_notify:
            await self._trigger_callbacks(progress_info)

    async def update_percent(
        self,
        percent: float,
        message: str,
        force_notify: bool = False
    ):
        """
        直接使用百分比更新进度

        Args:
            percent: 进度百分比（0-100）
            message: 进度消息
            force_notify: 强制通知所有回调
        """
        # 将百分比转换为步骤
        step = int((percent / 100) * self.total_steps)
        await self.update(step, message, force_notify)

    def _calculate_eta(self) -> Optional[float]:
        """
        计算预计剩余时间

        Returns:
            预计剩余时间（秒），如果无法计算则返回None
        """
        if self.current_step == 0:
            return None

        # 计算已用时间
        elapsed = (datetime.now() - self.start_time).total_seconds()

        # 计算平均每步耗时
        time_per_step = elapsed / self.current_step

        # 计算剩余时间
        remaining_steps = self.total_steps - self.current_step
        eta = time_per_step * remaining_steps

        return eta

    def _add_to_history(self, progress_info: ProgressInfo):
        """
        添加到历史记录

        Args:
            progress_info: 进度信息
        """
        self.history.append(progress_info)

        # 限制历史记录数量
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

    async def _trigger_callbacks(self, progress_info: ProgressInfo):
        """
        触发所有回调

        Args:
            progress_info: 进度信息
        """
        for callback in self.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(progress_info)
                else:
                    callback(progress_info)
            except Exception as e:
                self.logger.error(f"Error in progress callback: {e}")

    def get_current_progress(self) -> Optional[ProgressInfo]:
        """
        获取当前进度

        Returns:
            当前进度信息，如果没有则返回None
        """
        if self.history:
            return self.history[-1]
        return None

    def get_history(self, limit: Optional[int] = None) -> List[ProgressInfo]:
        """
        获取进度历史

        Args:
            limit: 返回的最大条数

        Returns:
            进度历史列表
        """
        if limit:
            return self.history[-limit:]
        return self.history.copy()

    def reset(self):
        """重置进度监控器"""
        self.current_step = 0
        self.start_time = datetime.now()
        self.history.clear()
        self.logger.info("Progress monitor reset")

    def get_elapsed_time(self) -> float:
        """
        获取已用时间

        Returns:
            已用时间（秒）
        """
        return (datetime.now() - self.start_time).total_seconds()

    def get_average_speed(self) -> float:
        """
        获取平均处理速度

        Returns:
            平均每步耗时（秒/步）
        """
        if self.current_step == 0:
            return 0.0

        elapsed = self.get_elapsed_time()
        return elapsed / self.current_step

    def is_completed(self) -> bool:
        """
        检查是否完成

        Returns:
            是否完成
        """
        return self.current_step >= self.total_steps

    def get_completion_percentage(self) -> float:
        """
        获取完成百分比

        Returns:
            完成百分比（0-100）
        """
        return (self.current_step / self.total_steps) * 100


class ConsoleProgressMonitor(ProgressMonitor):
    """控制台进度监控器（自动打印到控制台）"""

    def __init__(self, total_steps: int = 100, show_bar: bool = True):
        """
        初始化控制台进度监控器

        Args:
            total_steps: 总步骤数
            show_bar: 是否显示进度条
        """
        super().__init__(total_steps)
        self.show_bar = show_bar

        # 自动注册控制台打印回调
        self.register_callback(self._console_callback)

    def _console_callback(self, progress_info: ProgressInfo):
        """
        控制台回调函数

        Args:
            progress_info: 进度信息
        """
        if self.show_bar:
            # 显示进度条
            bar_length = 40
            filled_length = int(bar_length * progress_info.percent / 100)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)

            # 构建输出
            eta_str = f" | ETA: {progress_info.eta:.1f}s" if progress_info.eta else ""
            output = f"\r[{bar}] {progress_info.percent:.1f}% - {progress_info.message}{eta_str}"

            # 打印（不换行）
            print(output, end='', flush=True)

            # 如果完成，换行
            if progress_info.percent >= 100:
                print()
        else:
            # 简单打印
            print(f"{progress_info.percent:.1f}% - {progress_info.message}")


class FileProgressMonitor(ProgressMonitor):
    """文件进度监控器（记录到文件）"""

    def __init__(self, total_steps: int = 100, log_file: str = "progress.log"):
        """
        初始化文件进度监控器

        Args:
            total_steps: 总步骤数
            log_file: 日志文件路径
        """
        super().__init__(total_steps)
        self.log_file = log_file

        # 自动注册文件写入回调
        self.register_callback(self._file_callback)

    def _file_callback(self, progress_info: ProgressInfo):
        """
        文件回调函数

        Args:
            progress_info: 进度信息
        """
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"{progress_info}\n")
        except Exception as e:
            self.logger.error(f"Failed to write progress to file: {e}")
