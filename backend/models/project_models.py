"""
Project data models for persistent project management.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class ProjectStatus(str, Enum):
    """Project status enum."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VideoType(str, Enum):
    """Video type enum."""
    NEWS_BROADCAST = "news_broadcast"
    ANIME = "anime"
    MOVIE = "movie"
    SHORT_DRAMA = "short_drama"


class GenerationMode(str, Enum):
    """Generation mode enum."""
    FULL = "full"
    QUICK = "quick"


class Project(BaseModel):
    """Project model representing a video generation project."""
    id: str = Field(..., description="Unique project identifier (e.g., proj_abc123)")
    name: str = Field(..., min_length=1, max_length=200, description="Project name")
    description: Optional[str] = Field(None, max_length=1000, description="Project description")
    video_type: VideoType = Field(..., description="Type of video to generate")
    mode: GenerationMode = Field(..., description="Generation mode (full or quick)")
    task_id: Optional[str] = Field(None, description="Associated task ID for tracking generation")
    status: ProjectStatus = Field(default=ProjectStatus.PENDING, description="Current project status")
    progress: int = Field(default=0, ge=0, le=100, description="Generation progress (0-100)")
    thumbnail_path: Optional[str] = Field(None, description="Path to project thumbnail image")
    video_path: Optional[str] = Field(None, description="Path to generated video file")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Project creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    duration: Optional[float] = Field(None, ge=0, description="Video duration in seconds")
    scene_count: Optional[int] = Field(None, ge=0, description="Number of scenes in video")
    character_count: Optional[int] = Field(None, ge=0, description="Number of characters in video")
    error_message: Optional[str] = Field(None, description="Error message if generation failed")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    @validator('updated_at', pre=True, always=True)
    def set_updated_at(cls, v):
        """Automatically update the updated_at timestamp."""
        return datetime.utcnow()


class CreateProjectRequest(BaseModel):
    """Request model for creating a new project."""
    name: str = Field(..., min_length=1, max_length=200, description="Project name")
    description: Optional[str] = Field(None, max_length=1000, description="Project description")
    video_type: VideoType = Field(..., description="Type of video to generate")
    mode: GenerationMode = Field(..., description="Generation mode (full or quick)")


class UpdateProjectRequest(BaseModel):
    """Request model for updating project metadata."""
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Project name")
    description: Optional[str] = Field(None, max_length=1000, description="Project description")
    status: Optional[ProjectStatus] = Field(None, description="Project status")
    progress: Optional[int] = Field(None, ge=0, le=100, description="Generation progress")
    thumbnail_path: Optional[str] = Field(None, description="Path to thumbnail image")
    video_path: Optional[str] = Field(None, description="Path to video file")
    duration: Optional[float] = Field(None, ge=0, description="Video duration")
    scene_count: Optional[int] = Field(None, ge=0, description="Number of scenes")
    character_count: Optional[int] = Field(None, ge=0, description="Number of characters")
    error_message: Optional[str] = Field(None, description="Error message")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ProjectListResponse(BaseModel):
    """Response model for listing projects."""
    projects: list[Project] = Field(default_factory=list, description="List of projects")
    total: int = Field(..., description="Total number of projects")


class ProjectResponse(BaseModel):
    """Response model for single project."""
    project: Project = Field(..., description="Project details")
