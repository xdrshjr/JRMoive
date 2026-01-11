"""Request and response logging middleware

This middleware logs all incoming requests and outgoing responses with
detailed information including duration, status code, and client IP.
"""
import time
import json
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details
        
        Args:
            request: Incoming request
            call_next: Next middleware/endpoint
            
        Returns:
            Response from the endpoint
        """
        # Generate request ID
        request_id = f"req_{int(time.time() * 1000)}"
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Log request
        logger.info(
            f"API Request | {request.method} {request.url.path} | "
            f"client_ip={client_ip} | request_id={request_id}"
        )
        
        # Log query parameters if present
        if request.query_params:
            logger.debug(f"Query params: {dict(request.query_params)}")
        
        # Process request and measure duration
        start_time = time.time()
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Log response
            logger.info(
                f"API Response | {request.method} {request.url.path} | "
                f"status={response.status_code} | duration={duration:.3f}s | "
                f"request_id={request_id}"
            )
            
            # Add custom headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{duration:.3f}"
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            logger.error(
                f"API Error | {request.method} {request.url.path} | "
                f"error={type(e).__name__} | message={str(e)} | "
                f"duration={duration:.3f}s | request_id={request_id}"
            )
            
            raise

