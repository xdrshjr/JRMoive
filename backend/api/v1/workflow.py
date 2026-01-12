"""Workflow API Endpoints (REST v1)

Provides endpoints for full workflow video generation pipeline.
"""
from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import FileResponse
from pathlib import Path
import os

from backend.core.models import (
    WorkflowGenerationRequest,
    WorkflowGenerationResponse,
    TaskStatus,
    QuickModeWorkflowRequest
)
from backend.core.workflow_service import get_workflow_service
from backend.core.quick_mode_service import get_quick_mode_service
from backend.utils.asset_manager import get_asset_manager
from backend.core.task_manager import get_task_manager
from backend.core.exceptions import TaskNotFoundException
from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/generate", response_model=WorkflowGenerationResponse, summary="Generate Video Workflow")
async def generate_workflow(request: WorkflowGenerationRequest, http_request: Request):
    """
    Generate a complete video workflow from script to final composed video.
    
    This endpoint orchestrates the full CLI-based pipeline:
    1. Script parsing
    2. Character reference generation (if not provided)
    3. Scene image generation (if not provided)
    4. Video generation for each scene
    5. Video composition with transitions
    
    **Two Modes:**
    
    **Mode A - With Pre-generated Images:**
    ```json
    {
      "script": "# My Story\\n## Characters\\n...",
      "character_images": {
        "Alice": "base64_or_url",
        "Bob": "base64_or_url"
      },
      "scene_images": {
        "scene_001": "base64_or_url",
        "scene_002": "base64_or_url"
      },
      "config": {...}
    }
    ```
    
    **Mode B - Full Pipeline:**
    ```json
    {
      "script": "# My Story\\n## Characters\\n...",
      "config": {...}
    }
    ```
    
    **Returns:**
    - Task ID for polling status
    - Initial task status
    
    **Workflow:**
    1. Submit workflow request → Get task_id
    2. Poll `/api/v1/tasks/{task_id}` for status and progress
    3. When status="completed", get video_url and assets from result
    4. Access assets via `/api/v1/workflow/assets/{task_id}/{asset_type}/{filename}`
    """
    # Determine mode
    mode = "with_images" if (request.character_images or request.scene_images) else "full_pipeline"
    
    logger.info(
        f"WorkflowAPI | Workflow generation request | "
        f"mode={mode} | "
        f"script_length={len(request.script)} | "
        f"char_images={len(request.character_images) if request.character_images else 0} | "
        f"scene_images={len(request.scene_images) if request.scene_images else 0}"
    )
    
    try:
        # Get base URL from request
        base_url = str(http_request.base_url).rstrip('/')
        
        # Get task manager first to generate task_id
        task_manager = get_task_manager()
        
        # We need to capture the task_id in a closure
        # Since task_manager generates the ID during submit_task,
        # we'll create a holder for it
        workflow_task_id = None
        
        # Define workflow task
        async def workflow_task():
            # Use the task_id that was set after submission
            nonlocal workflow_task_id
            
            # Create progress callback that updates task status
            async def progress_callback(progress: float, message: str = ""):
                if workflow_task_id:
                    try:
                        await task_manager._update_task_status(
                            workflow_task_id,
                            TaskStatus.PROCESSING,
                            progress=int(progress),
                            message=message
                        )
                    except Exception as e:
                        logger.warning(f"WorkflowAPI | Failed to update progress | task_id={workflow_task_id} | error={e}")
            
            workflow_service = get_workflow_service()
            result = await workflow_service.execute_workflow(
                task_id=workflow_task_id,
                script=request.script,
                character_images=request.character_images,
                scene_images=request.scene_images,
                config=request.config,
                progress_callback=progress_callback,
                base_url=base_url
            )
            return result.dict()
        
        # Submit task
        task_id = await task_manager.submit_task(
            workflow_task,
            task_type="workflow"
        )
        
        # Set the task_id for the closure
        workflow_task_id = task_id
        
        logger.info(f"WorkflowAPI | Workflow task submitted | task_id={task_id} | mode={mode}")
        
        return WorkflowGenerationResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message=f"Workflow generation task submitted (mode: {mode}). Poll /api/v1/tasks/{task_id} for status."
        )
        
    except Exception as e:
        logger.exception(f"WorkflowAPI | Failed to submit workflow task | error={e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit workflow task: {str(e)}"
        )


@router.post("/quick-generate", response_model=WorkflowGenerationResponse, summary="Quick Mode Video Generation")
async def generate_quick_workflow(request: QuickModeWorkflowRequest, http_request: Request):
    """
    Generate video from pre-uploaded scene images (Quick Mode).

    This endpoint bypasses script parsing and image generation, directly generating
    videos from user-provided images with per-scene configuration.

    **Quick Mode Workflow:**
    1. User uploads images (scene_001.png, scene_002.png, etc.)
    2. User configures per-scene parameters (duration, prompt, camera motion)
    3. System generates videos directly from images
    4. System composes final video with transitions

    **Request Format:**
    ```json
    {
      "mode": "quick",
      "scenes": [
        {
          "scene_id": "scene_001",
          "image": "base64_encoded_image_or_url",
          "duration": 5,
          "prompt": "Camera slowly pans across the scene",
          "camera_motion": "pan",
          "motion_strength": 0.7
        },
        {
          "scene_id": "scene_002",
          "image": "base64_encoded_image_or_url",
          "duration": 7,
          "prompt": "Static shot with subtle movement",
          "camera_motion": "static",
          "motion_strength": 0.3
        }
      ],
      "config": {
        "video_fps": 30,
        "add_transitions": true
      }
    }
    ```

    **Returns:**
    - Task ID for polling status
    - Initial task status

    **Workflow:**
    1. Submit quick mode request → Get task_id
    2. Poll `/api/v1/tasks/{task_id}` for status and progress
    3. When status="completed", get video_url and assets from result
    4. Access assets via `/api/v1/workflow/assets/{task_id}/{asset_type}/{filename}`
    """
    logger.info(
        f"WorkflowAPI | Quick mode request | "
        f"scene_count={len(request.scenes)}"
    )

    try:
        # Get base URL from request
        base_url = str(http_request.base_url).rstrip('/')

        # Get task manager
        task_manager = get_task_manager()

        # Task ID holder
        workflow_task_id = None

        # Define quick mode workflow task
        async def quick_workflow_task():
            nonlocal workflow_task_id

            # Create progress callback
            async def progress_callback(progress: float, message: str = ""):
                if workflow_task_id:
                    try:
                        await task_manager._update_task_status(
                            workflow_task_id,
                            TaskStatus.PROCESSING,
                            progress=int(progress),
                            message=message
                        )
                    except Exception as e:
                        logger.warning(f"WorkflowAPI | Failed to update progress | task_id={workflow_task_id} | error={e}")

            # Execute quick mode workflow
            quick_mode_service = get_quick_mode_service()
            result = await quick_mode_service.execute_quick_workflow(
                task_id=workflow_task_id,
                scenes_config=request.scenes,
                config=request.config,
                progress_callback=progress_callback,
                base_url=base_url
            )
            return result.dict()

        # Submit task
        task_id = await task_manager.submit_task(
            quick_workflow_task,
            task_type="quick_workflow"
        )

        # Set task_id for closure
        workflow_task_id = task_id

        logger.info(f"WorkflowAPI | Quick mode task submitted | task_id={task_id} | scene_count={len(request.scenes)}")

        return WorkflowGenerationResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message=f"Quick mode workflow task submitted ({len(request.scenes)} scenes). Poll /api/v1/tasks/{task_id} for status."
        )

    except Exception as e:
        logger.exception(f"WorkflowAPI | Failed to submit quick mode task | error={e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit quick mode task: {str(e)}"
        )


@router.get(
    "/assets/{task_id}/{asset_type}/{filename}",
    summary="Get Workflow Asset",
    response_class=FileResponse
)
async def get_workflow_asset(task_id: str, asset_type: str, filename: str):
    """
    Get a specific asset from a workflow generation task.
    
    **Asset Types:**
    - `character_references` - Character reference images
    - `images` - Scene images
    - `videos` - Individual scene videos
    - `final` - Final composed video and metadata
    
    **Example:**
    ```
    GET /api/v1/workflow/assets/wf_abc123/final/workflow_wf_abc123.mp4
    GET /api/v1/workflow/assets/wf_abc123/images/scene_001_20260111_123456.png
    GET /api/v1/workflow/assets/wf_abc123/character_references/Alice_front.png
    ```
    
    **Returns:**
    - File content with appropriate content type
    - 404 if asset not found
    """
    logger.debug(f"WorkflowAPI | Asset request | task_id={task_id} | type={asset_type} | file={filename}")
    
    try:
        asset_manager = get_asset_manager()
        asset_path = asset_manager.get_asset_path(task_id, asset_type, filename)
        
        if asset_path is None or not asset_path.exists():
            logger.warning(f"WorkflowAPI | Asset not found | task_id={task_id} | type={asset_type} | file={filename}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset not found: {filename}"
            )
        
        logger.debug(f"WorkflowAPI | Serving asset | path={asset_path} | size={asset_path.stat().st_size}")
        
        # Determine media type
        suffix = asset_path.suffix.lower()
        media_type_map = {
            '.mp4': 'video/mp4',
            '.avi': 'video/x-msvideo',
            '.mov': 'video/quicktime',
            '.webm': 'video/webm',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.webp': 'image/webp',
            '.json': 'application/json',
        }
        media_type = media_type_map.get(suffix, 'application/octet-stream')
        
        return FileResponse(
            path=str(asset_path),
            media_type=media_type,
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"WorkflowAPI | Error serving asset | task_id={task_id} | error={e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error serving asset: {str(e)}"
        )


@router.get(
    "/cleanup",
    summary="Cleanup Old Workflow Assets",
    include_in_schema=False  # Admin endpoint, hide from public docs
)
async def cleanup_old_assets(max_age_hours: int = 24):
    """
    Clean up old workflow assets (admin endpoint).
    
    **Query Parameters:**
    - `max_age_hours`: Maximum age in hours before cleanup (default: 24)
    
    **Returns:**
    - Number of directories cleaned up
    """
    logger.info(f"WorkflowAPI | Cleanup requested | max_age_hours={max_age_hours}")
    
    try:
        asset_manager = get_asset_manager()
        cleaned_count = asset_manager.cleanup_old_assets(max_age_hours=max_age_hours)
        
        logger.info(f"WorkflowAPI | Cleanup completed | cleaned={cleaned_count}")
        
        return {
            "success": True,
            "cleaned_count": cleaned_count,
            "message": f"Cleaned up {cleaned_count} old workflow asset directories"
        }
        
    except Exception as e:
        logger.error(f"WorkflowAPI | Cleanup failed | error={e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cleanup failed: {str(e)}"
        )

