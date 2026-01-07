"""
Project Manager

Handles project folder operations: loading, validation, creation, and listing.
"""

import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from config.project_schema import ProjectConfig
from core.config_loader import load_yaml_config, validate_config_file
from core.validators import (
    validate_project_structure,
    validate_project_config,
    check_api_keys,
    perform_full_validation,
)
from core.errors import (
    ProjectNotFoundError,
    InvalidProjectStructureError,
    ConfigValidationError,
    ProjectAlreadyExistsError,
    TemplateNotFoundError,
)


class ProjectManager:
    """Manages drama generation projects"""

    def __init__(self, projects_root: Path = None):
        """
        Initialize project manager

        Args:
            projects_root: Root directory for all projects (default: ./projects)
        """
        if projects_root is None:
            projects_root = Path.cwd() / "projects"

        self.projects_root = projects_root
        self.templates_root = Path.cwd() / "templates"

    def validate_project_structure(self, project_path: Path) -> None:
        """
        Validate project folder structure

        Args:
            project_path: Path to project folder

        Raises:
            ProjectNotFoundError: If project doesn't exist
            InvalidProjectStructureError: If structure is invalid
        """
        if not project_path.exists():
            raise ProjectNotFoundError(str(project_path))

        is_valid, missing = validate_project_structure(project_path)
        if not is_valid:
            raise InvalidProjectStructureError(str(project_path), missing)

    def load_project(self, project_path: Path) -> Tuple[ProjectConfig, Path]:
        """
        Load and validate a project

        Args:
            project_path: Path to project folder

        Returns:
            Tuple of (ProjectConfig, absolute_project_path)

        Raises:
            ProjectNotFoundError: If project doesn't exist
            InvalidProjectStructureError: If structure is invalid
            ConfigValidationError: If config validation fails
        """
        # Convert to absolute path
        if not project_path.is_absolute():
            project_path = Path.cwd() / project_path

        # Validate structure
        self.validate_project_structure(project_path)

        # Load configuration
        config_path = project_path / "config.yaml"
        try:
            config = load_yaml_config(config_path)
        except Exception as e:
            raise ConfigValidationError(str(config_path), [str(e)])

        # Validate configuration against file system
        is_valid, errors = validate_project_config(config, project_path)
        if not is_valid:
            raise ConfigValidationError(str(config_path), errors)

        return config, project_path

    def create_project(
        self,
        project_name: str,
        template: str = "default",
        script_file: Optional[Path] = None,
        description: Optional[str] = None,
    ) -> Path:
        """
        Create a new project from template

        Args:
            project_name: Name of the project
            template: Template to use ('default' or 'minimal')
            script_file: Optional script file to copy
            description: Optional project description

        Returns:
            Path to created project folder

        Raises:
            ProjectAlreadyExistsError: If project already exists
            TemplateNotFoundError: If template doesn't exist
        """
        # Ensure projects root exists
        self.projects_root.mkdir(parents=True, exist_ok=True)

        # Check if project already exists
        project_path = self.projects_root / project_name
        if project_path.exists():
            raise ProjectAlreadyExistsError(project_name, str(project_path))

        # Validate template
        template_path = self.templates_root / template
        if not template_path.exists():
            raise TemplateNotFoundError(template)

        # Create project directory
        project_path.mkdir(parents=True)

        # Copy template files
        config_template = template_path / "config.yaml"
        if config_template.exists():
            shutil.copy(config_template, project_path / "config.yaml")

        readme_template = template_path / "README.md"
        if readme_template.exists():
            shutil.copy(readme_template, project_path / "README.md")

        # Update config with project metadata
        self._update_project_config(
            project_path / "config.yaml",
            project_name,
            description
        )

        # Copy script file if provided
        if script_file and script_file.exists():
            shutil.copy(script_file, project_path / "script.txt")
        else:
            # Create empty script file with template
            self._create_empty_script(project_path / "script.txt")

        # Create folder structure
        (project_path / "characters").mkdir(exist_ok=True)
        (project_path / "characters" / ".gitkeep").touch()

        (project_path / "outputs").mkdir(exist_ok=True)
        (project_path / "outputs" / ".gitkeep").touch()

        return project_path

    def list_projects(self) -> List[Dict[str, Any]]:
        """
        List all projects in projects root

        Returns:
            List of project info dictionaries
        """
        if not self.projects_root.exists():
            return []

        projects = []

        for item in self.projects_root.iterdir():
            if not item.is_dir():
                continue

            # Check if it's a valid project (has config.yaml)
            config_file = item / "config.yaml"
            if not config_file.exists():
                continue

            # Get project info
            try:
                info = self.get_project_info(item)
                projects.append(info)
            except Exception:
                # Skip invalid projects
                continue

        return sorted(projects, key=lambda x: x.get('name', ''))

    def get_project_info(self, project_path: Path) -> Dict[str, Any]:
        """
        Extract project information

        Args:
            project_path: Path to project folder

        Returns:
            Dictionary with project metadata
        """
        info = {
            "name": project_path.name,
            "path": str(project_path),
            "exists": project_path.exists(),
        }

        if not project_path.exists():
            return info

        # Check for config
        config_file = project_path / "config.yaml"
        if config_file.exists():
            info["has_config"] = True

            # Try to load config
            try:
                config = load_yaml_config(config_file)
                info["title"] = config.project.name
                info["description"] = config.project.description
                info["author"] = config.project.author
                info["version"] = config.project.version
            except Exception:
                info["config_valid"] = False
        else:
            info["has_config"] = False

        # Check for script
        script_file = project_path / "script.txt"
        if script_file.exists():
            info["has_script"] = True
            info["script_size"] = script_file.stat().st_size
        else:
            info["has_script"] = False

        # Check for outputs
        output_dir = project_path / "outputs"
        if output_dir.exists():
            final_dir = output_dir / "final"
            if final_dir.exists():
                videos = list(final_dir.glob("*.mp4"))
                info["has_outputs"] = len(videos) > 0
                if videos:
                    info["output_count"] = len(videos)
                    # Get most recent video
                    latest = max(videos, key=lambda p: p.stat().st_mtime)
                    info["latest_output"] = latest.name
                    info["latest_output_time"] = datetime.fromtimestamp(
                        latest.stat().st_mtime
                    ).isoformat()

        return info

    def validate_full_project(
        self,
        project_path: Path,
        check_dependencies: bool = True
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Perform full validation of project

        Args:
            project_path: Path to project folder
            check_dependencies: Whether to check system dependencies

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        try:
            config, abs_path = self.load_project(project_path)
            return perform_full_validation(abs_path, config, check_dependencies)
        except Exception as e:
            return False, [str(e)], []

    def _update_project_config(
        self,
        config_path: Path,
        project_name: str,
        description: Optional[str]
    ) -> None:
        """
        Update project configuration with metadata

        Args:
            config_path: Path to config.yaml
            project_name: Project name
            description: Project description
        """
        try:
            import yaml

            # Load existing config
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f) or {}

            # Update project metadata
            if 'project' not in config_data:
                config_data['project'] = {}

            config_data['project']['name'] = project_name

            if description:
                config_data['project']['description'] = description

            # Update output filename
            if 'output' not in config_data:
                config_data['output'] = {}

            if 'filename' not in config_data['output']:
                config_data['output']['filename'] = f"{project_name}.mp4"

            # Save updated config
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(
                    config_data,
                    f,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False
                )

        except Exception as e:
            # If update fails, that's ok - template is still valid
            pass

    def _create_empty_script(self, script_path: Path) -> None:
        """
        Create an empty script file with template

        Args:
            script_path: Path to script file
        """
        template = """# 短剧标题

作者: 作者名
简介: 在这里描述你的故事

## 角色
- 角色名: 描述, 年龄, 外貌特征

## 场景1: 地点 - 时间
地点: 具体地点描述
时间: 时间描述
天气: 天气状况
氛围: 氛围描述
镜头: 特写/中景/远景
运镜: 静止/摇镜/推镜/拉镜/跟镜
风格: cinematic/anime/realistic
色调: warm/cool/vibrant

描述: 场景的具体描述

角色名（情绪|语气）: "对话内容"

"""
        script_path.write_text(template, encoding='utf-8')


def get_project_manager() -> ProjectManager:
    """
    Get singleton project manager instance

    Returns:
        ProjectManager instance
    """
    return ProjectManager()
