"""Logging utilities for backend services

This module provides utility functions for better log formatting,
especially for handling large data like base64 strings.
"""
from typing import Any, Dict, Optional


def truncate_base64(data: str, max_length: int = 50) -> str:
    """
    Truncate base64 or other long string data for logging
    
    Args:
        data: String data to truncate
        max_length: Maximum length before truncation
        
    Returns:
        Truncated string with size info
    """
    if not isinstance(data, str):
        return str(data)
    
    data_len = len(data)
    
    if data_len <= max_length:
        return data
    
    # Check if it looks like base64 (for better formatting)
    is_base64_like = (
        data_len > 100 and
        all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in data[:100])
    )
    
    if is_base64_like:
        return f"<base64 data: {data_len} chars, preview: {data[:30]}...>"
    else:
        return f"{data[:max_length]}... ({data_len} chars)"


def sanitize_log_dict(data: Dict[str, Any], max_length: int = 50) -> Dict[str, Any]:
    """
    Sanitize a dictionary for logging by truncating long strings
    
    Args:
        data: Dictionary to sanitize
        max_length: Maximum length for string values
        
    Returns:
        Sanitized dictionary copy
    """
    if not isinstance(data, dict):
        return data
    
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str) and len(value) > max_length:
            sanitized[key] = truncate_base64(value, max_length)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_dict(value, max_length)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_log_dict(item, max_length) if isinstance(item, dict)
                else truncate_base64(item, max_length) if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            sanitized[key] = value
    
    return sanitized


def format_image_dict_for_log(images: Optional[Dict[str, str]]) -> str:
    """
    Format character_images or scene_images dict for logging
    
    Args:
        images: Dictionary of name/id -> base64/url mapping
        
    Returns:
        Formatted string for logging
    """
    if not images:
        return "None"
    
    items = []
    for key, value in images.items():
        if isinstance(value, str):
            truncated = truncate_base64(value, max_length=30)
            items.append(f"{key}: {truncated}")
        else:
            items.append(f"{key}: {value}")
    
    return "{" + ", ".join(items) + "}"

