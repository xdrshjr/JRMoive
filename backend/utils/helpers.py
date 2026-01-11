"""Helper utility functions for the backend"""
import base64
import hashlib
import time
from typing import Optional
from pathlib import Path


def generate_task_id(prefix: str = "task") -> str:
    """Generate a unique task ID
    
    Args:
        prefix: Prefix for the task ID (e.g., 'img', 'vid', 'task')
        
    Returns:
        Unique task ID string
    """
    timestamp = str(time.time()).encode()
    hash_obj = hashlib.sha256(timestamp)
    short_hash = hash_obj.hexdigest()[:12]
    return f"{prefix}_{short_hash}"


def encode_file_to_base64(file_path: Path) -> str:
    """Encode a file to base64 string
    
    Args:
        file_path: Path to the file
        
    Returns:
        Base64 encoded string
    """
    with open(file_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def decode_base64_to_file(base64_str: str, output_path: Path) -> Path:
    """Decode base64 string and save to file
    
    Args:
        base64_str: Base64 encoded string
        output_path: Path to save the decoded file
        
    Returns:
        Path to the saved file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Remove data URL prefix if present
    if ',' in base64_str:
        base64_str = base64_str.split(',', 1)[1]
    
    with open(output_path, 'wb') as f:
        f.write(base64.b64decode(base64_str))
    
    return output_path


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string (e.g., "2.5s", "1m 30s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    return f"{minutes}m {remaining_seconds}s"


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename

