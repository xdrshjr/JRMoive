"""
Project Manager service for managing project metadata and lifecycle.
"""
import json
import os
import shutil
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from loguru import logger
import filelock

from backend.models.project_models import (
    Project,
    ProjectStatus,
    CreateProjectRequest,
    UpdateProjectRequest,
    VideoType,
    GenerationMode
)
from backend.core.models import TaskStatus


class ProjectManager:
    """
    Manages project metadata, storage, and lifecycle operations.

    Responsibilities:
    - CRUD operations for project metadata
    - Thumbnail generation from video
    - Project asset cleanup
    - Status synchronization with TaskManager
    """

    def __init__(self, projects_dir: str = "backend/projects"):
        """
        Initialize ProjectManager.

        Args:
            projects_dir: Directory to store project metadata files
        """
        self.projects_dir = Path(projects_dir)
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"ProjectManager initialized with directory: {self.projects_dir}")

    def _generate_project_id(self) -> str:
        """Generate a unique project ID."""
        return f"proj_{uuid.uuid4().hex[:12]}"

    def _get_project_file_path(self, project_id: str) -> Path:
        """Get the file path for a project's metadata."""
        return self.projects_dir / f"{project_id}.json"

    def _get_project_thumbnail_path(self, project_id: str) -> Path:
        """Get the file path for a project's thumbnail."""
        project_dir = self.projects_dir / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir / "thumbnail.jpg"

    def _read_project_file(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Read project metadata from file with file locking.

        Args:
            project_id: Project identifier

        Returns:
            Project data dict or None if not found
        """
        file_path = self._get_project_file_path(project_id)
        if not file_path.exists():
            return None

        lock_path = str(file_path) + ".lock"
        lock = filelock.FileLock(lock_path, timeout=5)

        try:
            with lock:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error reading project file {project_id}: {e}")
            return None

    def _write_project_file(self, project: Project) -> bool:
        """
        Write project metadata to file with file locking.

        Args:
            project: Project object to save

        Returns:
            True if successful, False otherwise
        """
        file_path = self._get_project_file_path(project.id)
        lock_path = str(file_path) + ".lock"
        lock = filelock.FileLock(lock_path, timeout=5)

        try:
            with lock:
                # Update the updated_at timestamp
                project.updated_at = datetime.utcnow()

                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(project.dict(), f, indent=2, default=str)

                logger.debug(f"Project {project.id} saved successfully")
                return True
        except Exception as e:
            logger.error(f"Error writing project file {project.id}: {e}")
            return False

    def create_project(self, request: CreateProjectRequest) -> Project:
        """
        Create a new project.

        Args:
            request: Project creation request

        Returns:
            Created project
        """
        project_id = self._generate_project_id()

        project = Project(
            id=project_id,
            name=request.name,
            description=request.description,
            video_type=request.video_type,
            mode=request.mode,
            status=ProjectStatus.PENDING,
            progress=0
        )

        if self._write_project_file(project):
            logger.info(f"Created project: {project_id} - {project.name}")
            return project
        else:
            raise Exception(f"Failed to create project {project_id}")

    def get_project(self, project_id: str) -> Optional[Project]:
        """
        Get project by ID.

        Args:
            project_id: Project identifier

        Returns:
            Project object or None if not found
        """
        data = self._read_project_file(project_id)
        if data:
            return Project(**data)
        return None

    def list_projects(
        self,
        status: Optional[ProjectStatus] = None,
        video_type: Optional[VideoType] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Project]:
        """
        List all projects with optional filtering.

        Args:
            status: Filter by project status
            video_type: Filter by video type
            limit: Maximum number of projects to return
            offset: Number of projects to skip

        Returns:
            List of projects sorted by updated_at (newest first)
        """
        projects = []

        # Read all project files
        for file_path in self.projects_dir.glob("proj_*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    project = Project(**data)

                    # Apply filters
                    if status and project.status != status:
                        continue
                    if video_type and project.video_type != video_type:
                        continue

                    projects.append(project)
            except Exception as e:
                logger.error(f"Error reading project file {file_path}: {e}")
                continue

        # Sort by updated_at (newest first)
        projects.sort(key=lambda p: p.updated_at, reverse=True)

        # Apply pagination
        if limit:
            projects = projects[offset:offset + limit]
        elif offset:
            projects = projects[offset:]

        return projects

    def update_project(self, project_id: str, request: UpdateProjectRequest) -> Optional[Project]:
        """
        Update project metadata.

        Args:
            project_id: Project identifier
            request: Update request with fields to modify

        Returns:
            Updated project or None if not found
        """
        project = self.get_project(project_id)
        if not project:
            return None

        # Update fields if provided
        update_data = request.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)

        if self._write_project_file(project):
            logger.info(f"Updated project: {project_id}")
            return project
        else:
            raise Exception(f"Failed to update project {project_id}")

    def delete_project(self, project_id: str) -> bool:
        """
        Delete project and all associated assets.

        Args:
            project_id: Project identifier

        Returns:
            True if successful, False otherwise
        """
        project = self.get_project(project_id)
        if not project:
            logger.warning(f"Project {project_id} not found for deletion")
            return False

        try:
            # Delete project metadata file
            file_path = self._get_project_file_path(project_id)
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"Deleted project metadata file: {file_path}")

            # Delete project directory (thumbnails, etc.)
            project_dir = self.projects_dir / project_id
            if project_dir.exists():
                shutil.rmtree(project_dir)
                logger.debug(f"Deleted project directory: {project_dir}")

            # Delete temp_projects directory if exists
            if project.task_id:
                temp_dir = Path("backend/temp_projects") / project.task_id
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                    logger.debug(f"Deleted temp project directory: {temp_dir}")

            # Delete lock file if exists
            lock_path = Path(str(file_path) + ".lock")
            if lock_path.exists():
                lock_path.unlink()

            logger.info(f"Deleted project: {project_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting project {project_id}: {e}")
            return False

    def generate_thumbnail(self, project_id: str, video_path: str) -> Optional[str]:
        """
        Generate thumbnail from video first frame using FFmpeg.

        Args:
            project_id: Project identifier
            video_path: Path to video file

        Returns:
            Path to generated thumbnail or None if failed
        """
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return None

        thumbnail_path = self._get_project_thumbnail_path(project_id)

        try:
            # Use FFmpeg to extract first frame at 1 second
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-ss', '00:00:01',
                '-vframes', '1',
                '-vf', 'scale=640:-1',  # Scale to 640px width, maintain aspect ratio
                '-y',  # Overwrite output file
                str(thumbnail_path)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0 and thumbnail_path.exists():
                logger.info(f"Generated thumbnail for project {project_id}")
                return str(thumbnail_path)
            else:
                logger.error(f"FFmpeg failed: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            logger.error(f"Thumbnail generation timed out for project {project_id}")
            return None
        except Exception as e:
            logger.error(f"Error generating thumbnail for project {project_id}: {e}")
            return None

    def sync_task_status(self, project_id: str, task_status: TaskStatus, progress: int = 0) -> bool:
        """
        Sync project status with task status.

        Args:
            project_id: Project identifier
            task_status: Current task status
            progress: Task progress (0-100)

        Returns:
            True if successful, False otherwise
        """
        project = self.get_project(project_id)
        if not project:
            logger.warning(f"Project {project_id} not found for status sync")
            return False

        # Map task status to project status
        status_mapping = {
            TaskStatus.PENDING: ProjectStatus.PENDING,
            TaskStatus.PROCESSING: ProjectStatus.PROCESSING,
            TaskStatus.COMPLETED: ProjectStatus.COMPLETED,
            TaskStatus.FAILED: ProjectStatus.FAILED,
            TaskStatus.CANCELLED: ProjectStatus.CANCELLED
        }

        project.status = status_mapping.get(task_status, ProjectStatus.PENDING)
        project.progress = progress

        return self._write_project_file(project)

    def update_project_from_task_result(
        self,
        project_id: str,
        video_path: Optional[str] = None,
        duration: Optional[float] = None,
        scene_count: Optional[int] = None,
        character_count: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update project with task result data.

        Args:
            project_id: Project identifier
            video_path: Path to generated video
            duration: Video duration in seconds
            scene_count: Number of scenes
            character_count: Number of characters
            error_message: Error message if failed

        Returns:
            True if successful, False otherwise
        """
        project = self.get_project(project_id)
        if not project:
            return False

        if video_path:
            project.video_path = video_path

            # Generate thumbnail asynchronously (don't block on failure)
            try:
                thumbnail_path = self.generate_thumbnail(project_id, video_path)
                if thumbnail_path:
                    project.thumbnail_path = thumbnail_path
            except Exception as e:
                logger.warning(f"Failed to generate thumbnail for project {project_id}: {e}")

        if duration is not None:
            project.duration = duration
        if scene_count is not None:
            project.scene_count = scene_count
        if character_count is not None:
            project.character_count = character_count
        if error_message:
            project.error_message = error_message

        return self._write_project_file(project)

    def get_project_by_task_id(self, task_id: str) -> Optional[Project]:
        """
        Find project by associated task ID.

        Args:
            task_id: Task identifier

        Returns:
            Project object or None if not found
        """
        for file_path in self.projects_dir.glob("proj_*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get('task_id') == task_id:
                        return Project(**data)
            except Exception as e:
                logger.error(f"Error reading project file {file_path}: {e}")
                continue

        return None


# Global singleton instance
_project_manager: Optional[ProjectManager] = None


def get_project_manager() -> ProjectManager:
    """Get the global ProjectManager instance."""
    global _project_manager
    if _project_manager is None:
        _project_manager = ProjectManager()
    return _project_manager
