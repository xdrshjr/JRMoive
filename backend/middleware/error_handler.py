"""Global error handling middleware

This module provides centralized exception handling for the FastAPI application.
All exceptions are caught, logged, and converted to appropriate error responses.
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.core.exceptions import (
    APIException,
    ServiceException,
    TaskNotFoundException,
    TaskCancelledException,
    ValidationException
)
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def setup_exception_handlers(app: FastAPI):
    """Setup global exception handlers for the FastAPI app
    
    Args:
        app: FastAPI application instance
    """
    
    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        """Handle custom API exceptions"""
        logger.error(
            f"API Exception | path={request.url.path} | "
            f"code={exc.error_code} | message={exc.message}"
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details
                }
            }
        )
    
    @app.exception_handler(ServiceException)
    async def service_exception_handler(request: Request, exc: ServiceException):
        """Handle service-level exceptions"""
        logger.error(
            f"Service Exception | path={request.url.path} | "
            f"service={exc.service_name} | error={exc.message}"
        )
        
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": {
                    "code": "SERVICE_ERROR",
                    "message": f"Service error: {exc.message}",
                    "details": {
                        "service": exc.service_name,
                        "retryable": exc.retryable
                    }
                }
            }
        )
    
    @app.exception_handler(TaskNotFoundException)
    async def task_not_found_handler(request: Request, exc: TaskNotFoundException):
        """Handle task not found exceptions"""
        logger.warning(f"Task not found | task_id={exc.task_id}")
        
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": {
                    "code": "TASK_NOT_FOUND",
                    "message": f"Task not found: {exc.task_id}",
                    "details": {"task_id": exc.task_id}
                }
            }
        )
    
    @app.exception_handler(TaskCancelledException)
    async def task_cancelled_handler(request: Request, exc: TaskCancelledException):
        """Handle task cancellation exceptions"""
        logger.info(f"Task cancelled | task_id={exc.task_id}")
        
        return JSONResponse(
            status_code=status.HTTP_410_GONE,
            content={
                "error": {
                    "code": "TASK_CANCELLED",
                    "message": f"Task was cancelled: {exc.task_id}",
                    "details": {"task_id": exc.task_id}
                }
            }
        )
    
    @app.exception_handler(ValidationException)
    async def validation_exception_handler(request: Request, exc: ValidationException):
        """Handle validation exceptions"""
        logger.warning(f"Validation error | field={exc.field} | message={exc.message}")
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": exc.message,
                    "details": {"field": exc.field}
                }
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        """Handle Pydantic validation errors"""
        logger.warning(f"Request validation error | errors={exc.errors()}")
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": exc.errors()
                }
            }
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions"""
        logger.warning(
            f"HTTP Exception | path={request.url.path} | "
            f"status={exc.status_code} | detail={exc.detail}"
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": "HTTP_ERROR",
                    "message": exc.detail,
                    "details": {}
                }
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all other unexpected exceptions"""
        logger.exception(
            f"Unexpected error | path={request.url.path} | "
            f"error={type(exc).__name__} | message={str(exc)}"
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "details": {
                        "type": type(exc).__name__,
                        "message": str(exc)
                    }
                }
            }
        )

