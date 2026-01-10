"""
Example: Using Global Progress Bar

This example demonstrates how to use the global progress bar display
that shows progress at the bottom of the screen with logs above.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from agents.orchestrator_agent import SimpleDramaGenerator
import logging

# Sample script
SAMPLE_SCRIPT = """
# 程序员的一天

## 角色
- 小明: 25岁的程序员，戴眼镜，穿格子衬衫

## 场景1：办公室 - 早晨
地点: 现代办公室
时间: 早晨
天气: 晴朗
氛围: 忙碌
镜头: 中景
运镜: 静止
风格: realistic
描述: 小明坐在电脑前，专注地敲击键盘

小明（专注|平静）：今天要完成这个功能模块。

## 场景2：办公室 - 下午
地点: 现代办公室
时间: 下午
天气: 晴朗
氛围: 紧张
镜头: 特写
运镜: 推进
风格: realistic
描述: 小明盯着屏幕，表情严肃

小明（焦虑|急促）：Bug又出现了！

## 场景3：办公室 - 傍晚
地点: 现代办公室
时间: 傍晚
天气: 晴朗
氛围: 轻松
镜头: 全景
运镜: 拉远
风格: realistic
描述: 小明伸了个懒腰，露出满意的笑容

小明（开心|轻松）：终于搞定了！
"""


async def main():
    """Main function with global progress bar"""
    print("=" * 80)
    print("Example: Drama Generation with Global Progress Bar")
    print("=" * 80)
    print()
    print("This example demonstrates the global progress bar feature:")
    print("- Progress bar is displayed at the bottom of the screen")
    print("- Logs are displayed above the progress bar")
    print("- Errors are properly shown in the log area")
    print()
    print("=" * 80)
    print()

    # Configuration with global progress bar enabled
    config = {
        # Enable global progress bar
        'enable_global_progress_bar': True,

        # Logging configuration
        'log_level': 'INFO',
        'log_file': './output/example_progress_bar.log',

        # Image generation settings
        'image': {
            'max_concurrent': 2,
            'width': 1280,
            'height': 720,
        },

        # Video generation settings
        'video': {
            'max_concurrent': 2,
            'fps': 24,
        },

        # Composer settings
        'composer': {
            'add_transitions': True,
            'transition_type': 'fade',
            'transition_duration': 0.5,
        },
    }

    # Create generator
    generator = SimpleDramaGenerator(config=config)

    try:
        # Generate video
        # Note: The progress callback is optional when using global progress bar
        # The global progress bar will be updated automatically
        video_path = await generator.generate(
            script_text=SAMPLE_SCRIPT,
            output_file="example_with_progress_bar.mp4",
            progress_callback=None  # Not needed with global progress bar
        )

        print()
        print("=" * 80)
        print(f"✓ Video generated successfully: {video_path}")
        print("=" * 80)

    except Exception as e:
        print()
        print("=" * 80)
        print(f"✗ Generation failed: {e}")
        print("=" * 80)
        logging.error(f"Generation error: {e}", exc_info=True)

    finally:
        await generator.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nExecution interrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        logging.error("Main execution error", exc_info=True)
