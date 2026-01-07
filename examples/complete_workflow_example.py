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


# Sample script - Transmigration Cool Drama (穿越爽剧)
SAMPLE_SCRIPT = """
# 代码之神穿越记

作者: AI编剧
简介: 顶级程序员穿越古代，用现代知识碾压全场的爽文故事

## 角色
- 林枫: 28岁的天才程序员，冷静理智，穿越后附身在废材书生身上，眼神锐利，气质从容
- 王员外: 50岁的富商，傲慢势利，体态肥胖，满脸横肉
- 柳如烟: 20岁的才女，清冷高傲，绝美容貌，是王员外想要招为小妾的对象
- 县令: 45岁的地方官员，正直但有些迂腐，留着长须

## 场景1：破旧书房 - 穿越觉醒
地点: 古代，宋代，破旧的书房
时间: 清晨
天气: 阴沉
氛围: 昏暗压抑
镜头: 特写
运镜: 推进
风格: cinematic
色调: cool
描述: 昏暗的书房里，林枫从破旧的木床上醒来，眼神从迷茫变为锐利。四周是破败的家具和发霉的书籍

[音效@0.5：雷声隆隆]

林枫（震惊|低沉）：这...我穿越了？这具身体的记忆...原主竟然是个被人欺凌的废材书生？

[旁白|冷静]：顶级程序员林枫，意外穿越到古代，成为一个被全城嘲笑的废物。但他很快意识到，这是一个碾压的机会。

林枫（冷笑|自信）：既然来了，就让这个时代见识一下真正的智慧！

[音效@3.0：翻书声]

## 场景2：县衙门口 - 被刁难
地点: 古代，宋代，县衙大门外
时间: 上午
天气: 晴朗
氛围: 紧张对峙
镜头: 中景
运镜: 摇镜
风格: cinematic
色调: warm
描述: 县衙门口围满了看热闹的百姓。王员外趾高气扬地站在台阶上，指着林枫大笑。柳如烟站在一旁，冷眼旁观
动作: 王员外用扇子指着林枫，做出轻蔑的手势

王员外（嘲讽|尖锐）：就凭你这个废材？也想参加诗会？\n我看你连字都认不全吧！哈哈哈！

[音效：众人哄笑声]

[旁白]：原身因为参加诗会被羞辱，从此一蹶不振。但今天，一切都会不同。

林枫（淡然|平静）：是吗？那不如我们赌一场如何？

王员外（狂笑|嚣张）：赌？你拿什么赌？好！如果你能答对我的问题，我跪下给你道歉！

柳如烟（冷淡|好奇）：有点意思...这个废材，似乎变了？

## 场景3：县衙大堂 - 智慧碾压
地点: 古代，宋代，县衙大堂
时间: 上午
天气: 晴朗
氛围: 紧张刺激
镜头: 特写
运镜: 快速切换
风格: cinematic
色调: cool
描述: 大堂内挤满了人。县令坐在高位，王员外得意洋洋。林枫站在中央，面色从容
动作: 林枫随手在地上画出复杂的数学图形

县令（威严|平和）：既然要赌，本官来出题。请问，如何在不知道圆周率的情况下，测算这圆池的周长？

王员外（得意|阴险）：这种难题，他一个废材怎么可能...

林枫（冷笑|自信）：很简单。用绳子测量直径，再乘以三点一四一五九二六...\n这个数值，叫做圆周率。

[音效@2.0：倒吸凉气的声音]

县令（震惊|激动）：什么？！圆周率？你竟然知道如此精确的数值？

柳如烟（惊讶|赞叹）：不可思议...他真的算出来了？

王员外（慌张|结巴）：这、这不可能！你一定是作弊！

林枫（讥讽|霸气）：作弊？那再来一题。\n王员外，你可知地球是圆的？太阳系有八大行星？光速是每秒三十万公里？

[旁白|震撼]：降维打击！这就是现代知识对古代的碾压！

## 场景4：街道 - 美人倾心
地点: 古代，宋代，繁华的街道
时间: 傍晚
天气: 晴朗
氛围: 轻松浪漫
镜头: 中景
运镜: 跟踪
风格: cinematic
色调: warm
描述: 夕阳下的街道，柳如烟主动追上林枫。她的脸上第一次出现了少女般的羞涩

[音效@0.5：夜市喧闹声]

柳如烟（羞涩|温柔）：林公子，请留步。

林枫（平静|礼貌）：柳姑娘有何贵干？

柳如烟（认真|柔和）：方才在县衙，你说的那些...地球、行星、光速...\n这些都是真的吗？

林枫（微笑|自信）：当然。这个世界，比你想象的要大得多。

柳如烟（仰慕|轻声）：如烟从未见过如此博学之人。\n能否...能否请林公子收我为徒？

林枫（温和|坚定）：不必为徒。如果你愿意，我可以带你看看这个世界的真相。

[旁白|轻松]：美人倾心，强者得之。这就是穿越者的特权。

## 场景5：书房 - 新的征程
地点: 古代，宋代，焕然一新的书房
时间: 夜晚
天气: 晴朗
氛围: 雄心壮志
镜头: 全景
运镜: 缓慢拉远
风格: cinematic
色调: cool
描述: 书房已经整理一新，桌上摆满了纸张，上面画满了现代科技的草图。林枫站在窗前，眺望夜空
动作: 林枫手持毛笔，在纸上快速书写

[音效：毛笔书写声]

林枫（雄心|激昂）：王员外只是开始。\n接下来，我要改变这个时代！

[旁白|雄壮]：这只是序章。印刷术、火药、蒸汽机...现代文明即将在古代绽放！

林枫（霸气|坚定）：这个世界，终将因我而改变！

[音效@3.0：远处传来惊雷声]

[旁白|激昂]：一代传奇，就此开启！
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
