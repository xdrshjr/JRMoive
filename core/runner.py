"""
Project Runner

Executes drama generation workflow with project-specific configuration.
"""

import os
import asyncio
import time
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from config.project_schema import ProjectConfig
from agents.orchestrator_agent import DramaGenerationOrchestrator
from core.metadata import generate_metadata, save_metadata
from core.errors import GenerationError, ScriptFileNotFoundError


class ProjectRunner:
    """Runs drama generation for a project"""

    def __init__(self, project_config: ProjectConfig, project_path: Path):
        """
        Initialize project runner

        Args:
            project_config: Project configuration
            project_path: Absolute path to project folder
        """
        self.project_config = project_config
        self.project_path = project_path
        self.orchestrator = None

        # Resolve paths
        self.project_config.resolve_paths(project_path)

        # Build orchestrator configuration
        self.orchestrator_config = self._build_orchestrator_config()

        # Track generation info for metadata
        self.generation_info: Dict[str, Any] = {
            "paths": {},
            "timing": {},
        }

        self.start_time: Optional[float] = None

    def _build_orchestrator_config(self) -> Dict[str, Any]:
        """
        Convert project config to orchestrator config format

        Returns:
            Configuration dictionary for DramaGenerationOrchestrator
        """
        config = self.project_config

        orchestrator_config = {
            # Image generation settings
            'image': {
                'service': config.image.service,
                'max_concurrent': config.image.max_concurrent,
                'width': config.image.width,
                'height': config.image.height,
                'cfg_scale': config.image.cfg_scale,
                'steps': config.image.steps,
                'enable_image_to_image': config.image.enable_image_to_image,
                'reference_weight': config.image.reference_weight,
            },

            # Video generation settings
            'video': {
                'service': config.video.service,
                'max_concurrent': config.video.max_concurrent,
                'fps': config.video.fps,
                'resolution': config.video.resolution,
                'motion_strength': config.video.motion_strength,
                'model': config.video.model,
            },

            # Video composition settings
            'composer': {
                'add_transitions': config.composer.add_transitions,
                'transition_type': config.composer.transition_type,
                'transition_duration': config.composer.transition_duration,
                'fps': config.composer.fps,
                'preset': config.composer.preset,
                'threads': config.composer.threads,
            },

            # Character reference settings
            'enable_character_references': config.characters.enable_references,
            'character_reference': {
                'reference_mode': config.characters.reference_mode,
                'art_style': config.characters.art_style,
            },

            # BGM settings
            'bgm_path': config.composer.bgm.file if config.composer.bgm.enabled else None,
            'bgm_volume': config.composer.bgm.volume if config.composer.bgm.enabled else 0.0,

            # Subtitles
            'add_subtitles': config.composer.subtitles.enabled,

            # Performance settings
            'max_concurrent_requests': config.performance.max_concurrent_requests,
            'enable_checkpoints': config.performance.enable_checkpoints,

            # Output directory (project-specific)
            'output_dir': config.output.directory,

            # Global progress bar
            'enable_global_progress_bar': config.enable_global_progress_bar,
        }

        return orchestrator_config

    def _prepare_character_references(self) -> Optional[Dict[str, Any]]:
        """
        Prepare character reference images configuration

        Returns:
            Dictionary mapping character names to reference configs, or None
        """
        if not self.project_config.characters.reference_images:
            return None

        character_images = {}

        for char_name, char_config in self.project_config.characters.reference_images.items():
            character_images[char_name] = {
                'mode': char_config.mode,
            }

            if char_config.mode == 'load' and char_config.images:
                # Already resolved to absolute paths in project_config
                character_images[char_name]['images'] = char_config.images
            elif char_config.mode == 'generate':
                if char_config.views:
                    character_images[char_name]['views'] = char_config.views

        return character_images if character_images else None

    def _setup_api_keys(self):
        """
        Set API keys from project config to environment variables

        This allows services to read API keys from the project config
        Priority: config.yaml > existing environment variables
        """
        api_keys_map = {
            'doubao_api_key': 'DOUBAO_API_KEY',
            'nano_banana_api_key': 'NANO_BANANA_API_KEY',
            'midjourney_api_key': 'MIDJOURNEY_API_KEY',
            'veo3_api_key': 'VEO3_API_KEY',
            'openai_api_key': 'OPENAI_API_KEY',
        }

        for config_key, env_key in api_keys_map.items():
            # Get value from config
            config_value = getattr(self.project_config.api_keys, config_key, None)

            if config_value:
                # Set to environment (overrides existing value)
                os.environ[env_key] = config_value
                # Don't log the actual key for security
                import logging
                logging.getLogger(__name__).debug(f"Set {env_key} from project config")

    async def run(self, progress_callback: Optional[Callable] = None) -> str:
        """
        Execute drama generation workflow

        Args:
            progress_callback: Optional progress callback function

        Returns:
            Path to generated video file

        Raises:
            ScriptFileNotFoundError: If script file doesn't exist
            GenerationError: If generation fails
        """
        self.start_time = time.time()

        try:
            # Set API keys from config to environment variables (if provided)
            self._setup_api_keys()

            # Load script
            script_path = Path(self.project_config.script.file)
            if not script_path.exists():
                raise ScriptFileNotFoundError(str(script_path))

            with open(script_path, 'r', encoding=self.project_config.script.encoding) as f:
                script_text = f.read()

            # Prepare character references
            character_images = self._prepare_character_references()

            # Create orchestrator with project-specific output directory
            output_dir = Path(self.project_config.output.directory)
            self.orchestrator = DramaGenerationOrchestrator(
                config=self.orchestrator_config,
                output_dir=output_dir,
                project_path=self.project_path
            )

            # Wrap progress callback to track timing
            wrapped_callback = self._wrap_progress_callback(progress_callback)

            # Execute generation
            video_path = await self.orchestrator.execute(
                script_text=script_text,
                output_filename=self.project_config.output.filename,
                progress_callback=wrapped_callback,
                character_images=character_images,
            )

            # Calculate total time
            total_time = time.time() - self.start_time
            self.generation_info['total_time'] = total_time

            # Generate and save metadata
            if self.project_config.output.metadata.get('enabled', True):
                await self._save_metadata(video_path)

            return video_path

        except ScriptFileNotFoundError:
            raise
        except Exception as e:
            raise GenerationError("execution", str(e))

    def _wrap_progress_callback(
        self,
        user_callback: Optional[Callable]
    ) -> Optional[Callable]:
        """
        Wrap user progress callback to track timing information

        Args:
            user_callback: User-provided progress callback

        Returns:
            Wrapped callback function
        """
        if not user_callback:
            return None

        async def wrapped(progress: float, message: str = ""):
            # Track stage timing
            if "parsed" in message.lower():
                self.generation_info['timing']['script_parsing'] = time.time() - self.start_time
                # Extract scene and character counts from message
                # Message format: "Script parsed: X scenes, Y characters"
                try:
                    parts = message.split(':')[1].split(',')
                    if len(parts) >= 2:
                        scene_count = int(parts[0].strip().split()[0])
                        char_count = int(parts[1].strip().split()[0])
                        self.generation_info['scene_count'] = scene_count
                        self.generation_info['character_count'] = char_count
                except:
                    pass

            elif "character references complete" in message.lower():
                self.generation_info['timing']['character_references'] = time.time() - self.start_time

            elif "images generated" in message.lower() or "image generation complete" in message.lower():
                self.generation_info['timing']['image_generation'] = time.time() - self.start_time
                elapsed = self.generation_info['timing']['image_generation'] - \
                         self.generation_info['timing'].get('character_references', 0)
                self.generation_info['image_generation_time'] = elapsed

            elif "videos generated" in message.lower() or "video generation complete" in message.lower():
                self.generation_info['timing']['video_generation'] = time.time() - self.start_time
                elapsed = self.generation_info['timing']['video_generation'] - \
                         self.generation_info['timing'].get('image_generation', 0)
                self.generation_info['video_generation_time'] = elapsed

            elif "video composed" in message.lower() or "composition complete" in message.lower():
                self.generation_info['timing']['composition'] = time.time() - self.start_time
                elapsed = self.generation_info['timing']['composition'] - \
                         self.generation_info['timing'].get('video_generation', 0)
                self.generation_info['composition_time'] = elapsed

            # Call user callback
            if asyncio.iscoroutinefunction(user_callback):
                await user_callback(progress, message)
            else:
                user_callback(progress, message)

        return wrapped

    async def _save_metadata(self, video_path: str) -> None:
        """
        Generate and save metadata

        Args:
            video_path: Path to generated video
        """
        try:
            # Generate metadata
            metadata = generate_metadata(
                project_config=self.project_config,
                video_path=Path(video_path),
                generation_info=self.generation_info
            )

            # Determine metadata file path
            video_path_obj = Path(video_path)
            metadata_format = self.project_config.output.metadata.get('format', 'json')
            metadata_ext = f".{metadata_format}"
            metadata_path = video_path_obj.with_suffix(metadata_ext)

            # Save metadata
            save_metadata(metadata, metadata_path, format=metadata_format)

            self.generation_info['paths']['metadata'] = str(metadata_path)

        except Exception as e:
            # Don't fail the entire generation if metadata saving fails
            import logging
            logging.error(f"Failed to save metadata: {e}")

    async def close(self):
        """Clean up resources"""
        if self.orchestrator:
            await self.orchestrator.close()


async def run_project(
    project_config: ProjectConfig,
    project_path: Path,
    progress_callback: Optional[Callable] = None
) -> str:
    """
    Convenience function to run a project

    Args:
        project_config: Project configuration
        project_path: Project folder path
        progress_callback: Progress callback

    Returns:
        Path to generated video
    """
    runner = ProjectRunner(project_config, project_path)
    try:
        return await runner.run(progress_callback)
    finally:
        await runner.close()
