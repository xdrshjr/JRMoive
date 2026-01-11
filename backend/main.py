"""FastAPI Backend Main Application

This module initializes the FastAPI application with all routers, middleware,
and configuration for the AI Movie Agent API.
"""
import sys
from pathlib import Path

# Add parent directory to path to import existing services
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time

from backend.config import settings
from backend.utils.logger import setup_logging, get_logger
from backend.middleware.logging import LoggingMiddleware
from backend.middleware.error_handler import setup_exception_handlers
from backend.api.router import api_router

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    logger.info("=" * 60)
    logger.info(f"Starting {settings.api_title} v{settings.api_version}")
    logger.info(f"Server: {settings.host}:{settings.port}")
    logger.info(f"Log Level: {settings.log_level}")
    logger.info(f"Image Service: {settings.image_service_type}")
    logger.info(f"Video Service: Veo3 ({settings.veo3_model})")
    logger.info(f"Task Storage: {settings.task_storage_backend}")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("Shutting down API server...")
    logger.info("Cleanup completed")


# Initialize FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Setup exception handlers
setup_exception_handlers(app)

# Include API routers
app.include_router(api_router)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "status": "operational",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "rest_api": "/api/v1",
            "openai_compatible": "/v1"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": settings.api_title,
        "version": settings.api_version
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower()
    )

