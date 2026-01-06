"""
Project initialization script
Creates necessary directories and validates setup
"""
import os
from pathlib import Path


def create_project_structure():
    """创建项目目录结构"""

    dirs = [
        "agents",
        "services",
        "utils",
        "config",
        "models",
        "tests/test_agents",
        "tests/test_services",
        "tests/test_integration",
        "examples/sample_scripts",
        "output/images",
        "output/videos",
        "temp",
        "logs"
    ]

    print("Creating project directories...")
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"  [OK] {dir_path}")

    # Create __init__.py files
    print("\nCreating __init__.py files...")
    python_modules = [
        "agents",
        "services",
        "utils",
        "config",
        "models",
        "tests",
        "tests/test_agents",
        "tests/test_services",
        "tests/test_integration"
    ]

    for module in python_modules:
        init_file = Path(module) / "__init__.py"
        if not init_file.exists():
            init_file.write_text(f'"""{module} module"""\n')
            print(f"  [OK] {init_file}")

    print("\n[SUCCESS] Project structure created successfully!")


def check_environment():
    """检查环境配置"""
    print("\nChecking environment...")

    # Check .env file
    if not Path(".env").exists():
        print("  [WARNING] .env file not found. Please copy .env.example to .env and configure it.")
    else:
        print("  [OK] .env file exists")

    # Check Python version
    import sys
    python_version = sys.version_info
    if python_version.major >= 3 and python_version.minor >= 9:
        print(f"  [OK] Python version: {python_version.major}.{python_version.minor}")
    else:
        print(f"  [WARNING] Python version {python_version.major}.{python_version.minor} detected. Python 3.9+ recommended.")


def main():
    """主函数"""
    print("=" * 60)
    print("AI Drama Generator - Project Initialization")
    print("=" * 60)

    create_project_structure()
    check_environment()

    print("\n" + "=" * 60)
    print("Next steps:")
    print("  1. Copy .env.example to .env")
    print("  2. Configure API keys in .env")
    print("  3. Install dependencies: pip install -r requirements.txt")
    print("  4. Start development!")
    print("=" * 60)


if __name__ == "__main__":
    main()
