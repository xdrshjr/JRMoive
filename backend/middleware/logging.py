"""Request and response logging middleware

This middleware logs all incoming requests and outgoing responses with
detailed information including duration, status code, and client IP.
In DEBUG mode, also logs request/response bodies.
"""
import time
import json
import re
from typing import Callable, Awaitable, Any, Dict, List, Union
from starlette.types import ASGIApp, Scope, Receive, Send, Message
from starlette.datastructures import Headers

from backend.utils.logger import get_logger
from backend.config import settings

logger = get_logger(__name__)


def _truncate_base64_in_dict(data: Any, max_length: int = 100) -> Any:
    """Recursively truncate base64 strings in a dictionary/list structure

    Args:
        data: The data structure to process (dict, list, or primitive)
        max_length: Maximum length to show for base64 strings

    Returns:
        A copy of the data with base64 strings truncated
    """
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            # Check if this looks like a base64 image field
            if isinstance(value, str) and key in ['image', 'reference_image', 'base64', 'data']:
                # Check if it's a base64 string (starts with data:image or is long alphanumeric)
                if value.startswith('data:image') or (len(value) > 200 and re.match(r'^[A-Za-z0-9+/=]+$', value[:100])):
                    # Truncate to first max_length chars
                    result[key] = f"{value[:max_length]}... [base64 image truncated, length={len(value)}]"
                else:
                    result[key] = _truncate_base64_in_dict(value, max_length)
            else:
                result[key] = _truncate_base64_in_dict(value, max_length)
        return result
    elif isinstance(data, list):
        return [_truncate_base64_in_dict(item, max_length) for item in data]
    else:
        return data


class LoggingMiddleware:
    """Pure ASGI middleware for logging HTTP requests and responses

    This implementation doesn't wrap responses like BaseHTTPMiddleware,
    which allows FileResponse and other streaming responses to work correctly.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process ASGI request

        Args:
            scope: ASGI scope dict
            receive: ASGI receive callable
            send: ASGI send callable
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Generate request ID
        request_id = f"req_{int(time.time() * 1000)}"

        # Get request info
        method = scope["method"]
        path = scope["path"]
        client_ip = scope.get("client", ["unknown"])[0] if scope.get("client") else "unknown"
        headers = Headers(scope=scope)

        # Log request
        logger.info(
            f"API Request | {method} {path} | "
            f"client_ip={client_ip} | request_id={request_id}"
        )

        # Log query string if present
        if scope.get("query_string"):
            logger.debug(f"Query string | request_id={request_id} | query={scope['query_string'].decode('utf-8')}")

        # Log request headers in DEBUG mode
        if settings.log_level == "DEBUG":
            # Filter sensitive headers
            filtered_headers = {k: v for k, v in headers.items()
                              if k.lower() not in ['authorization', 'cookie', 'x-api-key']}
            logger.debug(f"Request headers | request_id={request_id} | headers={filtered_headers}")

        # Log request body in DEBUG mode (for POST/PUT/PATCH)
        # We need to buffer the entire body, log it, then replay it
        if settings.log_level == "DEBUG" and method in ["POST", "PUT", "PATCH"]:
            # Buffer all body chunks
            body_chunks = []

            async def receive_buffered() -> Message:
                message = await receive()
                if message["type"] == "http.request":
                    body = message.get("body", b"")
                    if body:
                        body_chunks.append(body)

                    # When body is complete, log it
                    if not message.get("more_body", False):
                        request_body = b"".join(body_chunks)
                        if request_body:
                            try:
                                body_text = request_body.decode('utf-8')
                                try:
                                    body_json = json.loads(body_text)
                                    # Truncate base64 image data for cleaner logs
                                    body_json_truncated = _truncate_base64_in_dict(body_json)
                                    logger.debug(
                                        f"Request body | request_id={request_id} | "
                                        f"content_type={headers.get('content-type', 'unknown')} | "
                                        f"body={json.dumps(body_json_truncated, indent=2, ensure_ascii=False)}"
                                    )
                                except json.JSONDecodeError:
                                    truncated_body = body_text[:1000] + "..." if len(body_text) > 1000 else body_text
                                    logger.debug(
                                        f"Request body | request_id={request_id} | "
                                        f"content_type={headers.get('content-type', 'unknown')} | "
                                        f"body={truncated_body}"
                                    )
                            except Exception as e:
                                logger.warning(f"Failed to decode request body | request_id={request_id} | error={str(e)}")
                return message

            # Collect all body chunks first
            messages = []
            while True:
                message = await receive_buffered()
                messages.append(message)
                if message["type"] == "http.request" and not message.get("more_body", False):
                    break
                elif message["type"] != "http.request":
                    break

            # Create a new receive that replays the buffered messages
            message_index = 0
            async def receive_replay() -> Message:
                nonlocal message_index
                if message_index < len(messages):
                    msg = messages[message_index]
                    message_index += 1
                    return msg
                # If we've replayed all messages, call original receive for any additional messages
                return await receive()

            receive = receive_replay

        # Track response info
        start_time = time.time()
        status_code = 500
        response_headers = {}
        response_body = b""

        async def send_with_logging(message: Message) -> None:
            nonlocal status_code, response_headers, response_body

            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_headers = dict(message.get("headers", []))

                # Add custom headers
                headers_list = list(message.get("headers", []))
                headers_list.append((b"x-request-id", request_id.encode()))
                headers_list.append((b"x-process-time", f"{time.time() - start_time:.3f}".encode()))
                message["headers"] = headers_list

                await send(message)

            elif message["type"] == "http.response.body":
                body = message.get("body", b"")
                more_body = message.get("more_body", False)

                # Collect body for logging (only for non-streaming responses in DEBUG mode)
                content_type = None
                for header_name, header_value in response_headers.items():
                    if header_name.lower() == b"content-type":
                        content_type = header_value.decode('utf-8', errors='ignore')
                        break

                is_binary = content_type and any(
                    content_type.startswith(prefix)
                    for prefix in ['video/', 'image/', 'audio/', 'application/octet-stream']
                )

                # Only collect body for logging if it's not binary and in DEBUG mode
                if settings.log_level == "DEBUG" and not is_binary and status_code < 500:
                    response_body += body

                # Send the body chunk
                await send(message)

                # Log response when complete
                if not more_body:
                    duration = time.time() - start_time

                    logger.info(
                        f"API Response | {method} {path} | "
                        f"status={status_code} | duration={duration:.3f}s | "
                        f"request_id={request_id}"
                    )

                    # Log response body in DEBUG mode (skip binary content)
                    if settings.log_level == "DEBUG" and response_body and not is_binary and status_code < 500:
                        try:
                            response_text = response_body.decode('utf-8')
                            try:
                                response_json = json.loads(response_text)
                                # Truncate base64 image data for cleaner logs
                                response_json_truncated = _truncate_base64_in_dict(response_json)
                                logger.debug(
                                    f"Response body | request_id={request_id} | "
                                    f"status={status_code} | "
                                    f"body={json.dumps(response_json_truncated, indent=2, ensure_ascii=False)}"
                                )
                            except json.JSONDecodeError:
                                truncated_response = response_text[:1000] + "..." if len(response_text) > 1000 else response_text
                                logger.debug(
                                    f"Response body | request_id={request_id} | "
                                    f"status={status_code} | "
                                    f"body={truncated_response}"
                                )
                        except Exception as e:
                            logger.debug(f"Skipping response body logging | request_id={request_id} | error={str(e)}")
                    elif is_binary:
                        content_length = response_headers.get(b"content-length", b"unknown").decode('utf-8', errors='ignore')
                        logger.debug(
                            f"Serving binary content | request_id={request_id} | "
                            f"content_type={content_type} | "
                            f"content_length={content_length}"
                        )
            else:
                await send(message)

        try:
            await self.app(scope, receive, send_with_logging)
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"API Error | {method} {path} | "
                f"error={type(e).__name__} | message={str(e)} | "
                f"duration={duration:.3f}s | request_id={request_id}"
            )
            raise
