"""
Global Progress Display - 全局进度条显示系统

在屏幕底部显示进度条，上方显示日志输出
"""

import sys
import logging
import threading
from typing import Optional
from datetime import datetime


class GlobalProgressDisplay:
    """
    全局进度条显示器

    在终端底部显示进度条，上方显示日志输出
    支持多线程安全的进度更新和日志输出
    """

    def __init__(self, enable: bool = True):
        """
        初始化全局进度显示器

        Args:
            enable: 是否启用进度条显示
        """
        self.enable = enable
        self.current_progress = 0.0
        self.current_message = ""
        self.lock = threading.Lock()
        self.last_log_line = ""

        # 进度条配置
        self.bar_length = 50
        self.show_percentage = True
        self.show_eta = True

        # 时间追踪
        self.start_time = None
        self.last_update_time = None

        # 终端配置
        self.terminal_width = self._get_terminal_width()

    def _get_terminal_width(self) -> int:
        """获取终端宽度"""
        try:
            import shutil
            return shutil.get_terminal_size().columns
        except:
            return 80  # 默认宽度

    def start(self):
        """启动进度显示"""
        if not self.enable:
            return

        self.start_time = datetime.now()
        self.last_update_time = self.start_time

        # 清空当前行
        self._clear_line()

    def update(self, progress: float, message: str = ""):
        """
        更新进度

        Args:
            progress: 进度百分比 (0-100)
            message: 进度消息
        """
        if not self.enable:
            return

        with self.lock:
            self.current_progress = min(100.0, max(0.0, progress))
            self.current_message = message
            self.last_update_time = datetime.now()

            # 重绘进度条
            self._redraw_progress_bar()

    def _redraw_progress_bar(self):
        """重绘进度条"""
        # 清空当前行
        self._clear_line()

        # 构建进度条
        progress_bar = self._build_progress_bar()

        # 输出进度条
        sys.stdout.write(progress_bar)
        sys.stdout.flush()

    def _build_progress_bar(self) -> str:
        """
        构建进度条字符串

        Returns:
            进度条字符串
        """
        # 计算填充长度
        filled_length = int(self.bar_length * self.current_progress / 100)

        # 构建进度条
        try:
            # 尝试使用 Unicode 字符
            bar = '█' * filled_length + '░' * (self.bar_length - filled_length)
        except UnicodeEncodeError:
            # 回退到 ASCII 字符
            bar = '#' * filled_length + '-' * (self.bar_length - filled_length)

        # 构建完整输出
        parts = [f"[{bar}]"]

        # 添加百分比
        if self.show_percentage:
            parts.append(f" {self.current_progress:.1f}%")

        # 添加消息
        if self.current_message:
            # 截断过长的消息
            max_message_length = self.terminal_width - len(''.join(parts)) - 20
            message = self.current_message
            if len(message) > max_message_length:
                message = message[:max_message_length-3] + "..."
            parts.append(f" - {message}")

        # 添加 ETA
        if self.show_eta and self.start_time:
            eta = self._calculate_eta()
            if eta is not None:
                parts.append(f" | ETA: {eta:.0f}s")

        return ''.join(parts)

    def _calculate_eta(self) -> Optional[float]:
        """
        计算预计剩余时间

        Returns:
            预计剩余时间（秒），如果无法计算则返回 None
        """
        if not self.start_time or self.current_progress <= 0:
            return None

        elapsed = (datetime.now() - self.start_time).total_seconds()

        # 避免除以零错误：如果时间太短（小于0.1秒），无法准确预估
        if elapsed < 0.1:
            return None

        # 计算平均速度
        speed = self.current_progress / elapsed  # percent per second

        if speed <= 0:
            return None

        # 计算剩余时间
        remaining_progress = 100 - self.current_progress
        eta = remaining_progress / speed

        return eta

    def _clear_line(self):
        """清空当前行"""
        sys.stdout.write('\r' + ' ' * self.terminal_width + '\r')
        sys.stdout.flush()

    def finish(self):
        """完成进度显示"""
        if not self.enable:
            return

        with self.lock:
            self.current_progress = 100.0
            self._redraw_progress_bar()
            sys.stdout.write('\n')
            sys.stdout.flush()

    def log(self, message: str, level: str = "INFO"):
        """
        输出日志消息（在进度条上方）

        Args:
            message: 日志消息
            level: 日志级别
        """
        if not self.enable:
            print(f"[{level}] {message}")
            return

        with self.lock:
            # 清空进度条
            self._clear_line()

            # 输出日志
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_line = f"{timestamp} - {level} - {message}"
            print(log_line)

            # 重绘进度条
            self._redraw_progress_bar()


class ProgressBarHandler(logging.Handler):
    """
    日志处理器，与全局进度条配合使用

    将日志输出到进度条上方，避免覆盖进度条
    """

    def __init__(self, progress_display: GlobalProgressDisplay):
        """
        初始化处理器

        Args:
            progress_display: 全局进度显示器实例
        """
        super().__init__()
        self.progress_display = progress_display

    def emit(self, record: logging.LogRecord):
        """
        输出日志记录

        Args:
            record: 日志记录
        """
        try:
            msg = self.format(record)
            self.progress_display.log(msg, record.levelname)
        except Exception:
            self.handleError(record)


# 全局单例
_global_progress_display: Optional[GlobalProgressDisplay] = None


def get_global_progress_display() -> GlobalProgressDisplay:
    """
    获取全局进度显示器单例

    Returns:
        全局进度显示器实例
    """
    global _global_progress_display

    if _global_progress_display is None:
        _global_progress_display = GlobalProgressDisplay()

    return _global_progress_display


def setup_global_progress_display(enable: bool = True) -> GlobalProgressDisplay:
    """
    设置全局进度显示器

    Args:
        enable: 是否启用进度条显示

    Returns:
        全局进度显示器实例
    """
    global _global_progress_display

    _global_progress_display = GlobalProgressDisplay(enable=enable)
    return _global_progress_display


def configure_logging_with_progress_bar(
    log_level: int = logging.INFO,
    log_file: Optional[str] = None
) -> GlobalProgressDisplay:
    """
    配置日志系统以配合进度条使用

    Args:
        log_level: 日志级别
        log_file: 日志文件路径（可选）

    Returns:
        全局进度显示器实例
    """
    # 获取或创建全局进度显示器
    progress_display = get_global_progress_display()

    # 获取根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 移除现有的控制台处理器
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler) and handler.stream in (sys.stdout, sys.stderr):
            root_logger.removeHandler(handler)

    # 添加进度条处理器（用于控制台输出）
    progress_handler = ProgressBarHandler(progress_display)
    progress_handler.setLevel(log_level)

    # 设置格式
    formatter = logging.Formatter(
        '%(name)s - %(levelname)s - %(message)s'
    )
    progress_handler.setFormatter(formatter)

    root_logger.addHandler(progress_handler)

    # 如果指定了日志文件，添加文件处理器
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    return progress_display
