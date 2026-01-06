"""
Complete Drama Generation Workflow Example

This example demonstrates the full end-to-end workflow of generating
an AI drama from script to final video using the orchestrator.
"""

import sys
import os
from pathlib import Path

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    try:
        os.system('chcp 65001 > nul')
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except Exception:
        pass  # If it fails, fall back to ASCII characters

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from agents.orchestrator_agent import DramaGenerationOrchestrator, SimpleDramaGenerator
from utils.progress_monitor import ProgressInfo
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # 改为 DEBUG 以查看详细信息
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


# Sample script
SAMPLE_SCRIPT = """
# 时光倒流

作者: AI编剧
简介: 一个关于错过与遗憾的温情故事

## 角色
- 李明: 30岁的上班族，内向，带着淡淡的忧郁

## 场景1：咖啡馆
地点: 温馨的咖啡馆
时间: 白天
天气: 晴朗
氛围: 安静温馨
时长: 3.5
镜头: 特写
风格: cinematic
色调: warm
描述: 李明坐在窗边，手里拿着一张旧照片，陷入沉思

李明（沉思）："如果能回到过去，我一定不会错过那个机会。"

## 场景2：熟悉的街道
地点: 城市街道
时间: 傍晚
天气: 晴朗
氛围: 怀旧
时长: 4.0
镜头: 全景
运镜: 跟踪
风格: cinematic
色调: warm
描述: 李明走在熟悉的街道上，夕阳将他的影子拉得很长
动作: 缓慢行走，低头沉思

旁白："有些错过，一生只有一次。"

## 场景3：公园长椅
地点: 公园
时间: 夜晚
天气: 晴朗
氛围: 宁静
时长: 3.5
镜头: 中景
风格: cinematic
色调: cool
描述: 李明坐在长椅上，抬头看着星空

李明（释然）："或许，这就是命运的安排吧。"
"""


async def progress_callback(percent: float, message: str):
    """
    Progress callback function

    Args:
        percent: Progress percentage
        message: Progress message
    """
    # Display progress bar
    bar_length = 40
    filled = int(bar_length * percent / 100)

    # Try Unicode characters first, fall back to ASCII if encoding fails
    try:
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f"\r[{bar}] {percent:.1f}% - {message}", end='', flush=True)
    except UnicodeEncodeError:
        # Fallback to ASCII characters
        bar = '#' * filled + '-' * (bar_length - filled)
        print(f"\r[{bar}] {percent:.1f}% - {message}", end='', flush=True)

    if percent >= 100:
        print()  # New line when complete


async def example_basic_usage():
    """Basic usage example - simplest way to generate a drama"""
    print("=" * 80)
    print("Example 1: Basic Usage with SimpleDramaGenerator")
    print("=" * 80)

    # Create simple generator
    generator = SimpleDramaGenerator()

    try:
        # Generate from script text
        video_path = await generator.generate(
            script_text=SAMPLE_SCRIPT,
            output_file="basic_drama.mp4",
            progress_callback=progress_callback
        )

        print(f"\n[OK] Video generated successfully: {video_path}")

    except Exception as e:
        print(f"\n[ERROR] Generation failed: {e}")
        logger.error(f"Generation error: {e}", exc_info=True)

    finally:
        await generator.close()


async def example_advanced_usage():
    """Advanced usage example with custom configuration"""
    print("\n" + "=" * 80)
    print("Example 2: Advanced Usage with Custom Configuration")
    print("=" * 80)

    # Custom configuration
    config = {
        'image': {
            'max_concurrent': 3,
            'width': 1920,
            'height': 1080,
            'quality': 'high'
        },
        'video': {
            'max_concurrent': 2,
            'fps': 30,
            'resolution': '1920x1080',
            'motion_strength': 0.6
        },
        'composer': {
            'add_transitions': True,
            'transition_type': 'fade',
            'transition_duration': 0.5,
            'fps': 30,
            'preset': 'medium',
            'threads': 4,
            'bgm_volume': 0.3
        },
        'add_subtitles': False,
        # 'bgm_path': './assets/background_music.mp3'  # Uncomment if you have BGM
    }

    # Create orchestrator with config
    orchestrator = DramaGenerationOrchestrator(config=config)

    try:
        # Execute with progress tracking
        video_path = await orchestrator.execute(
            script_text=SAMPLE_SCRIPT,
            output_filename="advanced_drama.mp4",
            progress_callback=progress_callback
        )

        print(f"\n[OK] Video generated successfully: {video_path}")

        # Get task status
        status = await orchestrator.get_task_status()
        print(f"\nTask Status:")
        print(f"  - Task ID: {status['task_id']}")
        print(f"  - Status: {status['status']}")
        print(f"  - Elapsed Time: {status['elapsed_time']:.2f}s")

    except Exception as e:
        print(f"\n[ERROR] Generation failed: {e}")
        logger.error(f"Generation error: {e}", exc_info=True)

    finally:
        await orchestrator.close()


async def example_from_file():
    """Example of generating drama from a script file"""
    print("\n" + "=" * 80)
    print("Example 3: Generate from Script File")
    print("=" * 80)

    # Create sample script file
    script_file = Path("./examples/sample_scripts/demo_script.txt")
    script_file.parent.mkdir(parents=True, exist_ok=True)

    with open(script_file, 'w', encoding='utf-8') as f:
        f.write(SAMPLE_SCRIPT)

    print(f"Created sample script: {script_file}")

    # Create generator
    generator = SimpleDramaGenerator()

    try:
        # Generate from file
        video_path = await generator.generate_from_file(
            script_file=str(script_file),
            output_file="file_drama.mp4",
            progress_callback=progress_callback
        )

        print(f"\n[OK] Video generated successfully: {video_path}")

    except Exception as e:
        print(f"\n[ERROR] Generation failed: {e}")
        logger.error(f"Generation error: {e}", exc_info=True)

    finally:
        await generator.close()


async def example_with_checkpoint():
    """Example demonstrating checkpoint/resume capability"""
    print("\n" + "=" * 80)
    print("Example 4: Using Checkpoints for Resume Capability")
    print("=" * 80)

    from utils.checkpoint import CheckpointManager

    checkpoint_manager = CheckpointManager()
    task_id = "demo_task_with_checkpoint"

    print(f"Task ID: {task_id}")

    # Simulate saving checkpoints at different stages
    print("\nSimulating checkpoints:")

    # Stage 1: Parsing
    checkpoint_manager.save_checkpoint(
        task_id=task_id,
        stage="parsing",
        data={
            "scenes": 3,
            "duration": 30.0,
            "title": "时光倒流"
        }
    )
    print("  [OK] Saved checkpoint: parsing")

    # Stage 2: Image generation
    checkpoint_manager.save_checkpoint(
        task_id=task_id,
        stage="image_generation",
        data={
            "images_generated": 3,
            "image_paths": [
                "output/images/scene1.png",
                "output/images/scene2.png",
                "output/images/scene3.png"
            ]
        }
    )
    print("  [OK] Saved checkpoint: image_generation")

    # List checkpoints
    print(f"\nCheckpoints for task '{task_id}':")
    checkpoints = checkpoint_manager.list_checkpoints(task_id)
    for cp in checkpoints:
        print(f"  - {cp['stage']} @ {cp['timestamp']}")

    # Get resume stage
    resume_stage = checkpoint_manager.get_resume_stage(task_id)
    print(f"\nNext stage to execute: {resume_stage}")

    # Load specific checkpoint
    loaded = checkpoint_manager.load_checkpoint(task_id, "parsing")
    print(f"\nLoaded checkpoint data:")
    print(f"  - Scenes: {loaded['data']['scenes']}")
    print(f"  - Duration: {loaded['data']['duration']}s")
    print(f"  - Title: {loaded['data']['title']}")

    # Clean up
    checkpoint_manager.clear_checkpoints(task_id)
    print(f"\n[OK] Cleaned up checkpoints for task '{task_id}'")


async def example_progress_monitoring():
    """Example of detailed progress monitoring"""
    print("\n" + "=" * 80)
    print("Example 5: Detailed Progress Monitoring")
    print("=" * 80)

    from utils.progress_monitor import ProgressMonitor, ConsoleProgressMonitor

    # Create console progress monitor
    monitor = ConsoleProgressMonitor(total_steps=10, show_bar=True)

    print("Simulating task with progress monitoring:\n")

    # Simulate task execution
    for i in range(11):
        await monitor.update(i, f"Processing step {i}/10...")
        await asyncio.sleep(0.5)  # Simulate work

    # Get statistics
    print(f"\nStatistics:")
    print(f"  - Total elapsed time: {monitor.get_elapsed_time():.2f}s")
    print(f"  - Average speed: {monitor.get_average_speed():.2f}s/step")
    print(f"  - Completion: {monitor.get_completion_percentage():.1f}%")


async def example_task_queue():
    """Example of using task queue for parallel processing"""
    print("\n" + "=" * 80)
    print("Example 6: Parallel Task Processing with TaskQueue")
    print("=" * 80)

    from utils.task_queue import TaskQueue

    # Create task queue
    queue = TaskQueue(max_workers=3)
    await queue.start()

    print("Submitting tasks to queue...")

    # Define test task
    async def process_scene(scene_id: int):
        await asyncio.sleep(1)  # Simulate processing
        return f"Scene {scene_id} processed"

    # Submit multiple tasks
    tasks = []
    for i in range(5):
        task = await queue.submit(process_scene, i)
        tasks.append(task)
        print(f"  - Submitted task: {task.task_id}")

    # Wait for all tasks
    print("\nWaiting for tasks to complete...")
    await queue.wait_all(timeout=30.0)

    # Get results
    print("\nResults:")
    for task in tasks:
        result = await queue.get_result(task.task_id)
        print(f"  - {result}")

    # Get statistics
    stats = queue.get_statistics()
    print(f"\nQueue Statistics:")
    print(f"  - Total tasks: {stats['total_tasks']}")
    print(f"  - Completed: {stats['completed_tasks']}")
    print(f"  - Success rate: {stats['success_rate']:.1f}%")
    print(f"  - Average duration: {stats['average_duration']:.2f}s")

    await queue.stop()


async def main():
    """Run all examples"""
    print("\n" + "=" * 80)
    print("AI Drama Generation - Complete Workflow Examples")
    print("=" * 80)
    print("\nNote: Some examples are simulated and won't generate actual videos")
    print("      without proper API keys and configuration.")
    print("=" * 80)

    # Run examples

    # Example 1: Basic usage (requires API keys)
    await example_basic_usage()

    # Example 2: Advanced usage (requires API keys)
    # await example_advanced_usage()

    # Example 3: From file (requires API keys)
    # await example_from_file()

    # Example 4: Checkpoint management (simulation, no API required)
    # await example_with_checkpoint()

    # Example 5: Progress monitoring (simulation, no API required)
    # await example_progress_monitoring()

    # Example 6: Task queue (simulation, no API required)
    # await example_task_queue()

    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nExecution interrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        logger.error("Main execution error", exc_info=True)
