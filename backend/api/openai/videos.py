"""OpenAI-compatible video generation endpoint

This endpoint mimics the OpenAI Videos API format (async with polling).
"""
from fastapi import APIRouter, HTTPException, status
import tempfile
from pathlib import Path
import time
from typing import Optional
from pydantic import BaseModel, Field

from backend.core.task_manager import get_task_manager
from backend.core.service_wrapper import get_video_service
from backend.core.exceptions import TaskNotFoundException
from backend.core.models import TaskStatus
from backend.utils.logger import get_logger
from backend.utils.helpers import decode_base64_to_file

logger = get_logger(__name__)
router = APIRouter()


class OpenAIVideoRequest(BaseModel):
    """OpenAI video generation request format"""
    prompt: str = Field(..., description="Video generation prompt")
    model: Optional[str] = Field("veo_3_1", description="Model to use")
    input_reference: Optional[str] = Field(None, description="Base64 encoded image or URL")
    size: Optional[str] = Field("1920x1080", description="Video resolution")
    seconds: Optional[int] = Field(None, ge=1, le=10, description="Video duration in seconds")


class OpenAIVideoResponse(BaseModel):
    """OpenAI video generation response format"""
    id: str = Field(..., description="Video task ID")
    object: str = "video"
    status: str = Field(..., description="Task status")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage")
    created: int = Field(..., description="Creation timestamp")
    video_url: Optional[str] = Field(None, description="Video URL when completed")


@router.post("/", response_model=OpenAIVideoResponse, summary="Create Video (OpenAI Compatible)")
async def create_video(request: OpenAIVideoRequest):
    """
    Create a video from an image and prompt (OpenAI API format - async).
    
    This endpoint submits a video generation task and returns immediately
    with a task ID. Poll the status endpoint to check progress.
    
    **Usage with OpenAI SDK (hypothetical):**
    ```python
    import openai
    openai.api_base = "http://localhost:8000/v1"
    openai.api_key = "not-needed"
    
    # Submit video generation
    response = openai.Video.create(
        prompt="A serene ocean scene",
        input_reference=image_base64,
        size="1920x1080",
        seconds=5
    )
    video_id = response['id']
    
    # Poll status
    while True:
        status = openai.Video.retrieve(video_id)
        if status['status'] == 'completed':
            video_url = status['video_url']
            break
        time.sleep(5)
    ```
    
    **Request Format:**
    ```json
    {
      "prompt": "A serene ocean scene with gentle waves",
      "input_reference": "base64_encoded_image...",
      "size": "1920x1080",
      "seconds": 5
    }
    ```
    
    **Response Format (submitted):**
    ```json
    {
      "id": "vid_abc123",
      "object": "video",
      "status": "pending",
      "progress": 0,
      "created": 1677652288,
      "video_url": null
    }
    ```
    """
    logger.info(f"OpenAI video generation request | size={request.size} | duration={request.seconds}s")
    
    if not request.input_reference:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="input_reference is required (base64 image or URL)"
        )
    
    try:
        # Save image to temporary file
        temp_dir = Path(tempfile.mkdtemp())
        image_path = temp_dir / "input_image.png"
        
        # Handle base64 or URL
        if request.input_reference.startswith("http://") or request.input_reference.startswith("https://"):
            image_path_str = request.input_reference
        else:
            decode_base64_to_file(request.input_reference, image_path)
            image_path_str = str(image_path)
        
        # Define task function
        async def video_generation_task():
            video_service = get_video_service()
            result = await video_service.generate_video(
                image_path=image_path_str,
                prompt=request.prompt,
                duration=request.seconds,
                fps=30,
                resolution=request.size or "1920x1080"
            )
            return result
        
        # Submit task
        task_manager = get_task_manager()
        task_id = await task_manager.submit_task(
            video_generation_task,
            task_type="vid"
        )
        
        logger.info(f"OpenAI video generation task submitted | task_id={task_id}")
        
        return OpenAIVideoResponse(
            id=task_id,
            object="video",
            status="pending",
            progress=0,
            created=int(time.time()),
            video_url=None
        )
        
    except Exception as e:
        logger.exception(f"Failed to submit video generation task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit task: {str(e)}"
        )


@router.get("/{video_id}", response_model=OpenAIVideoResponse, summary="Get Video Status")
async def get_video(video_id: str):
    """
    Retrieve video generation status (OpenAI API format).
    
    Poll this endpoint to check the status of a video generation task.
    When status is "completed", the video_url will be available.
    
    **Response Format (processing):**
    ```json
    {
      "id": "vid_abc123",
      "object": "video",
      "status": "processing",
      "progress": 45,
      "created": 1677652288,
      "video_url": null
    }
    ```
    
    **Response Format (completed):**
    ```json
    {
      "id": "vid_abc123",
      "object": "video",
      "status": "completed",
      "progress": 100,
      "created": 1677652288,
      "video_url": "https://..."
    }
    ```
    """
    logger.debug(f"OpenAI video status request | video_id={video_id}")
    
    try:
        task_manager = get_task_manager()
        task_result = await task_manager.get_task_result(video_id)
        
        # Extract video URL from result if completed
        video_url = None
        if task_result.status == TaskStatus.COMPLETED and task_result.result:
            service_result = task_result.result.get("result", {})
            video_url = service_result.get("video_url")
        
        # Map task status to OpenAI format
        status_map = {
            TaskStatus.PENDING: "pending",
            TaskStatus.PROCESSING: "processing",
            TaskStatus.COMPLETED: "completed",
            TaskStatus.FAILED: "failed",
            TaskStatus.CANCELLED: "cancelled"
        }
        
        return OpenAIVideoResponse(
            id=task_result.task_id,
            object="video",
            status=status_map.get(task_result.status, "unknown"),
            progress=task_result.progress,
            created=int(task_result.created_at.timestamp()),
            video_url=video_url
        )
        
    except TaskNotFoundException:
        logger.warning(f"Video task not found | video_id={video_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video not found: {video_id}"
        )
    except Exception as e:
        logger.exception(f"Error getting video status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/{video_id}/content", summary="Download Video")
async def get_video_content(video_id: str):
    """
    Get video download URL (OpenAI API format).
    
    Returns a redirect to the actual video file URL.
    """
    logger.debug(f"OpenAI video content request | video_id={video_id}")
    
    try:
        task_manager = get_task_manager()
        task_result = await task_manager.get_task_result(video_id)
        
        if task_result.status != TaskStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Video is not ready yet (status: {task_result.status})"
            )
        
        # Extract video URL
        if task_result.result:
            service_result = task_result.result.get("result", {})
            video_url = service_result.get("video_url")
            
            if video_url:
                from fastapi.responses import RedirectResponse
                return RedirectResponse(url=video_url, status_code=307)
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video URL not found in task result"
        )
        
    except TaskNotFoundException:
        logger.warning(f"Video task not found | video_id={video_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video not found: {video_id}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting video content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

