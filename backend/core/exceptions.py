"""Custom exceptions for the backend API

This module defines all custom exception classes used throughout the backend.
Each exception provides structured error information for proper error handling.
"""
from typing import Optional, Dict, Any


class APIException(Exception):
    """Base exception for all API-related errors"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "API_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}


class ServiceException(Exception):
    """Exception raised when an external service fails"""

    def __init__(
        self,
        message: str,
        service_name: str,
        retryable: bool = True,
        original_error: Optional[Exception] = None,
        error_code: str = "",
        error_type: str = "",
        stage: str = "",
        api_response: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.service_name = service_name
        self.retryable = retryable
        self.original_error = original_error
        self.error_code = error_code  # API返回的错误码
        self.error_type = error_type  # 错误类型分类（audio_filtered, content_policy等）
        self.stage = stage  # 错误发生的阶段（image_generation, video_generation等）
        self.api_response = api_response  # 完整的API响应

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，用于API响应"""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "service": self.service_name,
            "retryable": self.retryable,
            "error_code": self.error_code,
            "error_type": self.error_type,
            "stage": self.stage,
            "api_response": self.api_response,
            "original_error": str(self.original_error) if self.original_error else None
        }


class TaskNotFoundException(APIException):
    """Exception raised when a task is not found"""
    
    def __init__(self, task_id: str):
        super().__init__(
            message=f"Task not found: {task_id}",
            error_code="TASK_NOT_FOUND",
            status_code=404,
            details={"task_id": task_id}
        )
        self.task_id = task_id


class TaskCancelledException(APIException):
    """Exception raised when accessing a cancelled task"""
    
    def __init__(self, task_id: str):
        super().__init__(
            message=f"Task was cancelled: {task_id}",
            error_code="TASK_CANCELLED",
            status_code=410,
            details={"task_id": task_id}
        )
        self.task_id = task_id


class ValidationException(APIException):
    """Exception raised for validation errors"""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            details={"field": field} if field else {}
        )
        self.field = field


class ConfigurationException(APIException):
    """Exception raised for configuration errors"""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            status_code=500,
            details={"config_key": config_key} if config_key else {}
        )
        self.config_key = config_key


class RateLimitException(APIException):
    """Exception raised when rate limit is exceeded"""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details={"retry_after": retry_after} if retry_after else {}
        )
        self.retry_after = retry_after


class StorageException(APIException):
    """Exception raised for storage-related errors"""
    
    def __init__(self, message: str, operation: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="STORAGE_ERROR",
            status_code=500,
            details={"operation": operation} if operation else {}
        )
        self.operation = operation

