"""
Migration script to link orphaned tasks to projects and fix stuck project statuses.

This script:
1. Finds projects with task_id=null and status=pending (orphaned projects)
2. Finds completed tasks in temp_projects
3. Links completed tasks to their corresponding projects
4. Creates projects for orphaned completed tasks
5. Updates project statuses to match task completion status
"""
import json
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root))

from backend.core.project_manager import get_project_manager
from backend.models.project_models import (
    UpdateProjectRequest,
    CreateProjectRequest,
    ProjectStatus,
    VideoType,
    GenerationMode
)
from loguru import logger


def find_completed_workflow_results():
    """
    Find all completed workflow results in temp_projects.
    
    Returns:
        Dict mapping task_id to result metadata
    """
    temp_dir = Path("backend/temp_projects")
    completed_tasks = {}
    
    if not temp_dir.exists():
        logger.warning(f"temp_projects directory not found: {temp_dir}")
        return completed_tasks
    
    for workflow_dir in temp_dir.glob("workflow_*"):
        final_dir = workflow_dir / "output" / "final"
        if not final_dir.exists():
            continue
        
        # Check for JSON manifest
        manifest_files = list(final_dir.glob("workflow_*.json"))
        if not manifest_files:
            continue
        
        manifest_file = manifest_files[0]
        try:
            with open(manifest_file, 'r') as f:
                data = json.load(f)
                
            # Extract task_id from directory name
            task_id = workflow_dir.name
            video_path = data.get("generation", {}).get("video_path")
            
            if video_path:
                completed_tasks[task_id] = {
                    "task_id": task_id,
                    "video_path": video_path,
                    "manifest_data": data
                }
                logger.info(f"Found completed task: {task_id}")
        except Exception as e:
            logger.error(f"Error reading manifest {manifest_file}: {e}")
            continue
    
    return completed_tasks


def migrate_orphaned_projects():
    """
    Migrate orphaned projects by linking them to completed tasks.
    """
    project_manager = get_project_manager()
    
    # Find all projects
    projects_dir = Path("backend/projects")
    if not projects_dir.exists():
        logger.error("Projects directory not found")
        return
    
    # Get all project files
    project_files = list(projects_dir.glob("proj_*.json"))
    logger.info(f"Found {len(project_files)} project files")
    
    # Find completed workflow results
    completed_tasks = find_completed_workflow_results()
    logger.info(f"Found {len(completed_tasks)} completed tasks")
    
    updated_count = 0
    created_count = 0
    
    # Step 1: Link completed tasks to orphaned projects
    orphaned_projects = []
    for project_file in project_files:
        try:
            with open(project_file, 'r') as f:
                project_data = json.load(f)
            
            project_id = project_data.get("id")
            task_id = project_data.get("task_id")
            status = project_data.get("status")
            
            # Check if project is orphaned (no task_id) but pending
            if task_id is None and status == "pending":
                orphaned_projects.append({
                    "project_id": project_id,
                    "project_data": project_data,
                    "file_path": project_file
                })
                logger.warning(f"Found orphaned project: {project_id}")
        except Exception as e:
            logger.error(f"Error reading project file {project_file}: {e}")
            continue
    
    # Step 2: Try to match orphaned projects with completed tasks
    for orphaned_project in orphaned_projects:
        project_id = orphaned_project["project_id"]
        project_data = orphaned_project["project_data"]
        
        # Try to find a matching completed task
        # For now, we'll just use the first available completed task
        # In production, you might want better matching logic based on timestamps, etc.
        if completed_tasks:
            # Get first completed task
            task_id, task_result = next(iter(completed_tasks.items()))
            
            # Link project to task
            project_manager.update_project(project_id, UpdateProjectRequest(
                task_id=task_id
            ))
            
            # Update project with result data
            project_manager.update_project_from_task_result(
                project_id,
                video_path=task_result["video_path"],
                duration=task_result["manifest_data"].get("scenes", {}).get("total_duration"),
                scene_count=task_result["manifest_data"].get("scenes", {}).get("count"),
                character_count=task_result["manifest_data"].get("characters", {}).get("count")
            )
            
            # Update project status to completed
            project_manager.sync_task_status(project_id, ProjectStatus.COMPLETED, 100)
            
            logger.info(f"Linked orphaned project {project_id} to task {task_id}")
            updated_count += 1
            
            # Remove this task from completed_tasks so it's not reused
            del completed_tasks[task_id]
    
    # Step 3: Create projects for remaining orphaned completed tasks
    for task_id, task_result in completed_tasks.items():
        try:
            # Create a new project for this completed task
            project = project_manager.create_project(CreateProjectRequest(
                name=f"Migrated Project {task_id[:8]}",
                description=f"Auto-migrated from completed task {task_id}",
                video_type=VideoType.SHORT_DRAMA,
                mode=GenerationMode.FULL
            ))

            # Link project to task
            project_manager.update_project(project.id, UpdateProjectRequest(
                task_id=task_id
            ))

            # Update project with result data
            project_manager.update_project_from_task_result(
                project.id,
                video_path=task_result["video_path"],
                duration=task_result["manifest_data"].get("scenes", {}).get("total_duration"),
                scene_count=task_result["manifest_data"].get("scenes", {}).get("count"),
                character_count=task_result["manifest_data"].get("characters", {}).get("count")
            )

            # Update project status to completed
            project_manager.sync_task_status(project.id, ProjectStatus.COMPLETED, 100)

            logger.info(f"Created new project {project.id} for task {task_id}")
            created_count += 1
        except Exception as e:
            logger.error(f"Error creating project for task {task_id}: {e}")
            continue
    
    logger.info(f"Migration complete: {updated_count} orphaned projects updated, {created_count} new projects created")
    return updated_count, created_count


def main():
    """Main migration function"""
    logger.info("=" * 60)
    logger.info("Starting orphaned project migration")
    logger.info("=" * 60)
    
    updated, created = migrate_orphaned_projects()
    
    logger.info("=" * 60)
    logger.info(f"Migration completed successfully!")
    logger.info(f"  - Updated {updated} orphaned projects")
    logger.info(f"  - Created {created} new projects for completed tasks")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
