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
    import argparse
    import uvicorn
    import os
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run AI Movie Agent API server")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable DEBUG logging level"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set logging level (overrides --debug)"
    )
    parser.add_argument(
        "--host",
        default=settings.host,
        help=f"Host to bind to (default: {settings.host})"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.port,
        help=f"Port to bind to (default: {settings.port})"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=True,
        help="Enable auto-reload on code changes (default: True)"
    )
    parser.add_argument(
        "--no-reload",
        dest="reload",
        action="store_false",
        help="Disable auto-reload"
    )
    
    args = parser.parse_args()
    
    # Determine log level
    if args.log_level:
        log_level = args.log_level
    elif args.debug:
        log_level = "DEBUG"
    else:
        log_level = settings.log_level
    
    # Update settings with CLI arguments
    settings.log_level = log_level
    
    # IMPORTANT: Set environment variable so child processes also get DEBUG level
    os.environ['LOG_LEVEL'] = log_level
    
    # Re-initialize logging with new level
    setup_logging(log_level=log_level)
    
    logger.info("=" * 60)
    logger.info(f"Starting {settings.api_title} v{settings.api_version}")
    logger.info(f"Server: {args.host}:{args.port}")
    logger.info(f"Log Level: {log_level}")
    logger.info(f"Auto-reload: {args.reload}")
    logger.info(f"Image Service: {settings.image_service_type}")
    logger.info(f"Video Service: Veo3 ({settings.veo3_model})")
    logger.info("=" * 60)
    
    uvicorn.run(
        "backend.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=log_level.lower()
    )

