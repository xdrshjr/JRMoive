"""Request and response logging middleware

This middleware logs all incoming requests and outgoing responses with
detailed information including duration, status code, and client IP.
In DEBUG mode, also logs request/response bodies.
"""
import time
import json
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from backend.utils.logger import get_logger
from backend.config import settings

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
            logger.debug(f"Query params | request_id={request_id} | params={dict(request.query_params)}")
        
        # Log request headers in DEBUG mode
        if settings.log_level == "DEBUG":
            headers_dict = dict(request.headers)
            # 过滤敏感信息
            filtered_headers = {k: v for k, v in headers_dict.items() 
                              if k.lower() not in ['authorization', 'cookie', 'x-api-key']}
            logger.debug(f"Request headers | request_id={request_id} | headers={filtered_headers}")
        
        # Log request body in DEBUG mode (for POST/PUT/PATCH)
        request_body = None
        if settings.log_level == "DEBUG" and request.method in ["POST", "PUT", "PATCH"]:
            try:
                # Read body
                body_bytes = await request.body()
                if body_bytes:
                    request_body = body_bytes.decode('utf-8')
                    try:
                        # Try to parse as JSON for pretty printing
                        body_json = json.loads(request_body)
                        logger.debug(
                            f"Request body | request_id={request_id} | "
                            f"content_type={request.headers.get('content-type', 'unknown')} | "
                            f"body={json.dumps(body_json, indent=2, ensure_ascii=False)}"
                        )
                    except json.JSONDecodeError:
                        # Not JSON, log as string (truncate if too long)
                        truncated_body = request_body[:1000] + "..." if len(request_body) > 1000 else request_body
                        logger.debug(
                            f"Request body | request_id={request_id} | "
                            f"content_type={request.headers.get('content-type', 'unknown')} | "
                            f"body={truncated_body}"
                        )
                
                # Important: Recreate request with body for downstream handlers
                async def receive():
                    return {"type": "http.request", "body": body_bytes}
                
                request._receive = receive
                
            except Exception as e:
                logger.warning(f"Failed to read request body | request_id={request_id} | error={str(e)}")
        
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
            
            # Log response body in DEBUG mode
            if settings.log_level == "DEBUG" and response.status_code < 500:
                try:
                    # Read response body
                    response_body = b""
                    async for chunk in response.body_iterator:
                        response_body += chunk
                    
                    if response_body:
                        response_text = response_body.decode('utf-8')
                        try:
                            # Try to parse as JSON
                            response_json = json.loads(response_text)
                            logger.debug(
                                f"Response body | request_id={request_id} | "
                                f"status={response.status_code} | "
                                f"body={json.dumps(response_json, indent=2, ensure_ascii=False)}"
                            )
                        except json.JSONDecodeError:
                            # Not JSON, log as string (truncate if too long)
                            truncated_response = response_text[:1000] + "..." if len(response_text) > 1000 else response_text
                            logger.debug(
                                f"Response body | request_id={request_id} | "
                                f"status={response.status_code} | "
                                f"body={truncated_response}"
                            )
                    
                    # Recreate response with the body we just read
                    from starlette.responses import Response as StarletteResponse
                    response = StarletteResponse(
                        content=response_body,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type=response.media_type
                    )
                    
                except Exception as e:
                    logger.warning(f"Failed to read response body | request_id={request_id} | error={str(e)}")
            
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

