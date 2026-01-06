"""Retry decorator for async functions"""
import asyncio
import logging
from typing import Callable, Type, Tuple
from functools import wraps


def async_retry(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    logger: logging.Logger = None
):
    """
    异步重试装饰器

    Args:
        max_attempts: 最大重试次数
        backoff_factor: 退避因子（每次重试等待时间翻倍）
        exceptions: 需要重试的异常类型
        logger: 日志记录器

    Example:
        @async_retry(max_attempts=3, backoff_factor=2.0)
        async def fetch_data():
            # 可能失败的操作
            pass
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e

                    if attempt < max_attempts - 1:
                        wait_time = backoff_factor ** attempt
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}"
                        )

            # 所有重试都失败，抛出最后一个异常
            raise last_exception

        return wrapper
    return decorator
