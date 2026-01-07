"""
Custom Error Classes

Defines custom exceptions for the project management system with helpful error messages.
"""


class ProjectError(Exception):
    """Base exception for project-related errors"""

    def __init__(self, message: str, hint: str = None):
        """
        Initialize project error

        Args:
            message: Error message
            hint: Optional hint for resolving the error
        """
        self.message = message
        self.hint = hint
        super().__init__(self.message)

    def __str__(self):
        """Format error message with hint"""
        if self.hint:
            return f"{self.message}\n[HINT] {self.hint}"
        return self.message


class ProjectNotFoundError(ProjectError):
    """Raised when project folder does not exist"""

    def __init__(self, project_path: str):
        message = f"Project folder not found: {project_path}"
        hint = (
            "Create a new project using: python cli.py init <project_name>"
        )
        super().__init__(message, hint)


class InvalidProjectStructureError(ProjectError):
    """Raised when project folder structure is invalid"""

    def __init__(self, project_path: str, missing_items: list = None):
        if missing_items:
            missing_str = ", ".join(missing_items)
            message = f"Invalid project structure in {project_path}: missing {missing_str}"
        else:
            message = f"Invalid project structure in {project_path}"

        hint = (
            "A valid project must contain:\n"
            "  - config.yaml: Project configuration file\n"
            "  - script.txt: Script file (or as specified in config)"
        )
        super().__init__(message, hint)


class ConfigValidationError(ProjectError):
    """Raised when configuration validation fails"""

    def __init__(self, config_path: str, errors: list = None):
        if errors:
            error_str = "\n".join(f"  - {err}" for err in errors)
            message = f"Config validation failed in {config_path}:\n{error_str}"
        else:
            message = f"Config validation failed in {config_path}"

        hint = "Check the configuration file format and values. See templates/default/config.yaml for reference."
        super().__init__(message, hint)


class MissingAPIKeyError(ProjectError):
    """Raised when required API key is not configured"""

    def __init__(self, service: str, key_name: str):
        message = f"Required API key not configured: {key_name} (for service: {service})"
        hint = (
            f"Add {key_name} to your .env file or set as environment variable.\n"
            f"Example: {key_name}=your_api_key_here"
        )
        super().__init__(message, hint)


class CharacterImageNotFoundError(ProjectError):
    """Raised when character reference image file is not found"""

    def __init__(self, character_name: str, image_path: str, project_path: str):
        message = (
            f"Character reference image not found:\n"
            f"  Character: {character_name}\n"
            f"  Path: {image_path}"
        )
        hint = (
            "Either:\n"
            f"  1. Add the image file to: {project_path}/characters/\n"
            f"  2. Change mode to 'generate' in config.yaml to auto-generate references"
        )
        super().__init__(message, hint)


class ScriptFileNotFoundError(ProjectError):
    """Raised when script file is not found"""

    def __init__(self, script_path: str):
        message = f"Script file not found: {script_path}"
        hint = "Create a script file at the specified path or update the 'script.file' in config.yaml"
        super().__init__(message, hint)


class InvalidScriptFormatError(ProjectError):
    """Raised when script file format is invalid"""

    def __init__(self, script_path: str, parse_error: str):
        message = f"Invalid script format in {script_path}: {parse_error}"
        hint = (
            "Check the script format. Expected format:\n"
            "  - Title/标题\n"
            "  - 作者: Author Name\n"
            "  - ## 角色\n"
            "  - ## 场景N: Location - Time\n"
            "See examples/sample_scripts/ for reference."
        )
        super().__init__(message, hint)


class OutputDirectoryError(ProjectError):
    """Raised when output directory cannot be created or accessed"""

    def __init__(self, output_path: str, error: str):
        message = f"Failed to access output directory {output_path}: {error}"
        hint = "Check directory permissions and ensure the path is valid"
        super().__init__(message, hint)


class ProjectAlreadyExistsError(ProjectError):
    """Raised when trying to create a project that already exists"""

    def __init__(self, project_name: str, project_path: str):
        message = f"Project '{project_name}' already exists at: {project_path}"
        hint = (
            "Either:\n"
            "  1. Choose a different project name\n"
            "  2. Delete the existing project folder\n"
            "  3. Use the existing project"
        )
        super().__init__(message, hint)


class TemplateNotFoundError(ProjectError):
    """Raised when project template is not found"""

    def __init__(self, template_name: str):
        message = f"Project template not found: {template_name}"
        hint = "Available templates: default, minimal. Use 'default' if unsure."
        super().__init__(message, hint)


class ConfigOverrideError(ProjectError):
    """Raised when CLI config override format is invalid"""

    def __init__(self, override_str: str, error: str):
        message = f"Invalid config override '{override_str}': {error}"
        hint = (
            "Override format: --override key.subkey=value\n"
            "Examples:\n"
            "  --override video.fps=60\n"
            "  --override image.width=2560\n"
            "  --override composer.add_transitions=false"
        )
        super().__init__(message, hint)


class GenerationError(ProjectError):
    """Raised when drama generation fails"""

    def __init__(self, stage: str, error: str):
        message = f"Generation failed at stage '{stage}': {error}"
        hint = (
            "Check:\n"
            "  1. API keys are valid and have sufficient quota\n"
            "  2. Network connection is stable\n"
            "  3. Log file for detailed error information"
        )
        super().__init__(message, hint)


class CheckpointError(ProjectError):
    """Raised when checkpoint loading/saving fails"""

    def __init__(self, operation: str, error: str):
        message = f"Checkpoint {operation} failed: {error}"
        hint = (
            "If resuming from checkpoint fails, try:\n"
            "  1. Run without --resume flag to start fresh\n"
            "  2. Delete checkpoint files in project outputs folder"
        )
        super().__init__(message, hint)


def format_error_for_cli(error: Exception) -> str:
    """
    Format error for CLI display

    Args:
        error: Exception to format

    Returns:
        Formatted error string
    """
    if isinstance(error, ProjectError):
        return str(error)
    else:
        return f"[ERROR] {str(error)}"
