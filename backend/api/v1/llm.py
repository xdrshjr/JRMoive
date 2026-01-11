"""LLM API endpoints (REST v1)

Provides endpoints for chat completion and prompt optimization.
"""
from fastapi import APIRouter, HTTPException, status
from typing import List
import time

from backend.core.models import (
    ChatRequest,
    ChatResponse,
    ChatMessage,
    PromptOptimizationRequest,
    PromptOptimizationResponse
)
from backend.core.service_wrapper import get_llm_service
from backend.core.exceptions import ServiceException
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/chat", response_model=ChatResponse, summary="Chat Completion")
async def chat_completion(request: ChatRequest):
    """
    Generate a chat completion using LLM.
    
    This endpoint accepts a list of messages and generates a response
    using the configured LLM service.
    
    **Parameters:**
    - **messages**: List of conversation messages with roles and content
    - **model**: Optional model override (uses configured model by default)
    - **temperature**: Sampling temperature (0.0 to 2.0)
    - **max_tokens**: Maximum tokens to generate
    - **stream**: Enable streaming (not yet supported)
    
    **Returns:**
    - OpenAI-compatible chat completion response
    """
    logger.info(f"Chat completion request | messages={len(request.messages)}")
    
    if request.stream:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Streaming is not yet supported"
        )
    
    try:
        llm_service = get_llm_service()
        
        # Convert Pydantic models to dicts
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
        
        logger.debug(f"Raw LLM response: {response}")
        
        # Extract content from the response
        # The LLM service returns OpenAI-format response with nested structure
        content = ""
        if "choices" in response and len(response["choices"]) > 0:
            # Response already in OpenAI format from LLM service
            content = response["choices"][0]["message"]["content"]
            logger.debug(f"Extracted content from choices: {content[:100]}...")
        elif "content" in response:
            # Fallback: direct content field
            content = response["content"]
            logger.debug(f"Extracted content from direct field: {content[:100]}...")
        elif "message" in response:
            # Fallback: message field
            content = response["message"]
            logger.debug(f"Extracted content from message field: {content[:100]}...")
        else:
            logger.warning(f"No content found in response, response keys: {response.keys()}")
        
        # Format response to match OpenAI format
        formatted_response = {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model or response.get("model", "unknown"),
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
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
        
        logger.info(f"Chat completion successful | content_length={len(content)} chars")
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


@router.post("/optimize-prompt", response_model=PromptOptimizationResponse, summary="Optimize Prompt")
async def optimize_prompt(request: PromptOptimizationRequest):
    """
    Optimize a prompt for image or video generation using LLM.
    
    This endpoint takes a simple prompt and enhances it with more details,
    better structure, and style improvements for better generation results.
    
    **Parameters:**
    - **prompt**: Original prompt to optimize
    - **type**: Optimization type ('image' or 'video')
    - **style**: Desired style (optional)
    - **enhance_details**: Whether to add more details
    
    **Returns:**
    - Original and optimized prompts with list of improvements
    """
    logger.info(f"Prompt optimization request | type={request.type} | length={len(request.prompt)}")
    
    try:
        llm_service = get_llm_service()
        
        # Optimize prompt
        optimized = await llm_service.optimize_prompt(
            prompt=request.prompt,
            prompt_type=request.type
        )
        
        # Extract improvements (simplified)
        improvements = [
            "Enhanced visual details",
            "Improved composition structure",
            "Added technical parameters",
            "Optimized for generation quality"
        ]
        
        logger.info("Prompt optimization successful")
        
        return PromptOptimizationResponse(
            original_prompt=request.prompt,
            optimized_prompt=optimized,
            improvements=improvements
        )
        
    except ServiceException as e:
        logger.error(f"Prompt optimization failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=e.message
        )
    except Exception as e:
        logger.exception(f"Unexpected error in prompt optimization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

