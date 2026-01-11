"""Asset Manager for Workflow Assets

This module manages storage, retrieval, and cleanup of workflow-generated assets.
"""
import shutil
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timedelta

from backend.config import settings
from backend.utils.logger import get_logger
from backend.core.models import AssetsManifest, AssetInfo

logger = get_logger(__name__)


class AssetManager:
    """Manages workflow assets storage and retrieval"""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize asset manager
        
        Args:
            base_dir: Base directory for storing assets (default: backend/temp_projects)
        """
        if base_dir is None:
            # Use backend/temp_projects as default
            base_dir = Path(__file__).parent.parent / "temp_projects"
        
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"AssetManager initialized | base_dir={self.base_dir}")
    
    def get_task_directory(self, task_id: str) -> Path:
        """
        Get the directory for a specific task
        
        Args:
            task_id: Task identifier
            
        Returns:
            Path to task directory
        """
        task_dir = self.base_dir / task_id
        return task_dir
    
    def save_workflow_assets(
        self,
        task_id: str,
        project_path: Path,
        video_path: str,
        base_url: str = ""
    ) -> AssetsManifest:
        """
        Save workflow assets and create manifest
        
        Args:
            task_id: Task identifier
            project_path: Path to the project directory
            video_path: Path to the final video file
            base_url: Base URL for asset access (e.g., http://localhost:8000)
            
        Returns:
            AssetsManifest with all asset information
        """
        logger.info(f"AssetManager | Saving workflow assets | task_id={task_id} | project_path={project_path}")
        
        manifest = AssetsManifest()
        project_path = Path(project_path)
        
        # Character references
        char_ref_dir = project_path / "output" / "character_references"
        if char_ref_dir.exists():
            logger.debug(f"AssetManager | Scanning character references | dir={char_ref_dir}")
            for char_file in char_ref_dir.glob("*.png"):
                asset = self._create_asset_info(
                    char_file,
                    task_id,
                    "character_references",
                    base_url
                )
                manifest.character_references.append(asset)
                logger.debug(f"AssetManager | Added character reference | file={char_file.name}")
        
        # Scene images
        images_dir = project_path / "output" / "images"
        if images_dir.exists():
            logger.debug(f"AssetManager | Scanning scene images | dir={images_dir}")
            for img_file in images_dir.glob("*.png"):
                asset = self._create_asset_info(
                    img_file,
                    task_id,
                    "images",
                    base_url
                )
                manifest.scene_images.append(asset)
                logger.debug(f"AssetManager | Added scene image | file={img_file.name}")
        
        # Scene videos
        videos_dir = project_path / "output" / "videos"
        if videos_dir.exists():
            logger.debug(f"AssetManager | Scanning scene videos | dir={videos_dir}")
            for vid_file in videos_dir.glob("*.mp4"):
                asset = self._create_asset_info(
                    vid_file,
                    task_id,
                    "videos",
                    base_url
                )
                manifest.scene_videos.append(asset)
                logger.debug(f"AssetManager | Added scene video | file={vid_file.name}")
        
        # Final video
        video_path_obj = Path(video_path)
        if video_path_obj.exists():
            manifest.final_video = self._create_asset_info(
                video_path_obj,
                task_id,
                "final",
                base_url
            )
            logger.info(f"AssetManager | Added final video | file={video_path_obj.name}")
        else:
            logger.warning(f"AssetManager | Final video not found | path={video_path}")
        
        # Metadata file
        metadata_path = video_path_obj.with_suffix('.json')
        if metadata_path.exists():
            manifest.metadata_file = self._create_asset_info(
                metadata_path,
                task_id,
                "final",
                base_url
            )
            logger.debug(f"AssetManager | Added metadata file | file={metadata_path.name}")
        
        logger.info(
            f"AssetManager | Assets manifest created | "
            f"task_id={task_id} | "
            f"char_refs={len(manifest.character_references)} | "
            f"scene_imgs={len(manifest.scene_images)} | "
            f"scene_vids={len(manifest.scene_videos)} | "
            f"final_video={'yes' if manifest.final_video else 'no'}"
        )
        
        return manifest
    
    def _create_asset_info(
        self,
        file_path: Path,
        task_id: str,
        asset_type: str,
        base_url: str
    ) -> AssetInfo:
        """
        Create AssetInfo from a file
        
        Args:
            file_path: Path to the asset file
            task_id: Task identifier
            asset_type: Type of asset (character_references, images, videos, final)
            base_url: Base URL for asset access
            
        Returns:
            AssetInfo object
        """
        file_size = file_path.stat().st_size if file_path.exists() else 0
        file_ext = file_path.suffix.lower()
        
        # Determine file type
        if file_ext in ['.png', '.jpg', '.jpeg', '.webp']:
            file_type = 'image'
        elif file_ext in ['.mp4', '.avi', '.mov', '.webm']:
            file_type = 'video'
        elif file_ext in ['.json']:
            file_type = 'json'
        else:
            file_type = 'other'
        
        # Build URL
        url = f"{base_url}/api/v1/workflow/assets/{task_id}/{asset_type}/{file_path.name}"
        
        return AssetInfo(
            filename=file_path.name,
            url=url,
            size_bytes=file_size,
            type=file_type,
            path=str(file_path.absolute())
        )
    
    def get_asset_path(
        self,
        task_id: str,
        asset_type: str,
        filename: str
    ) -> Optional[Path]:
        """
        Get the path to a specific asset
        
        Args:
            task_id: Task identifier
            asset_type: Asset type (character_references, images, videos, final)
            filename: Asset filename
            
        Returns:
            Path to the asset file, or None if not found
        """
        task_dir = self.get_task_directory(task_id)
        
        # Map asset type to subdirectory
        if asset_type == "character_references":
            asset_path = task_dir / "output" / "character_references" / filename
        elif asset_type == "images":
            asset_path = task_dir / "output" / "images" / filename
        elif asset_type == "videos":
            asset_path = task_dir / "output" / "videos" / filename
        elif asset_type == "final":
            asset_path = task_dir / "output" / "final" / filename
        else:
            logger.warning(f"AssetManager | Unknown asset type | asset_type={asset_type}")
            return None
        
        if asset_path.exists():
            logger.debug(f"AssetManager | Asset found | path={asset_path}")
            return asset_path
        else:
            logger.debug(f"AssetManager | Asset not found | path={asset_path}")
            return None
    
    def cleanup_old_assets(self, max_age_hours: int = 24) -> int:
        """
        Clean up old workflow assets
        
        Args:
            max_age_hours: Maximum age in hours before cleanup
            
        Returns:
            Number of directories cleaned up
        """
        logger.info(f"AssetManager | Starting cleanup | max_age_hours={max_age_hours}")
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        try:
            for task_dir in self.base_dir.iterdir():
                if not task_dir.is_dir():
                    continue
                
                # Check directory modification time
                dir_mtime = datetime.fromtimestamp(task_dir.stat().st_mtime)
                
                if dir_mtime < cutoff_time:
                    try:
                        logger.debug(f"AssetManager | Cleaning up old task | task_id={task_dir.name} | age={(datetime.now() - dir_mtime).total_seconds() / 3600:.1f}h")
                        shutil.rmtree(task_dir)
                        cleaned_count += 1
                    except Exception as e:
                        logger.warning(f"AssetManager | Failed to cleanup task | task_id={task_dir.name} | error={e}")
            
            logger.info(f"AssetManager | Cleanup completed | cleaned={cleaned_count} directories")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"AssetManager | Cleanup failed | error={e}", exc_info=True)
            return cleaned_count
    
    def get_all_task_ids(self) -> List[str]:
        """
        Get all task IDs with assets
        
        Returns:
            List of task IDs
        """
        task_ids = []
        
        try:
            for task_dir in self.base_dir.iterdir():
                if task_dir.is_dir():
                    task_ids.append(task_dir.name)
        except Exception as e:
            logger.error(f"AssetManager | Failed to list tasks | error={e}")
        
        return task_ids
    
    def delete_task_assets(self, task_id: str) -> bool:
        """
        Delete all assets for a specific task
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if successful, False otherwise
        """
        task_dir = self.get_task_directory(task_id)
        
        if not task_dir.exists():
            logger.warning(f"AssetManager | Task directory not found | task_id={task_id}")
            return False
        
        try:
            logger.info(f"AssetManager | Deleting task assets | task_id={task_id}")
            shutil.rmtree(task_dir)
            logger.info(f"AssetManager | Task assets deleted successfully | task_id={task_id}")
            return True
        except Exception as e:
            logger.error(f"AssetManager | Failed to delete task assets | task_id={task_id} | error={e}", exc_info=True)
            return False


# Singleton instance
_asset_manager_instance: Optional[AssetManager] = None


def get_asset_manager() -> AssetManager:
    """
    Get the singleton AssetManager instance
    
    Returns:
        AssetManager instance
    """
    global _asset_manager_instance
    
    if _asset_manager_instance is None:
        _asset_manager_instance = AssetManager()
    
    return _asset_manager_instance

