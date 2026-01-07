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

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

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
        print(f"  1. Add your script to {project_path / 'script.txt'}")
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

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
