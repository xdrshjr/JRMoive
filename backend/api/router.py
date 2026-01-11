"""Main API router

This module combines all API routers (REST v1 and OpenAI-compatible)
"""
from fastapi import APIRouter

from backend.api.v1 import llm, images, videos, tasks
from backend.api.openai import chat, images as openai_images, videos as openai_videos

# Create main API router
api_router = APIRouter()

# REST API v1 routes
v1_router = APIRouter(prefix="/api/v1", tags=["REST API v1"])
v1_router.include_router(llm.router, prefix="/llm", tags=["LLM"])
v1_router.include_router(images.router, prefix="/images", tags=["Images"])
v1_router.include_router(videos.router, prefix="/videos", tags=["Videos"])
v1_router.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])

# OpenAI-compatible routes
openai_router = APIRouter(prefix="/v1", tags=["OpenAI Compatible"])
openai_router.include_router(chat.router, tags=["OpenAI Chat"])
openai_router.include_router(openai_images.router, tags=["OpenAI Images"])
openai_router.include_router(openai_videos.router, prefix="/videos", tags=["OpenAI Videos"])

# Include all routers
api_router.include_router(v1_router)
api_router.include_router(openai_router)

