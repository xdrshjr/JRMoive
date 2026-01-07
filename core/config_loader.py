"""
Configuration Loader

Loads and merges project configurations from YAML files with proper priority handling.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import ValidationError

from config.project_schema import ProjectConfig


class ConfigLoadError(Exception):
    """Exception raised when configuration loading fails"""
    pass


def load_yaml_config(yaml_path: Path) -> ProjectConfig:
    """
    Load and parse YAML configuration file to ProjectConfig model

    Args:
        yaml_path: Path to YAML configuration file

    Returns:
        ProjectConfig object

    Raises:
        ConfigLoadError: If YAML file cannot be loaded or parsed
        ValidationError: If configuration validation fails
    """
    if not yaml_path.exists():
        raise ConfigLoadError(f"Configuration file not found: {yaml_path}")

    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            yaml_data = yaml.safe_load(f)

        if not yaml_data:
            raise ConfigLoadError(f"Empty configuration file: {yaml_path}")

        # Parse YAML data into ProjectConfig model
        config = ProjectConfig(**yaml_data)
        return config

    except yaml.YAMLError as e:
        raise ConfigLoadError(f"Invalid YAML format in {yaml_path}: {e}")
    except ValidationError as e:
        # Re-raise with more context
        error_messages = []
        for error in e.errors():
            loc = ".".join(str(x) for x in error['loc'])
            msg = error['msg']
            error_messages.append(f"  {loc}: {msg}")

        raise ConfigLoadError(
            f"Configuration validation failed in {yaml_path}:\n" +
            "\n".join(error_messages)
        )
    except Exception as e:
        raise ConfigLoadError(f"Failed to load configuration from {yaml_path}: {e}")


def merge_configs(
    base: Optional[Dict[str, Any]] = None,
    project: Optional[ProjectConfig] = None,
    overrides: Optional[Dict[str, Any]] = None
) -> ProjectConfig:
    """
    Merge multiple configuration sources with priority:
    CLI overrides > Project YAML > Base defaults

    Args:
        base: Base configuration defaults (dict)
        project: Project configuration from YAML
        overrides: Runtime overrides from CLI

    Returns:
        Merged ProjectConfig

    Raises:
        ConfigLoadError: If merge fails
    """
    try:
        # Start with project config
        if project is None:
            raise ConfigLoadError("Project configuration is required")

        # Convert to dict for merging
        config_dict = project.model_dump()

        # Apply CLI overrides if provided
        if overrides:
            config_dict = _deep_merge(config_dict, overrides)

        # Reconstruct ProjectConfig from merged dict
        merged_config = ProjectConfig(**config_dict)
        return merged_config

    except ValidationError as e:
        error_messages = []
        for error in e.errors():
            loc = ".".join(str(x) for x in error['loc'])
            msg = error['msg']
            error_messages.append(f"  {loc}: {msg}")

        raise ConfigLoadError(
            "Configuration merge validation failed:\n" +
            "\n".join(error_messages)
        )
    except Exception as e:
        raise ConfigLoadError(f"Failed to merge configurations: {e}")


def apply_cli_overrides(config: ProjectConfig, overrides: List[str]) -> ProjectConfig:
    """
    Apply CLI override arguments to configuration

    Args:
        config: Base configuration
        overrides: List of override strings in format "key.subkey=value"
                  Example: ["video.fps=60", "image.width=2560"]

    Returns:
        Updated ProjectConfig

    Raises:
        ConfigLoadError: If override format is invalid
    """
    if not overrides:
        return config

    override_dict = {}

    for override_str in overrides:
        try:
            if '=' not in override_str:
                raise ValueError(f"Invalid override format (expected key=value): {override_str}")

            key_path, value_str = override_str.split('=', 1)
            keys = key_path.split('.')

            if not keys:
                raise ValueError(f"Empty key in override: {override_str}")

            # Convert value string to appropriate type
            value = _parse_value(value_str)

            # Build nested dict from key path
            _set_nested_dict(override_dict, keys, value)

        except Exception as e:
            raise ConfigLoadError(f"Failed to parse override '{override_str}': {e}")

    # Merge overrides into config
    return merge_configs(project=config, overrides=override_dict)


def resolve_paths(config: ProjectConfig, base_path: Path) -> ProjectConfig:
    """
    Resolve all relative paths in configuration to absolute paths

    Args:
        config: Configuration with relative paths
        base_path: Project folder base path

    Returns:
        Configuration with resolved absolute paths
    """
    # Use the built-in resolve_paths method
    config.resolve_paths(base_path)
    return config


def _deep_merge(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries

    Args:
        base: Base dictionary
        update: Dictionary with updates

    Returns:
        Merged dictionary
    """
    result = base.copy()

    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dicts
            result[key] = _deep_merge(result[key], value)
        else:
            # Override value
            result[key] = value

    return result


def _set_nested_dict(d: Dict[str, Any], keys: List[str], value: Any) -> None:
    """
    Set a value in a nested dictionary using a key path

    Args:
        d: Dictionary to modify
        keys: List of keys representing the path
        value: Value to set

    Example:
        _set_nested_dict({}, ['video', 'fps'], 60)
        -> {'video': {'fps': 60}}
    """
    current = d

    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        elif not isinstance(current[key], dict):
            # Convert to dict if not already
            current[key] = {}
        current = current[key]

    # Set the final value
    current[keys[-1]] = value


def _parse_value(value_str: str) -> Any:
    """
    Parse string value to appropriate Python type

    Args:
        value_str: String value to parse

    Returns:
        Parsed value (int, float, bool, str)
    """
    value_str = value_str.strip()

    # Boolean
    if value_str.lower() in ('true', 'yes', 'on'):
        return True
    if value_str.lower() in ('false', 'no', 'off'):
        return False

    # None/null
    if value_str.lower() in ('none', 'null'):
        return None

    # Number
    try:
        # Try int first
        if '.' not in value_str:
            return int(value_str)
        # Try float
        return float(value_str)
    except ValueError:
        pass

    # String (remove quotes if present)
    if (value_str.startswith('"') and value_str.endswith('"')) or \
       (value_str.startswith("'") and value_str.endswith("'")):
        return value_str[1:-1]

    # Return as-is string
    return value_str


def validate_config_file(yaml_path: Path) -> tuple[bool, Optional[str]]:
    """
    Validate a configuration file without loading it fully

    Args:
        yaml_path: Path to YAML file

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        load_yaml_config(yaml_path)
        return True, None
    except (ConfigLoadError, ValidationError) as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected error: {e}"
