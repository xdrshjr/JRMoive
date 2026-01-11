"""Centralized logging configuration for the backend

This module sets up structured logging with rotation and proper formatting.
Logs are categorized into different files based on severity.
"""
import sys
from pathlib import Path
from loguru import logger
from backend.config import settings


def setup_logging():
    """Configure logging with rotation and formatting"""
    
    # Remove default logger
    logger.remove()
    
    # Create log directory
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Console output (all levels based on LOG_LEVEL)
    logger.add(
        sys.stdout,
        format=settings.log_format,
        level=settings.log_level,
        colorize=True
    )
    
    # API log file (INFO and above)
    logger.add(
        log_dir / "api.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        level="INFO",
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        compression="zip",
        enqueue=True
    )
    
    # Error log file (ERROR and above)
    logger.add(
        log_dir / "error.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        compression="zip",
        enqueue=True,
        backtrace=True,
        diagnose=True
    )
    
    # Debug log file (DEBUG and above) - only if log level is DEBUG
    if settings.log_level == "DEBUG":
        logger.add(
            log_dir / "debug.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            level="DEBUG",
            rotation=settings.log_rotation,
            retention=settings.log_retention,
            compression="zip",
            enqueue=True
        )
    
    logger.info("Logging system initialized")
    logger.info(f"Log directory: {log_dir.absolute()}")
    logger.info(f"Log level: {settings.log_level}")


def get_logger(name: str):
    """Get a logger instance for a specific module
    
    Args:
        name: Module name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logger.bind(name=name)

