"""
Task Queue - 异步任务队列管理器
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import uuid


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """任务数据类"""
    task_id: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[Exception] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    priority: int = 0  # 优先级（数字越大优先级越高）

    def __lt__(self, other):
        """用于优先级队列排序"""
        return self.priority > other.priority  # 优先级高的先执行

    @property
    def duration(self) -> Optional[float]:
        """获取任务执行时长"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'status': self.status.value,
            'result': str(self.result) if self.result else None,
            'error': str(self.error) if self.error else None,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration': self.duration,
            'priority': self.priority
        }


class TaskQueue:
    """异步任务队列管理器"""

    def __init__(self, max_workers: int = 3, use_priority: bool = False):
        """
        初始化任务队列

        Args:
            max_workers: 最大并发worker数
            use_priority: 是否启用优先级队列
        """
        self.max_workers = max_workers
        self.use_priority = use_priority

        if use_priority:
            self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        else:
            self.queue: asyncio.Queue = asyncio.Queue()

        self.tasks: Dict[str, Task] = {}
        self.workers: List[asyncio.Task] = []
        self.logger = logging.getLogger(__name__)
        self._running = False
        self._worker_semaphore = asyncio.Semaphore(max_workers)

    async def start(self):
        """启动worker"""
        if self._running:
            self.logger.warning("Task queue already running")
            return

        self._running = True
        self.workers = [
            asyncio.create_task(self._worker(i))
            for i in range(self.max_workers)
        ]
        self.logger.info(f"Started {self.max_workers} workers")

    async def stop(self, graceful: bool = True):
        """
        停止所有worker

        Args:
            graceful: 是否优雅停止（等待队列清空）
        """
        if graceful:
            # 等待队列清空
            await self.queue.join()

        self._running = False

        # 取消所有worker
        for worker in self.workers:
            worker.cancel()

        await asyncio.gather(*self.workers, return_exceptions=True)
        self.logger.info("All workers stopped")

    async def submit(
        self,
        func: Callable,
        *args,
        task_id: Optional[str] = None,
        priority: int = 0,
        **kwargs
    ) -> Task:
        """
        提交任务到队列

        Args:
            func: 异步函数
            *args: 函数参数
            task_id: 任务ID（可选，不提供则自动生成）
            priority: 优先级（仅在use_priority=True时有效）
            **kwargs: 函数关键字参数

        Returns:
            Task对象
        """
        if task_id is None:
            task_id = str(uuid.uuid4())

        task = Task(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority
        )

        self.tasks[task_id] = task

        if self.use_priority:
            await self.queue.put((task.priority, task))
        else:
            await self.queue.put(task)

        self.logger.info(f"Task submitted: {task_id} (priority: {priority})")
        return task

    async def get_result(
        self,
        task_id: str,
        timeout: Optional[float] = None
    ) -> Any:
        """
        获取任务结果（阻塞直到完成）

        Args:
            task_id: 任务ID
            timeout: 超时时间（秒）

        Returns:
            任务结果

        Raises:
            ValueError: 任务不存在
            TimeoutError: 超时
            Exception: 任务执行失败
        """
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        start_time = asyncio.get_event_loop().time()

        while task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            if timeout:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    raise TimeoutError(f"Task {task_id} timeout")

            await asyncio.sleep(0.1)

        if task.status == TaskStatus.FAILED:
            raise task.error
        elif task.status == TaskStatus.CANCELLED:
            raise RuntimeError(f"Task {task_id} was cancelled")

        return task.result

    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功取消
        """
        task = self.tasks.get(task_id)
        if not task:
            return False

        if task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            self.logger.info(f"Task cancelled: {task_id}")
            return True
        else:
            self.logger.warning(f"Cannot cancel task {task_id} in status {task.status}")
            return False

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态，如果任务不存在则返回None
        """
        task = self.tasks.get(task_id)
        return task.status if task else None

    def get_task(self, task_id: str) -> Optional[Task]:
        """
        获取任务对象

        Args:
            task_id: 任务ID

        Returns:
            Task对象，如果不存在则返回None
        """
        return self.tasks.get(task_id)

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None
    ) -> List[Task]:
        """
        列出所有任务

        Args:
            status: 过滤特定状态的任务

        Returns:
            任务列表
        """
        if status:
            return [task for task in self.tasks.values() if task.status == status]
        return list(self.tasks.values())

    def get_queue_size(self) -> int:
        """获取队列中待处理任务数"""
        return self.queue.qsize()

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取队列统计信息

        Returns:
            统计信息字典
        """
        total_tasks = len(self.tasks)
        completed_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED])
        failed_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.FAILED])
        running_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.RUNNING])
        pending_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING])

        # 计算平均执行时间
        durations = [t.duration for t in self.tasks.values() if t.duration is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'failed_tasks': failed_tasks,
            'running_tasks': running_tasks,
            'pending_tasks': pending_tasks,
            'queue_size': self.get_queue_size(),
            'average_duration': avg_duration,
            'success_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        }

    async def _worker(self, worker_id: int):
        """
        Worker协程

        Args:
            worker_id: Worker ID
        """
        self.logger.info(f"Worker {worker_id} started")

        while self._running:
            try:
                # 从队列获取任务
                item = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=1.0
                )

                # 如果使用优先级队列，解包任务
                if self.use_priority:
                    _, task = item
                else:
                    task = item

                # 检查任务是否被取消
                if task.status == TaskStatus.CANCELLED:
                    self.queue.task_done()
                    continue

                # 执行任务
                await self._execute_task(task, worker_id)

                # 标记任务完成
                self.queue.task_done()

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Worker {worker_id} error: {e}")

        self.logger.info(f"Worker {worker_id} stopped")

    async def _execute_task(self, task: Task, worker_id: int):
        """
        执行单个任务

        Args:
            task: 任务对象
            worker_id: Worker ID
        """
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()

        self.logger.info(f"Worker {worker_id} executing task: {task.task_id}")

        try:
            # 执行任务函数
            result = await task.func(*task.args, **task.kwargs)
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()

            self.logger.info(
                f"Task completed: {task.task_id} "
                f"(duration: {task.duration:.2f}s)"
            )

        except Exception as e:
            task.error = e
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()

            self.logger.error(
                f"Task failed: {task.task_id}, error: {e} "
                f"(duration: {task.duration:.2f}s)"
            )

    async def wait_all(self, timeout: Optional[float] = None):
        """
        等待所有任务完成

        Args:
            timeout: 超时时间（秒）

        Raises:
            TimeoutError: 超时
        """
        if timeout:
            try:
                await asyncio.wait_for(self.queue.join(), timeout=timeout)
            except asyncio.TimeoutError:
                raise TimeoutError("Wait for all tasks timeout")
        else:
            await self.queue.join()

    def clear_completed_tasks(self):
        """清理已完成的任务"""
        completed_ids = [
            task_id for task_id, task in self.tasks.items()
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
        ]

        for task_id in completed_ids:
            del self.tasks[task_id]

        self.logger.info(f"Cleared {len(completed_ids)} completed tasks")
