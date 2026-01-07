"""
Metadata Generator

Generates comprehensive metadata for generated drama videos.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from config.project_schema import ProjectConfig


def generate_metadata(
    project_config: ProjectConfig,
    video_path: Path,
    generation_info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate comprehensive metadata for the generated video

    Args:
        project_config: Project configuration
        video_path: Path to generated video file
        generation_info: Information about the generation process

    Returns:
        Dictionary containing metadata
    """
    metadata = {
        # Project information
        "project": {
            "name": project_config.project.name,
            "description": project_config.project.description,
            "author": project_config.project.author,
            "version": project_config.project.version,
        },

        # Generation information
        "generation": {
            "timestamp": datetime.now().isoformat(),
            "video_path": str(video_path),
            "script_file": project_config.script.file,
        },

        # Scene information
        "scenes": {
            "count": generation_info.get("scene_count", 0),
            "total_duration": generation_info.get("total_duration", 0),
        },

        # Character information
        "characters": {
            "count": generation_info.get("character_count", 0),
            "names": generation_info.get("character_names", []),
            "reference_mode": project_config.characters.reference_mode if project_config.characters.enable_references else "disabled",
        },

        # Services used
        "services": {
            "image_generation": {
                "service": project_config.image.service,
                "resolution": f"{project_config.image.width}x{project_config.image.height}",
                "quality": project_config.image.quality,
            },
            "video_generation": {
                "service": project_config.video.service,
                "model": project_config.video.model,
                "fps": project_config.video.fps,
                "resolution": project_config.video.resolution,
            },
        },

        # Configuration snapshot
        "config": {
            "image": {
                "service": project_config.image.service,
                "max_concurrent": project_config.image.max_concurrent,
                "width": project_config.image.width,
                "height": project_config.image.height,
                "cfg_scale": project_config.image.cfg_scale,
                "steps": project_config.image.steps,
            },
            "video": {
                "service": project_config.video.service,
                "max_concurrent": project_config.video.max_concurrent,
                "fps": project_config.video.fps,
                "model": project_config.video.model,
            },
            "composer": {
                "add_transitions": project_config.composer.add_transitions,
                "transition_type": project_config.composer.transition_type,
                "bgm_enabled": project_config.composer.bgm.enabled,
            },
        },

        # File paths
        "paths": generation_info.get("paths", {}),

        # Performance metrics
        "performance": {
            "total_time_seconds": generation_info.get("total_time", 0),
            "image_generation_time": generation_info.get("image_generation_time", 0),
            "video_generation_time": generation_info.get("video_generation_time", 0),
            "composition_time": generation_info.get("composition_time", 0),
        },

        # Character consistency data (if available)
        "consistency": generation_info.get("character_consistency", {}),
    }

    return metadata


def save_metadata(
    metadata: Dict[str, Any],
    output_path: Path,
    format: str = "json"
) -> Path:
    """
    Save metadata to file

    Args:
        metadata: Metadata dictionary
        output_path: Path to save metadata
        format: Output format ('json' or 'yaml')

    Returns:
        Path to saved metadata file
    """
    if format == "json":
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    elif format == "yaml":
        import yaml
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(metadata, f, allow_unicode=True, default_flow_style=False)
    else:
        raise ValueError(f"Unsupported metadata format: {format}")

    return output_path


def load_metadata(metadata_path: Path) -> Dict[str, Any]:
    """
    Load metadata from file

    Args:
        metadata_path: Path to metadata file

    Returns:
        Metadata dictionary
    """
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

    suffix = metadata_path.suffix.lower()

    if suffix == ".json":
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    elif suffix in [".yaml", ".yml"]:
        import yaml
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    else:
        raise ValueError(f"Unsupported metadata format: {suffix}")


def format_metadata_summary(metadata: Dict[str, Any]) -> str:
    """
    Format metadata as human-readable summary

    Args:
        metadata: Metadata dictionary

    Returns:
        Formatted summary string
    """
    lines = []

    # Project info
    project = metadata.get("project", {})
    lines.append(f"Project: {project.get('name', 'Unknown')}")
    if project.get("description"):
        lines.append(f"Description: {project.get('description')}")
    if project.get("author"):
        lines.append(f"Author: {project.get('author')}")

    lines.append("")

    # Generation info
    generation = metadata.get("generation", {})
    timestamp = generation.get("timestamp", "")
    if timestamp:
        try:
            dt = datetime.fromisoformat(timestamp)
            timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            lines.append(f"Generated: {timestamp_str}")
        except:
            lines.append(f"Generated: {timestamp}")

    lines.append(f"Video: {generation.get('video_path', 'N/A')}")
    lines.append("")

    # Scenes and characters
    scenes = metadata.get("scenes", {})
    lines.append(f"Scenes: {scenes.get('count', 0)}")
    lines.append(f"Duration: {scenes.get('total_duration', 0):.1f}s")

    characters = metadata.get("characters", {})
    char_names = characters.get("names", [])
    if char_names:
        lines.append(f"Characters: {', '.join(char_names)}")

    lines.append("")

    # Services
    services = metadata.get("services", {})
    image_svc = services.get("image_generation", {})
    video_svc = services.get("video_generation", {})

    lines.append(f"Image Service: {image_svc.get('service', 'N/A')}")
    lines.append(f"Video Service: {video_svc.get('service', 'N/A')} ({video_svc.get('model', 'N/A')})")
    lines.append("")

    # Performance
    perf = metadata.get("performance", {})
    total_time = perf.get("total_time_seconds", 0)
    if total_time > 0:
        minutes = int(total_time // 60)
        seconds = int(total_time % 60)
        lines.append(f"Total Time: {minutes}m {seconds}s")

        image_time = perf.get("image_generation_time", 0)
        video_time = perf.get("video_generation_time", 0)
        if image_time > 0:
            lines.append(f"  Image Generation: {image_time:.1f}s")
        if video_time > 0:
            lines.append(f"  Video Generation: {video_time:.1f}s")

    return "\n".join(lines)
