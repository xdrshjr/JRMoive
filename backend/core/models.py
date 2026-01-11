"""Pydantic models for API requests and responses

This module defines all data models used in the API endpoints including
request models, response models, and task-related models.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from enum import Enum


# ==================== Task Models ====================

class TaskStatus(str, Enum):
    """Task status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskInfo(BaseModel):
    """Basic task information"""
    task_id: str = Field(..., description="Unique task identifier")
    status: TaskStatus = Field(..., description="Current task status")
    progress: int = Field(0, ge=0, le=100, description="Task progress percentage")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    message: Optional[str] = Field(None, description="Status message or error description")


class TaskResult(BaseModel):
    """Task result with output data"""
    task_id: str
    status: TaskStatus
    progress: int = 100
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = Field(None, description="Task result data")
    error: Optional[Dict[str, Any]] = Field(None, description="Error information if failed")


# ==================== LLM Models ====================

class ChatMessage(BaseModel):
    """Chat message for LLM conversations"""
    role: Literal["system", "user", "assistant"] = Field(..., description="Message role")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Chat completion request"""
    messages: List[ChatMessage] = Field(..., description="Conversation messages")
    model: Optional[str] = Field(None, description="LLM model to use")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, ge=1, description="Maximum tokens to generate")
    stream: bool = Field(False, description="Enable streaming response")


class ChatResponse(BaseModel):
    """Chat completion response"""
    id: str = Field(..., description="Response ID")
    object: str = "chat.completion"
    created: int = Field(..., description="Creation timestamp")
    model: str = Field(..., description="Model used")
    choices: List[Dict[str, Any]] = Field(..., description="Response choices")
    usage: Optional[Dict[str, int]] = Field(None, description="Token usage statistics")


class PromptOptimizationRequest(BaseModel):
    """Request to optimize a prompt"""
    prompt: str = Field(..., description="Original prompt to optimize")
    type: Literal["image", "video"] = Field(..., description="Optimization type")
    style: Optional[str] = Field(None, description="Desired style")
    enhance_details: bool = Field(True, description="Enhance prompt details")


class PromptOptimizationResponse(BaseModel):
    """Response from prompt optimization"""
    original_prompt: str
    optimized_prompt: str
    improvements: List[str] = Field(default_factory=list, description="List of improvements made")


# ==================== Image Models ====================

class ImageGenerationRequest(BaseModel):
    """Request to generate an image"""
    prompt: str = Field(..., min_length=1, description="Image description prompt")
    service: Optional[Literal["doubao", "nano_banana", "midjourney"]] = Field(
        None, 
        description="Image service to use (default: from config)"
    )
    width: int = Field(1920, ge=64, le=4096, description="Image width in pixels")
    height: int = Field(1080, ge=64, le=4096, description="Image height in pixels")
    quality: Literal["low", "medium", "high", "ultra"] = Field("high", description="Image quality")
    style: Optional[str] = Field(None, description="Image style")
    negative_prompt: Optional[str] = Field(None, description="Negative prompt")
    seed: Optional[int] = Field(None, description="Random seed for reproducibility")
    cfg_scale: Optional[float] = Field(None, ge=1.0, le=20.0, description="CFG guidance scale")
    steps: Optional[int] = Field(None, ge=20, le=100, description="Generation steps")
    optimize_prompt: bool = Field(False, description="Auto-optimize prompt with LLM")


class ImageToImageRequest(BaseModel):
    """Request for image-to-image generation"""
    prompt: str = Field(..., min_length=1, description="Image description prompt")
    image: str = Field(..., description="Base64 encoded reference image or URL")
    service: Optional[Literal["doubao"]] = Field(
        None,
        description="Image service (only doubao supports i2i)"
    )
    width: int = Field(1920, ge=64, le=4096)
    height: int = Field(1080, ge=64, le=4096)
    reference_weight: float = Field(0.7, ge=0.0, le=1.0, description="Reference image weight")
    negative_prompt: Optional[str] = Field(None)
    seed: Optional[int] = Field(None)
    cfg_scale: Optional[float] = Field(None, ge=1.0, le=20.0)
    steps: Optional[int] = Field(None, ge=20, le=100)


class ImageGenerationResponse(BaseModel):
    """Response from image generation"""
    task_id: Optional[str] = Field(None, description="Task ID for async operations")
    image_url: Optional[str] = Field(None, description="Generated image URL")
    image_b64: Optional[str] = Field(None, description="Base64 encoded image")
    service: str = Field(..., description="Service used")
    duration: Optional[float] = Field(None, description="Generation duration in seconds")


# ==================== Video Models ====================

class VideoGenerationRequest(BaseModel):
    """Request to generate a video from an image"""
    image: str = Field(..., description="Base64 encoded image or URL")
    prompt: Optional[str] = Field(None, description="Video generation prompt")
    duration: Optional[int] = Field(None, ge=1, le=10, description="Video duration in seconds")
    fps: int = Field(30, ge=24, le=60, description="Frames per second")
    resolution: str = Field("1920x1080", description="Video resolution")
    motion_strength: float = Field(0.5, ge=0.0, le=1.0, description="Motion strength")
    camera_motion: Optional[Literal["pan", "tilt", "zoom", "static"]] = Field(
        None,
        description="Camera motion type"
    )
    optimize_prompt: bool = Field(False, description="Auto-optimize prompt with LLM")


class VideoGenerationResponse(BaseModel):
    """Response from video generation (async)"""
    task_id: str = Field(..., description="Task ID for polling status")
    status: TaskStatus = Field(..., description="Initial task status")
    message: str = Field(..., description="Status message")


class VideoStatusResponse(BaseModel):
    """Video generation status response"""
    task_id: str
    status: TaskStatus
    progress: int = Field(ge=0, le=100)
    video_url: Optional[str] = Field(None, description="Video URL when completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime
    updated_at: datetime


# ==================== Service Info Models ====================

class ServiceInfo(BaseModel):
    """Information about an available service"""
    name: str = Field(..., description="Service name")
    type: str = Field(..., description="Service type (image/video/llm)")
    available: bool = Field(..., description="Whether service is configured and available")
    features: List[str] = Field(default_factory=list, description="Supported features")


class ServicesListResponse(BaseModel):
    """List of available services"""
    image_services: List[ServiceInfo]
    video_services: List[ServiceInfo]
    llm_services: List[ServiceInfo]

