"""
API routes for project management.
"""
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse
from typing import Optional
from loguru import logger

from backend.models.project_models import (
    Project,
    CreateProjectRequest,
    UpdateProjectRequest,
    ProjectListResponse,
    ProjectResponse,
    ProjectStatus,
    VideoType
)
from backend.core.project_manager import get_project_manager


router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    status: Optional[ProjectStatus] = None,
    video_type: Optional[VideoType] = None,
    limit: Optional[int] = None,
    offset: int = 0
):
    """
    List all projects with optional filtering.

    Args:
        status: Filter by project status
        video_type: Filter by video type
        limit: Maximum number of projects to return
        offset: Number of projects to skip

    Returns:
        List of projects
    """
    try:
        project_manager = get_project_manager()
        projects = project_manager.list_projects(
            status=status,
            video_type=video_type,
            limit=limit,
            offset=offset
        )

        return ProjectListResponse(
            projects=projects,
            total=len(projects)
        )

    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {str(e)}")


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """
    Get project details by ID.

    Args:
        project_id: Project identifier

    Returns:
        Project details
    """
    try:
        project_manager = get_project_manager()
        project = project_manager.get_project(project_id)

        if not project:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

        return ProjectResponse(project=project)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get project: {str(e)}")


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(request: CreateProjectRequest):
    """
    Create a new project.

    Args:
        request: Project creation request

    Returns:
        Created project
    """
    try:
        project_manager = get_project_manager()
        project = project_manager.create_project(request)

        logger.info(f"Created project {project.id}: {project.name}")

        return ProjectResponse(project=project)

    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, request: UpdateProjectRequest):
    """
    Update project metadata.

    Args:
        project_id: Project identifier
        request: Update request

    Returns:
        Updated project
    """
    try:
        project_manager = get_project_manager()
        project = project_manager.update_project(project_id, request)

        if not project:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

        logger.info(f"Updated project {project_id}")

        return ProjectResponse(project=project)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update project: {str(e)}")


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str):
    """
    Delete project and all associated assets.

    Args:
        project_id: Project identifier

    Returns:
        No content
    """
    try:
        project_manager = get_project_manager()
        success = project_manager.delete_project(project_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

        logger.info(f"Deleted project {project_id}")

        return Response(status_code=204)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete project: {str(e)}")


@router.get("/{project_id}/thumbnail")
async def get_project_thumbnail(project_id: str):
    """
    Get project thumbnail image.

    Args:
        project_id: Project identifier

    Returns:
        Thumbnail image file
    """
    try:
        project_manager = get_project_manager()
        project = project_manager.get_project(project_id)

        if not project:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

        if not project.thumbnail_path:
            raise HTTPException(status_code=404, detail=f"Thumbnail not found for project {project_id}")

        # Return thumbnail file
        return FileResponse(
            project.thumbnail_path,
            media_type="image/jpeg",
            headers={
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                "Content-Disposition": f"inline; filename=thumbnail_{project_id}.jpg"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting thumbnail for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get thumbnail: {str(e)}")
