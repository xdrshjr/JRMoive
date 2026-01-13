"""Async task management system

This module provides task submission, status tracking, and result storage.
Tasks are stored in memory or Redis depending on configuration.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
import time
import traceback

from backend.core.models import TaskStatus, TaskInfo, TaskResult
from backend.core.exceptions import TaskNotFoundException, TaskCancelledException, StorageException, ServiceException
from backend.config import settings
from backend.utils.logger import get_logger
from backend.utils.helpers import generate_task_id

logger = get_logger(__name__)


class TaskStore:
    """In-memory task storage with automatic cleanup"""
    
    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def start_cleanup(self):
        """Start background cleanup task"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Task cleanup service started")
    
    async def stop_cleanup(self):
        """Stop background cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Task cleanup service stopped")
    
    async def _cleanup_loop(self):
        """Background loop to clean up expired tasks"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                await self.cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def cleanup_expired(self):
        """Remove tasks older than retention period"""
        async with self._lock:
            retention_delta = timedelta(hours=settings.task_retention_hours)
            now = datetime.utcnow()
            expired_tasks = []
            
            for task_id, task_data in self._tasks.items():
                created_at = task_data.get("created_at")
                if created_at and (now - created_at) > retention_delta:
                    expired_tasks.append(task_id)
            
            for task_id in expired_tasks:
                del self._tasks[task_id]
            
            if expired_tasks:
                logger.info(f"Cleaned up {len(expired_tasks)} expired tasks")
    
    async def save(self, task_id: str, task_data: Dict[str, Any]):
        """Save task data"""
        async with self._lock:
            self._tasks[task_id] = task_data
            logger.debug(f"Task saved: {task_id}")
    
    async def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task data"""
        async with self._lock:
            return self._tasks.get(task_id)
    
    async def delete(self, task_id: str):
        """Delete task data"""
        async with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                logger.debug(f"Task deleted: {task_id}")
    
    async def list_tasks(self) -> List[Dict[str, Any]]:
        """List all tasks"""
        async with self._lock:
            return list(self._tasks.values())


class TaskManager:
    """Manager for async task execution and tracking"""
    
    def __init__(self):
        self.store = TaskStore()
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_tasks)
        logger.info(f"TaskManager initialized (max concurrent: {settings.max_concurrent_tasks})")
    
    async def start(self):
        """Start the task manager"""
        await self.store.start_cleanup()
    
    async def stop(self):
        """Stop the task manager and cancel all running tasks"""
        # Cancel all running tasks
        for task_id, task in self._running_tasks.items():
            task.cancel()
            logger.info(f"Cancelled running task: {task_id}")
        
        # Wait for cancellation
        if self._running_tasks:
            await asyncio.gather(*self._running_tasks.values(), return_exceptions=True)
        
        await self.store.stop_cleanup()
    
    async def submit_task(
        self,
        task_func: Callable,
        task_type: str = "task",
        **kwargs
    ) -> str:
        """Submit a new task for async execution
        
        Args:
            task_func: Async function to execute
            task_type: Type prefix for task ID (e.g., 'img', 'vid')
            **kwargs: Arguments to pass to task_func
            
        Returns:
            Task ID
        """
        task_id = generate_task_id(task_type)
        
        # Create task data
        task_data = {
            "task_id": task_id,
            "status": TaskStatus.PENDING,
            "progress": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "message": "Task submitted",
            "task_type": task_type,
            "result": None,
            "error": None
        }
        
        await self.store.save(task_id, task_data)
        
        # Start task execution in background
        task = asyncio.create_task(self._execute_task(task_id, task_func, **kwargs))
        self._running_tasks[task_id] = task
        
        logger.info(f"Task submitted: {task_id} (type: {task_type})")
        
        return task_id
    
    async def _execute_task(
        self,
        task_id: str,
        task_func: Callable,
        **kwargs
    ):
        """Execute a task with error handling
        
        Args:
            task_id: Task identifier
            task_func: Async function to execute
            **kwargs: Arguments to pass to task_func
        """
        try:
            # Acquire semaphore for concurrency control
            async with self._semaphore:
                # Update status to processing
                await self._update_task_status(
                    task_id,
                    TaskStatus.PROCESSING,
                    message="Task processing started"
                )
                
                logger.info(f"Task processing started: {task_id}")
                start_time = time.time()
                
                # Execute the task function
                result = await task_func(**kwargs)
                
                duration = time.time() - start_time
                
                # Update status to completed
                await self._update_task_status(
                    task_id,
                    TaskStatus.COMPLETED,
                    progress=100,
                    message="Task completed successfully",
                    result=result
                )
                
                logger.info(f"Task completed: {task_id} (duration: {duration:.2f}s)")
                
        except asyncio.CancelledError:
            logger.warning(f"Task cancelled: {task_id}")
            await self._update_task_status(
                task_id,
                TaskStatus.CANCELLED,
                message="Task was cancelled"
            )
            
        except Exception as e:
            logger.exception(f"Task failed: {task_id} | error: {str(e)}")

            # 构建详细的错误信息
            error_info = {
                "type": type(e).__name__,
                "message": str(e),
                "traceback": traceback.format_exc()
            }

            # 如果是ServiceException，提取额外的错误信息
            if isinstance(e, ServiceException):
                error_info.update({
                    "service": e.service_name,
                    "retryable": e.retryable,
                    "error_code": e.error_code,
                    "error_type": e.error_type,
                    "stage": e.stage,
                    "api_response": e.api_response,
                    "original_error": str(e.original_error) if e.original_error else None
                })
                logger.error(f"Service error details | service={e.service_name} | "
                           f"code={e.error_code} | type={e.error_type} | "
                           f"stage={e.stage} | retryable={e.retryable}")

            await self._update_task_status(
                task_id,
                TaskStatus.FAILED,
                message=str(e),
                error=error_info
            )
        
        finally:
            # Remove from running tasks
            if task_id in self._running_tasks:
                del self._running_tasks[task_id]
    
    async def _update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress: int = None,
        message: str = None,
        result: Any = None,
        error: Any = None
    ):
        """Update task status
        
        Args:
            task_id: Task identifier
            status: New status
            progress: Progress percentage (0-100)
            message: Status message
            result: Task result data
            error: Error information
        """
        task_data = await self.store.get(task_id)
        if not task_data:
            logger.warning(f"Attempted to update non-existent task: {task_id}")
            return
        
        task_data["status"] = status
        task_data["updated_at"] = datetime.utcnow()
        
        if progress is not None:
            task_data["progress"] = progress
        
        if message is not None:
            task_data["message"] = message
        
        if result is not None:
            task_data["result"] = result
        
        if error is not None:
            task_data["error"] = error
        
        if status == TaskStatus.COMPLETED:
            task_data["completed_at"] = datetime.utcnow()
        
        await self.store.save(task_id, task_data)
    
    async def get_task_status(self, task_id: str) -> TaskInfo:
        """Get current task status
        
        Args:
            task_id: Task identifier
            
        Returns:
            TaskInfo object
            
        Raises:
            TaskNotFoundException: If task doesn't exist
        """
        task_data = await self.store.get(task_id)
        if not task_data:
            raise TaskNotFoundException(task_id)
        
        return TaskInfo(
            task_id=task_data["task_id"],
            status=task_data["status"],
            progress=task_data["progress"],
            created_at=task_data["created_at"],
            updated_at=task_data["updated_at"],
            message=task_data.get("message")
        )
    
    async def get_task_result(self, task_id: str) -> TaskResult:
        """Get complete task result
        
        Args:
            task_id: Task identifier
            
        Returns:
            TaskResult object
            
        Raises:
            TaskNotFoundException: If task doesn't exist
            TaskCancelledException: If task was cancelled
        """
        task_data = await self.store.get(task_id)
        if not task_data:
            raise TaskNotFoundException(task_id)
        
        if task_data["status"] == TaskStatus.CANCELLED:
            raise TaskCancelledException(task_id)
        
        return TaskResult(
            task_id=task_data["task_id"],
            status=task_data["status"],
            progress=task_data["progress"],
            created_at=task_data["created_at"],
            updated_at=task_data["updated_at"],
            completed_at=task_data.get("completed_at"),
            result=task_data.get("result"),
            error=task_data.get("error")
        )
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if task was cancelled, False if not running
        """
        if task_id in self._running_tasks:
            task = self._running_tasks[task_id]
            task.cancel()
            logger.info(f"Task cancellation requested: {task_id}")
            return True
        
        # If task exists but not running, mark as cancelled
        task_data = await self.store.get(task_id)
        if task_data and task_data["status"] in [TaskStatus.PENDING, TaskStatus.PROCESSING]:
            await self._update_task_status(
                task_id,
                TaskStatus.CANCELLED,
                message="Task cancelled by user"
            )
            return True
        
        return False
    
    async def list_all_tasks(self) -> List[TaskInfo]:
        """List all tasks
        
        Returns:
            List of TaskInfo objects
        """
        all_tasks = await self.store.list_tasks()
        return [
            TaskInfo(
                task_id=task["task_id"],
                status=task["status"],
                progress=task["progress"],
                created_at=task["created_at"],
                updated_at=task["updated_at"],
                message=task.get("message")
            )
            for task in all_tasks
        ]


# Global task manager instance
_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """Get the global task manager instance"""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager

