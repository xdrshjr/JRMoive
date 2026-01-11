"""OpenAI-compatible image generation endpoint

This endpoint mimics the OpenAI Images API format.
"""
from fastapi import APIRouter, HTTPException, status
import time
from typing import Optional, Literal

from pydantic import BaseModel, Field

from backend.core.service_wrapper import get_image_service, get_llm_service
from backend.core.exceptions import ServiceException
from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class OpenAIImageRequest(BaseModel):
    """OpenAI image generation request format"""
    prompt: str = Field(..., description="Image description")
    model: Optional[str] = Field(None, description="Model to use (mapped to service)")
    n: int = Field(1, ge=1, le=1, description="Number of images (currently only 1 supported)")
    size: Optional[str] = Field("1024x1024", description="Image size (e.g., '1024x1024')")
    response_format: Optional[Literal["url", "b64_json"]] = Field("url", description="Response format")
    quality: Optional[Literal["standard", "hd"]] = Field("standard", description="Image quality")
    style: Optional[str] = Field(None, description="Image style")


class OpenAIImageResponse(BaseModel):
    """OpenAI image generation response format"""
    created: int = Field(..., description="Creation timestamp")
    data: list = Field(..., description="List of generated images")


@router.post("/images/generations", response_model=OpenAIImageResponse, summary="Create Image (OpenAI Compatible)")
async def create_image(request: OpenAIImageRequest):
    """
    Create an image from a prompt (OpenAI API format).
    
    This endpoint is compatible with the OpenAI Python SDK:
    ```python
    import openai
    openai.api_base = "http://localhost:8000/v1"
    openai.api_key = "not-needed"
    
    response = openai.Image.create(
        prompt="A cute cat",
        n=1,
        size="1024x1024"
    )
    image_url = response['data'][0]['url']
    ```
    
    **Request Format:**
    ```json
    {
      "prompt": "A beautiful sunset over mountains",
      "n": 1,
      "size": "1024x1024",
      "response_format": "url",
      "quality": "standard"
    }
    ```
    
    **Response Format:**
    ```json
    {
      "created": 1677652288,
      "data": [
        {
          "url": "https://..."
        }
      ]
    }
    ```
    
    Or with `response_format: "b64_json"`:
    ```json
    {
      "created": 1677652288,
      "data": [
        {
          "b64_json": "iVBORw0KG..."
        }
      ]
    }
    ```
    """
    logger.info(f"OpenAI image generation request | size={request.size}")
    
    if request.n > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only n=1 is currently supported"
        )
    
    try:
        # Parse size
        if request.size and 'x' in request.size:
            width_str, height_str = request.size.split('x')
            width = int(width_str)
            height = int(height_str)
        else:
            width, height = 1024, 1024
        
        # Map quality to service parameters
        quality = "high" if request.quality == "hd" else "medium"
        
        # Generate image
        image_service = get_image_service()
        result = await image_service.generate_image(
            prompt=request.prompt,
            service_type=None,  # Use default from config
            width=width,
            height=height,
            quality=quality,
            style=request.style
        )
        
        # Extract result
        service_result = result.get("result", {})
        image_url = service_result.get("url")
        image_b64 = service_result.get("b64_json")
        
        # Format response
        if request.response_format == "b64_json":
            data_item = {"b64_json": image_b64} if image_b64 else {"url": image_url}
        else:
            data_item = {"url": image_url} if image_url else {"b64_json": image_b64}
        
        response = OpenAIImageResponse(
            created=int(time.time()),
            data=[data_item]
        )
        
        logger.info("OpenAI image generation successful")
        return response
        
    except ServiceException as e:
        logger.error(f"Image generation failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=e.message
        )
    except Exception as e:
        logger.exception(f"Unexpected error in image generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

