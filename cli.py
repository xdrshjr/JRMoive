#!/usr/bin/env python
"""
AI Drama Generation CLI

Unified command-line interface for managing and generating AI drama projects.
"""

import sys
import asyncio
import argparse
from pathlib import Path
from typing import Optional
import logging
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Load .env file to environment variables
# This must be done early so validators can read from os.getenv()
load_dotenv()

from core.project_manager import ProjectManager
from core.config_loader import load_yaml_config, apply_cli_overrides, ConfigLoadError
from core.runner import ProjectRunner
from core.errors import (
    ProjectError,
    format_error_for_cli,
)


# Version
__version__ = "1.0.0"


def setup_logging(level: str = "INFO"):
    """Setup basic logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='[%(levelname)s] %(message)s'
    )


def print_success(message: str):
    """Print success message"""
    print(f"✓ {message}")


def print_error(message: str):
    """Print error message"""
    print(f"✗ {message}", file=sys.stderr)


def print_info(message: str):
    """Print info message"""
    print(f"ℹ {message}")


def format_size(bytes: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.1f} TB"


# ==================== Commands ====================

def cmd_generate(args):
    """Generate drama from project"""
    setup_logging(args.log_level)

    try:
        # Initialize project manager
        pm = ProjectManager()

        # Load project
        project_path = Path(args.project_path)
        print_info(f"Loading project: {project_path}")

        config, abs_path = pm.load_project(project_path)

        # Apply CLI overrides
        if args.override:
            print_info(f"Applying {len(args.override)} configuration override(s)")
            config = apply_cli_overrides(config, args.override)

        # Override output filename if specified
        if args.output:
            config.output.filename = args.output

        # Validate project
        if args.dry_run:
            print_info("Performing dry-run validation...")

        is_valid, errors, warnings = pm.validate_full_project(
            abs_path,
            check_dependencies=not args.dry_run
        )

        if errors:
            print_error("Validation failed:")
            for error in errors:
                print_error(f"  - {error}")
            return 1

        if warnings:
            print_info("Warnings:")
            for warning in warnings:
                print_info(f"  - {warning}")

        print_success("Project validation passed")

        if args.dry_run:
            print_info("Dry-run complete. Use without --dry-run to generate.")
            return 0

        # Create runner
        runner = ProjectRunner(config, abs_path)

        # Progress callback
        def progress_callback(progress: float, message: str = ""):
            bar_length = 40
            filled = int(bar_length * progress / 100)
            bar = '█' * filled + '░' * (bar_length - filled)
            print(f"\r[{bar}] {progress:.0f}% - {message}", end='', flush=True)

        # Run generation
        print_info("Starting drama generation...")
        print()

        video_path = asyncio.run(runner.run(progress_callback))

        print()  # New line after progress bar
        print_success(f"Video generated: {video_path}")

        # Show metadata if available
        metadata_path = Path(video_path).with_suffix('.json')
        if metadata_path.exists():
            print_success(f"Metadata saved: {metadata_path}")

        return 0

    except ProjectError as e:
        print_error(str(e))
        return 1
    except ConfigLoadError as e:
        print_error(f"Configuration error: {e}")
        return 1
    except KeyboardInterrupt:
        print()
        print_info("Generation cancelled by user")
        return 130
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        logging.exception("Full traceback:")
        return 1


def cmd_init(args):
    """Initialize new project"""
    setup_logging("INFO")

    try:
        pm = ProjectManager()

        print_info(f"Creating project: {args.project_name}")

        # Optional script file
        script_file = Path(args.script) if args.script else None
        if script_file and not script_file.exists():
            print_error(f"Script file not found: {script_file}")
            return 1

        # Create project
        project_path = pm.create_project(
            project_name=args.project_name,
            template=args.template,
            script_file=script_file,
            description=args.description
        )

        print_success(f"Created project: {project_path}")
        print_success("Generated config.yaml from template")
        print_success("Created folder structure")
        print()
        print_info("Next steps:")
        print(f"  1. Add your script to {project_path / 'script.yaml'}")
        print(f"  2. Review config at {project_path / 'config.yaml'}")
        print(f"  3. Run: python cli.py generate {project_path}")

        return 0

    except ProjectError as e:
        print_error(str(e))
        return 1
    except Exception as e:
        print_error(f"Failed to create project: {e}")
        logging.exception("Full traceback:")
        return 1


def cmd_validate(args):
    """Validate project structure and configuration"""
    setup_logging("INFO")

    try:
        pm = ProjectManager()

        project_path = Path(args.project_path)
        print_info(f"Validating project: {project_path}")

        # Load and validate
        config, abs_path = pm.load_project(project_path)

        is_valid, errors, warnings = pm.validate_full_project(abs_path)

        # Show results
        print_success("Project structure valid")

        # Script info
        script_path = Path(config.script.file)
        if script_path.exists():
            size = script_path.stat().st_size
            print_success(f"Script file found: {script_path.name} ({format_size(size)})")

        # Config info
        print_success("Config schema valid")

        # API keys
        from core.validators import check_api_keys
        keys_valid, missing_keys = check_api_keys(config)
        if keys_valid:
            print_success(f"API keys configured: {config.image.service}, {config.video.service}")
        else:
            print_error("Missing API keys:")
            for key in missing_keys:
                print_error(f"  - {key}")

        # Character settings
        if config.characters.enable_references:
            if config.characters.reference_images:
                load_count = sum(
                    1 for c in config.characters.reference_images.values()
                    if c.mode == "load"
                )
                gen_count = sum(
                    1 for c in config.characters.reference_images.values()
                    if c.mode == "generate"
                )
                print_success(
                    f"Character references: {gen_count} generate, {load_count} load"
                )
            else:
                print_success("Character references: auto-generate")
        else:
            print_info("Character references: disabled")

        # Warnings
        if warnings:
            print()
            print_info("Warnings:")
            for warning in warnings:
                print_info(f"  - {warning}")

        # Errors
        if errors:
            print()
            print_error("Errors:")
            for error in errors:
                print_error(f"  - {error}")
            return 1

        print()
        print_success("Ready to generate!")

        return 0

    except ProjectError as e:
        print_error(str(e))
        return 1
    except Exception as e:
        print_error(f"Validation failed: {e}")
        logging.exception("Full traceback:")
        return 1


def cmd_list(args):
    """List all projects"""
    setup_logging("INFO")

    try:
        pm = ProjectManager()

        projects = pm.list_projects()

        if not projects:
            print_info("No projects found")
            print_info(f"Create a project: python cli.py init <project_name>")
            return 0

        print(f"\nFound {len(projects)} project(s):\n")

        for project in projects:
            name = project.get('name', 'Unknown')
            title = project.get('title', name)
            description = project.get('description', '')
            has_script = project.get('has_script', False)
            has_outputs = project.get('has_outputs', False)

            print(f"📁 {name}")
            if title != name:
                print(f"   Title: {title}")
            if description:
                print(f"   Description: {description}")

            status_parts = []
            if has_script:
                status_parts.append("✓ script")
            else:
                status_parts.append("✗ script")

            if has_outputs:
                status_parts.append("✓ outputs")
                if 'output_count' in project:
                    status_parts.append(f"({project['output_count']} video(s))")

            print(f"   Status: {' | '.join(status_parts)}")
            print(f"   Path: {project['path']}")
            print()

        return 0

    except Exception as e:
        print_error(f"Failed to list projects: {e}")
        logging.exception("Full traceback:")
        return 1


def cmd_generate_quick(args):
    """Generate video from pre-uploaded images (Quick Mode)"""
    setup_logging(args.log_level)

    try:
        # Validate images directory
        images_dir = Path(args.images_dir)
        if not images_dir.exists():
            print_error(f"Images directory not found: {images_dir}")
            return 1

        if not images_dir.is_dir():
            print_error(f"Path is not a directory: {images_dir}")
            return 1

        # Find all scene images
        print_info(f"Scanning for scene images in: {images_dir}")
        scene_images = sorted(images_dir.glob("scene_*.png")) + sorted(images_dir.glob("scene_*.jpg"))

        if not scene_images:
            print_error("No scene images found. Images must be named scene_001.png, scene_002.png, etc.")
            return 1

        print_success(f"Found {len(scene_images)} scene images")

        # Validate sequential naming
        scene_numbers = []
        for img_path in scene_images:
            # Extract number from scene_XXX.ext
            import re
            match = re.match(r'scene_(\d{3})\.(png|jpg)', img_path.name)
            if not match:
                print_error(f"Invalid image name format: {img_path.name}")
                print_info("Images must be named scene_001.png, scene_002.png, etc.")
                return 1
            scene_numbers.append(int(match.group(1)))

        # Check for sequential order
        expected = list(range(1, len(scene_numbers) + 1))
        if sorted(scene_numbers) != expected:
            print_error(f"Scene numbers must be sequential starting from 001")
            print_error(f"Expected: {expected}, Found: {sorted(scene_numbers)}")
            return 1

        # Build scene configurations
        from models.script_models import Scene

        scenes = []
        scene_image_paths = {}
        scene_params = {}

        for img_path in scene_images:
            scene_id = img_path.stem  # e.g., "scene_001"

            # Create minimal Scene object
            scene = Scene(
                scene_id=scene_id,
                location="Quick Mode Scene",
                time="day",
                description=f"Scene from {img_path.name}",
                characters=[],
                dialogues=[],
                duration=args.duration
            )
            scenes.append(scene)

            # Store image path
            scene_image_paths[scene_id] = str(img_path.absolute())

            # Store scene parameters
            scene_params[scene_id] = {
                'duration': args.duration,
                'prompt': args.prompt if args.prompt else None,
                'camera_motion': args.camera_motion if args.camera_motion else None,
                'motion_strength': args.motion_strength
            }

        print_success(f"Prepared {len(scenes)} scenes for video generation")

        # Create output directory
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize orchestrator
        from agents.orchestrator_agent import DramaGenerationOrchestrator

        orchestrator_config = {
            'video': {
                'service': 'veo3',
                'max_concurrent': 2,
                'fps': args.fps,
                'resolution': f"{args.width}x{args.height}",
                'motion_strength': args.motion_strength,
            },
            'composer': {
                'add_transitions': args.transitions,
                'transition_duration': 0.5,
                'fps': args.fps,
            },
            'enable_character_references': False,
        }

        orchestrator = DramaGenerationOrchestrator(
            agent_id="quick_cli_orchestrator",
            config=orchestrator_config,
            output_dir=output_dir
        )

        # Progress callback
        def progress_callback(progress: float, message: str = ""):
            bar_length = 40
            filled = int(bar_length * progress / 100)
            bar = '█' * filled + '░' * (bar_length - filled)
            print(f"\r[{bar}] {progress:.0f}% - {message}", end='', flush=True)

        # Run quick mode generation
        print_info("Starting quick mode video generation...")
        print()

        video_path = asyncio.run(orchestrator.execute_quick_mode(
            scenes_config=scenes,
            scene_image_paths=scene_image_paths,
            scene_params=scene_params,
            output_filename=args.output,
            progress_callback=progress_callback
        ))

        print()  # New line after progress bar
        print_success(f"Video generated: {video_path}")

        # Show metadata if available
        metadata_path = Path(video_path).with_suffix('.json')
        if metadata_path.exists():
            print_success(f"Metadata saved: {metadata_path}")

        return 0

    except Exception as e:
        print_error(f"Quick mode generation failed: {e}")
        logging.exception("Full traceback:")
        return 1


# ==================== Main ====================

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="AI Drama Generation CLI - Unified project management and generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create new project
  python cli.py init my_drama

  # Generate drama
  python cli.py generate projects/my_drama

  # Generate with custom log level
  python cli.py generate projects/my_drama --log-level DEBUG

  # Override configuration
  python cli.py generate projects/my_drama --override video.fps=60

  # Quick mode: Generate from images
  python cli.py quick-generate ./my_images --duration 7 --transitions

  # Quick mode with custom prompt
  python cli.py quick-generate ./my_images --prompt "Cinematic camera movement" --camera-motion pan

  # Validate project
  python cli.py validate projects/my_drama

  # List all projects
  python cli.py list
"""
    )

    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate drama from project')
    gen_parser.add_argument('project_path', help='Path to project folder')
    gen_parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )
    gen_parser.add_argument('--output', help='Override output filename')
    gen_parser.add_argument(
        '--override',
        action='append',
        help='Override config values (e.g., video.fps=60)',
        metavar='KEY=VALUE'
    )
    gen_parser.add_argument('--dry-run', action='store_true', help='Validate without generating')
    gen_parser.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    gen_parser.add_argument('--skip-characters', action='store_true', help='Skip character reference generation')
    gen_parser.set_defaults(func=cmd_generate)

    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize new project')
    init_parser.add_argument('project_name', help='Name of the project')
    init_parser.add_argument('--template', default='default', help='Template to use (default: default)')
    init_parser.add_argument('--script', help='Copy script from file')
    init_parser.add_argument('--description', help='Project description')
    init_parser.set_defaults(func=cmd_init)

    # Validate command
    val_parser = subparsers.add_parser('validate', help='Validate project structure')
    val_parser.add_argument('project_path', help='Path to project folder')
    val_parser.set_defaults(func=cmd_validate)

    # List command
    list_parser = subparsers.add_parser('list', help='List all projects')
    list_parser.set_defaults(func=cmd_list)

    # Quick generate command
    quick_parser = subparsers.add_parser(
        'quick-generate',
        help='Generate video from images (Quick Mode)'
    )
    quick_parser.add_argument('images_dir', help='Directory containing scene images (scene_001.png, scene_002.png, etc.)')
    quick_parser.add_argument(
        '--output',
        default='quick_mode.mp4',
        help='Output video filename (default: quick_mode.mp4)'
    )
    quick_parser.add_argument(
        '--output-dir',
        default='./output_quick',
        help='Output directory (default: ./output_quick)'
    )
    quick_parser.add_argument(
        '--duration',
        type=int,
        default=5,
        choices=range(1, 11),
        metavar='1-10',
        help='Default duration per scene in seconds (default: 5)'
    )
    quick_parser.add_argument(
        '--prompt',
        help='Optional prompt to apply to all scenes'
    )
    quick_parser.add_argument(
        '--camera-motion',
        choices=['static', 'pan', 'tilt', 'zoom'],
        help='Camera motion type (default: none)'
    )
    quick_parser.add_argument(
        '--motion-strength',
        type=float,
        default=0.6,
        help='Motion strength 0.0-1.0 (default: 0.6)'
    )
    quick_parser.add_argument(
        '--fps',
        type=int,
        default=30,
        help='Video FPS (default: 30)'
    )
    quick_parser.add_argument(
        '--width',
        type=int,
        default=1920,
        help='Video width (default: 1920)'
    )
    quick_parser.add_argument(
        '--height',
        type=int,
        default=1080,
        help='Video height (default: 1080)'
    )
    quick_parser.add_argument(
        '--transitions',
        action='store_true',
        help='Add transitions between scenes'
    )
    quick_parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )
    quick_parser.set_defaults(func=cmd_generate_quick)

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
