"""Video generation API endpoints (REST v1)

Provides endpoints for async video generation from images.
"""
from fastapi import APIRouter, HTTPException, status
import tempfile
import httpx
from pathlib import Path

from backend.core.models import (
    VideoGenerationRequest,
    VideoGenerationResponse,
    VideoStatusResponse,
    TaskStatus
)
from backend.core.service_wrapper import get_video_service, get_llm_service
from backend.core.task_manager import get_task_manager
from backend.core.exceptions import ServiceException, TaskNotFoundException
from backend.config import settings
from backend.utils.logger import get_logger
from backend.utils.helpers import decode_base64_to_file

logger = get_logger(__name__)
router = APIRouter()


@router.post("/generate", response_model=VideoGenerationResponse, summary="Generate Video")
async def generate_video(request: VideoGenerationRequest):
    """
    Generate a video from an image (async operation).
    
    This endpoint submits a video generation task and returns a task ID.
    The video generation happens asynchronously. Poll the task status
    using the `/api/v1/tasks/{task_id}` endpoint.
    
    **Parameters:**
    - **image**: Base64 encoded image or URL
    - **prompt**: Optional video generation prompt
    - **duration**: Video duration in seconds (1-10)
    - **fps**: Frames per second (24-60)
    - **resolution**: Video resolution (e.g., "1920x1080")
    - **motion_strength**: Motion intensity (0.0-1.0)
    - **camera_motion**: Camera movement type
    - **optimize_prompt**: Auto-optimize prompt with LLM
    
    **Returns:**
    - Task ID for polling status
    - Initial task status
    
    **Workflow:**
    1. Submit video generation request → Get task_id
    2. Poll `/api/v1/tasks/{task_id}` for status
    3. When status="completed", get video_url from result
    """
    logger.info(f"Video generation request | duration={request.duration}s | fps={request.fps}")
    
    try:
        # Save image to temporary file
        temp_dir = Path(tempfile.mkdtemp())
        image_path = temp_dir / "input_image.png"
        
        # Handle base64 or URL
        if request.image.startswith("http://") or request.image.startswith("https://"):
            # URL - download to temporary file
            logger.info(f"Downloading image from URL: {request.image[:100]}...")
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(request.image)
                    response.raise_for_status()
                    
                    # Save to temp file
                    with open(image_path, 'wb') as f:
                        f.write(response.content)
                    
                    logger.info(f"Image downloaded successfully | size={len(response.content)} bytes")
            except httpx.HTTPError as e:
                logger.error(f"Failed to download image from URL: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to download image from URL: {str(e)}"
                )
            
            image_path_str = str(image_path)
        else:
            # Base64 - decode and save
            logger.info("Decoding base64 image data")
            decode_base64_to_file(request.image, image_path)
            image_path_str = str(image_path)
        
        logger.debug(f"Image saved to: {image_path_str}")
        
        # Optimize prompt if requested
        prompt = request.prompt
        if prompt and request.optimize_prompt and settings.enable_prompt_optimization:
            logger.info("Optimizing video prompt with LLM")
            llm_service = get_llm_service()
            prompt = await llm_service.optimize_prompt(prompt, prompt_type="video")
        
        # Define task function
        async def video_generation_task():
            video_service = get_video_service()
            result = await video_service.generate_video(
                image_path=image_path_str,
                prompt=prompt,
                duration=request.duration,
                fps=request.fps,
                resolution=request.resolution,
                motion_strength=request.motion_strength,
                camera_motion=request.camera_motion
            )
            return result
        
        # Submit task
        task_manager = get_task_manager()
        task_id = await task_manager.submit_task(
            video_generation_task,
            task_type="vid"
        )
        
        logger.info(f"Video generation task submitted | task_id={task_id}")
        
        return VideoGenerationResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message="Video generation task submitted. Poll /api/v1/tasks/{task_id} for status."
        )
        
    except Exception as e:
        logger.exception(f"Failed to submit video generation task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit task: {str(e)}"
        )


@router.get("/{video_id}", response_model=VideoStatusResponse, summary="Get Video Status")
async def get_video_status(video_id: str):
    """
    Get the status of a video generation task.
    
    **Note:** This endpoint is deprecated. Use `/api/v1/tasks/{task_id}` instead.
    
    Returns the current status, progress, and video URL if completed.
    """
    logger.info(f"Video status request | video_id={video_id}")
    
    try:
        task_manager = get_task_manager()
        task_result = await task_manager.get_task_result(video_id)
        
        # Extract video URL from result if completed
        video_url = None
        error_msg = None
        
        if task_result.status == TaskStatus.COMPLETED and task_result.result:
            service_result = task_result.result.get("result", {})
            video_url = service_result.get("video_url")
        elif task_result.status == TaskStatus.FAILED and task_result.error:
            error_msg = task_result.error.get("message")
        
        return VideoStatusResponse(
            task_id=task_result.task_id,
            status=task_result.status,
            progress=task_result.progress,
            video_url=video_url,
            error=error_msg,
            created_at=task_result.created_at,
            updated_at=task_result.updated_at
        )
        
    except TaskNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video task not found: {video_id}"
        )
    except Exception as e:
        logger.exception(f"Error getting video status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

