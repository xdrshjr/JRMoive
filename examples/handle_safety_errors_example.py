"""
Example: Handling Content Safety Errors

This example demonstrates how to configure the system to gracefully handle
content safety errors from Veo3 or other generation services.

Features demonstrated:
1. Enable skip_failed_scenes mode
2. Continue workflow even when some scenes fail
3. Review which scenes were skipped
4. Generate final video with successful scenes only
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.orchestrator_agent import SimpleDramaGenerator
from config.settings import settings
from loguru import logger


async def example_with_error_handling():
    """
    Generate video with error handling enabled.

    If any scene fails due to content safety, it will be skipped
    and the workflow will continue with remaining scenes.
    """

    logger.info("=" * 80)
    logger.info("Example: Generate drama with safety error handling")
    logger.info("=" * 80)

    # Create generator with skip_failed_scenes enabled
    generator = SimpleDramaGenerator(
        config={
            'skip_failed_scenes': True,  # Main config
            'video_generator': {
                'skip_failed_scenes': True  # Video generator specific
            },
            'max_concurrent_requests': 2  # Limit concurrent requests
        }
    )

    # Sample script (intentionally includes potentially problematic content)
    script_content = """
标题: 测试安全过滤

场景1: 咖啡店 - 白天
中景镜头
明亮温馨的咖啡店，阳光透过窗户洒进来。小明坐在窗边，微笑着看书。
小明: "今天天气真好。"

场景2: 公园 - 下午
全景镜头
公园里人们在散步，小孩在玩耍，气氛轻松愉快。
旁白: "和平的下午时光。"

场景3: 城市街道 - 夜晚
特写镜头
霓虹灯闪烁的街道，人来人往。
旁白: "夜晚的城市充满活力。"
"""

    try:
        # Generate drama
        logger.info("Starting generation with error handling enabled...")
        video_path = await generator.generate(
            script_content=script_content,
            output_filename="test_with_error_handling.mp4"
        )

        logger.success(f"Video generated successfully: {video_path}")

        # Check if any scenes were skipped
        if hasattr(generator.orchestrator, 'video_results'):
            video_results = generator.orchestrator.video_results
            skipped_scenes = [
                r for r in video_results
                if r.get('skipped', False)
            ]

            if skipped_scenes:
                logger.warning(f"\n{len(skipped_scenes)} scene(s) were skipped due to errors:")
                for result in skipped_scenes:
                    logger.warning(
                        f"  - Scene {result['scene_id']}: {result.get('error', 'Unknown error')}"
                    )
                logger.info("\nSee docs/CONTENT_SAFETY_GUIDE.md for guidance on fixing these scenes")
            else:
                logger.success("All scenes processed successfully!")

        return video_path

    except Exception as e:
        logger.error(f"Generation failed completely: {e}")
        logger.info("If all scenes are failing, review your script for content policy violations")
        raise
    finally:
        await generator.close()


async def example_without_error_handling():
    """
    Generate video WITHOUT error handling.

    If any scene fails, the entire workflow will stop with an error.
    This is the default behavior.
    """

    logger.info("=" * 80)
    logger.info("Example: Generate drama without error handling (default)")
    logger.info("=" * 80)

    # Create generator with default config (skip_failed_scenes=False)
    generator = SimpleDramaGenerator()

    script_content = """
标题: 测试默认行为

场景1: 办公室 - 白天
中景镜头
现代化办公室，员工专注工作。
员工: "让我们开始会议吧。"
"""

    try:
        logger.info("Starting generation with default error handling...")
        video_path = await generator.generate(
            script_content=script_content,
            output_filename="test_default_behavior.mp4"
        )

        logger.success(f"Video generated successfully: {video_path}")
        return video_path

    except RuntimeError as e:
        if "UNSAFE_GENERATION" in str(e):
            logger.error(f"Content safety error: {e}")
            logger.info("\nTo handle this error gracefully:")
            logger.info("1. Enable skip_failed_scenes mode (see example_with_error_handling)")
            logger.info("2. Review and modify the problematic scene")
            logger.info("3. See docs/CONTENT_SAFETY_GUIDE.md for detailed guidance")
        else:
            logger.error(f"Generation failed: {e}")
        raise
    finally:
        await generator.close()


async def example_analyze_safety_errors():
    """
    Helper function to analyze which scenes are causing safety errors.

    Useful for debugging and identifying problematic content patterns.
    """

    logger.info("=" * 80)
    logger.info("Example: Analyze safety errors")
    logger.info("=" * 80)

    generator = SimpleDramaGenerator(
        config={
            'skip_failed_scenes': True,
            'video_generator': {
                'skip_failed_scenes': True
            }
        }
    )

    # Your script here
    script_content = """
标题: 分析测试

场景1: 咖啡店 - 白天
中景镜头
温馨的咖啡店场景。
角色A: "你好。"

场景2: 公园 - 下午
全景镜头
公园里的休闲场景。
角色B: "天气真好。"
"""

    try:
        logger.info("Generating with all scenes...")
        await generator.generate(
            script_content=script_content,
            output_filename="analysis_test.mp4"
        )

        # Analyze results
        if hasattr(generator.orchestrator, 'video_results'):
            results = generator.orchestrator.video_results

            total = len(results)
            successful = len([r for r in results if not r.get('skipped', False)])
            failed = total - successful

            logger.info(f"\n=== Generation Summary ===")
            logger.info(f"Total scenes: {total}")
            logger.info(f"Successful: {successful} ({successful/total*100:.1f}%)")
            logger.info(f"Failed: {failed} ({failed/total*100:.1f}%)")

            if failed > 0:
                logger.warning("\nFailed scenes:")
                for r in results:
                    if r.get('skipped', False):
                        logger.warning(
                            f"  - {r['scene_id']}: "
                            f"{r.get('error', 'Unknown error')}"
                        )

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise
    finally:
        await generator.close()


async def main():
    """Run all examples"""

    print("\n" + "=" * 80)
    print("CONTENT SAFETY ERROR HANDLING EXAMPLES")
    print("=" * 80)
    print("\nThese examples show how to handle content safety errors from")
    print("Veo3 and other generation services.")
    print("\nExamples:")
    print("1. With error handling (recommended)")
    print("2. Without error handling (default)")
    print("3. Analyze safety errors")
    print("\nSee docs/CONTENT_SAFETY_GUIDE.md for detailed guidance.")
    print("=" * 80)

    # Example 1: With error handling (recommended for production)
    try:
        await example_with_error_handling()
    except Exception as e:
        logger.error(f"Example 1 failed: {e}")

    # Example 2: Without error handling (default behavior)
    try:
        await example_without_error_handling()
    except Exception as e:
        logger.error(f"Example 2 failed (expected if content is flagged): {e}")

    # Example 3: Analyze safety errors
    try:
        await example_analyze_safety_errors()
    except Exception as e:
        logger.error(f"Example 3 failed: {e}")

    print("\n" + "=" * 80)
    print("Examples completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
