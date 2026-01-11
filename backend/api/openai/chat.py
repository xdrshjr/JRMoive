"""OpenAI-compatible chat completion endpoint

This endpoint mimics the OpenAI Chat API format for compatibility
with the OpenAI Python SDK and other tools.
"""
from fastapi import APIRouter, HTTPException, status
import time

from backend.core.models import ChatRequest, ChatResponse
from backend.core.service_wrapper import get_llm_service
from backend.core.exceptions import ServiceException
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/chat/completions", response_model=ChatResponse, summary="Chat Completions (OpenAI Compatible)")
async def chat_completions(request: ChatRequest):
    """
    Create a chat completion (OpenAI API format).
    
    This endpoint is compatible with the OpenAI Python SDK. You can use it
    as a drop-in replacement by setting:
    ```python
    import openai
    openai.api_base = "http://localhost:8000/v1"
    openai.api_key = "not-needed"  # Or your API key if auth is enabled
    
    response = openai.ChatCompletion.create(
        model="qwen3-next-80b-a3b-instruct",
        messages=[
            {"role": "user", "content": "Hello!"}
        ]
    )
    ```
    
    **Request Format:**
    ```json
    {
      "model": "qwen3-next-80b-a3b-instruct",
      "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
      ],
      "temperature": 0.7,
      "max_tokens": 1000
    }
    ```
    
    **Response Format:**
    ```json
    {
      "id": "chatcmpl-123456789",
      "object": "chat.completion",
      "created": 1677652288,
      "model": "qwen3-next-80b-a3b-instruct",
      "choices": [
        {
          "index": 0,
          "message": {
            "role": "assistant",
            "content": "Hello! How can I help you today?"
          },
          "finish_reason": "stop"
        }
      ],
      "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 15,
        "total_tokens": 25
      }
    }
    ```
    """
    logger.info(f"OpenAI chat completion request | messages={len(request.messages)}")
    
    if request.stream:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Streaming is not yet supported"
        )
    
    try:
        llm_service = get_llm_service()
        
        # Convert to dict format
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]
        
        # Generate completion
        response = await llm_service.chat_completion(
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        # Format response to OpenAI format
        formatted_response = {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model or response.get("model", "qwen3-next-80b-a3b-instruct"),
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response.get("content", response.get("message", ""))
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": response.get("usage", {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            })
        }
        
        logger.info("OpenAI chat completion successful")
        return formatted_response
        
    except ServiceException as e:
        logger.error(f"Chat completion failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=e.message
        )
    except Exception as e:
        logger.exception(f"Unexpected error in chat completion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

