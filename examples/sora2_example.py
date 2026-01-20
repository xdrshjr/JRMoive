"""
Sora2视频生成服务使用示例

本文件演示如何使用Sora2Service生成视频，包括：
1. 基础图片转视频
2. 使用风格参数
3. 角色一致性
4. 故事板模式
5. 错误处理
6. 使用工厂模式
7. 批量生成

运行要求：
- 已配置SORA2_API_KEY环境变量
- 准备好测试图片

运行方法：
    python examples/sora2_example.py
"""

import asyncio
from pathlib import Path
from services.sora2_service import Sora2Service
from services.video_service_factory import VideoServiceFactory
from backend.core.exceptions import ServiceException
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def example1_basic_usage():
    """示例1：基础图片转视频"""
    logger.info("=" * 60)
    logger.info("示例1：基础图片转视频")
    logger.info("=" * 60)

    # 注意：请确保图片文件存在，或者修改为实际的图片路径
    image_path = "examples/images/sample_scene.png"

    async with Sora2Service() as service:
        try:
            result = await service.image_to_video(
                image_path=image_path,
                duration=8,
                size="1280x720",
                prompt="A cat playing piano on stage"
            )

            logger.info(f"Video generated successfully!")
            logger.info(f"Task ID: {result['id']}")
            logger.info(f"Video URL: {result['video_url']}")

            # 下载视频
            save_path = Path("output/examples/basic_video.mp4")
            save_path.parent.mkdir(parents=True, exist_ok=True)

            await service.download_video(
                video_url=result['video_url'],
                save_path=save_path
            )
            logger.info(f"Video saved to: {save_path}")

        except ServiceException as e:
            logger.error(f"Video generation failed: {e.message}")
            logger.error(f"Error type: {e.error_type}, Retryable: {e.retryable}")
        except FileNotFoundError:
            logger.warning(f"Image file not found: {image_path}")
            logger.warning("Please create example images or modify the path")


async def example2_with_style():
    """示例2：使用风格参数（动漫风格）"""
    logger.info("=" * 60)
    logger.info("示例2：使用风格参数（动漫风格）")
    logger.info("=" * 60)

    image_path = "examples/images/sample_scene.png"

    async with Sora2Service() as service:
        try:
            result = await service.image_to_video(
                image_path=image_path,
                duration=8,
                size="1280x720",
                style="anime",  # 动漫风格
                prompt="A magical girl transformation scene"
            )

            save_path = Path("output/examples/anime_style_video.mp4")
            save_path.parent.mkdir(parents=True, exist_ok=True)

            await service.download_video(result['video_url'], save_path)
            logger.info(f"Anime style video saved to: {save_path}")

        except FileNotFoundError:
            logger.warning(f"Image file not found: {image_path}")


async def example3_character_consistency():
    """示例3：角色一致性"""
    logger.info("=" * 60)
    logger.info("示例3：角色一致性")
    logger.info("=" * 60)

    character_image = "examples/images/character_design.png"
    scene_image = "examples/images/scene_with_character.png"

    async with Sora2Service() as service:
        try:
            # 第一步：生成角色参考视频
            logger.info("Step 1: Generating character reference video...")
            ref_result = await service.image_to_video(
                image_path=character_image,
                duration=8,
                prompt="Character turnaround view, showing front, side, and back angles"
            )
            character_video_url = ref_result['video_url']
            logger.info(f"Character reference video: {character_video_url}")

            # 第二步：使用角色参考生成场景视频
            logger.info("Step 2: Generating scene video with character consistency...")
            result = await service.image_to_video(
                image_path=scene_image,
                duration=8,
                size="1280x720",
                character_url=character_video_url,
                character_timestamps="1,3",  # 角色在1-3秒出现
                prompt="The character walks into the room"
            )

            save_path = Path("output/examples/character_video.mp4")
            save_path.parent.mkdir(parents=True, exist_ok=True)

            await service.download_video(result['video_url'], save_path)
            logger.info(f"Character consistency video saved to: {save_path}")

        except FileNotFoundError as e:
            logger.warning(f"Image file not found: {e}")


async def example4_storyboard_mode():
    """示例4：故事板模式（多镜头）"""
    logger.info("=" * 60)
    logger.info("示例4：故事板模式（多镜头）")
    logger.info("=" * 60)

    # 故事板提示词（特殊格式）
    storyboard_prompt = """
Shot 1:
duration: 5sec
Scene: A cat sits in front of a piano on a stage

Shot 2:
duration: 5sec
Scene: The cat starts playing the piano with its paws

Shot 3:
duration: 5sec
Scene: The audience stands and applauds
"""

    image_path = "examples/images/stage_reference.png"

    async with Sora2Service() as service:
        try:
            result = await service.image_to_video(
                image_path=image_path,
                prompt=storyboard_prompt,
                duration=15,  # 总时长15秒
                size="1280x720"
            )

            save_path = Path("output/examples/storyboard_video.mp4")
            save_path.parent.mkdir(parents=True, exist_ok=True)

            await service.download_video(result['video_url'], save_path)
            logger.info(f"Storyboard video saved to: {save_path}")

        except FileNotFoundError:
            logger.warning(f"Image file not found: {image_path}")


async def example5_error_handling():
    """示例5：错误处理和重试"""
    logger.info("=" * 60)
    logger.info("示例5：错误处理和重试")
    logger.info("=" * 60)

    image_path = "examples/images/sample_scene.png"

    async with Sora2Service() as service:
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                result = await service.image_to_video(
                    image_path=image_path,
                    duration=8,
                    size="1280x720",
                    prompt="A peaceful garden scene"
                )

                logger.info("Video generated successfully!")
                save_path = Path("output/examples/retry_video.mp4")
                save_path.parent.mkdir(parents=True, exist_ok=True)

                await service.download_video(result['video_url'], save_path)
                logger.info(f"Video saved to: {save_path}")
                break

            except ServiceException as e:
                retry_count += 1
                logger.error(f"Attempt {retry_count} failed: {e.message}")
                logger.error(f"Error type: {e.error_type}")
                logger.error(f"Error code: {e.error_code}")

                # 检查是否可重试
                if not e.retryable:
                    logger.error("Error is not retryable, aborting...")
                    logger.error(f"Please check: {e.error_type}")
                    break

                if retry_count < max_retries:
                    wait_time = 2 ** retry_count  # 指数退避
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("Max retries reached, giving up...")

            except FileNotFoundError:
                logger.warning(f"Image file not found: {image_path}")
                break


async def example6_factory_pattern():
    """示例6：使用工厂模式创建服务"""
    logger.info("=" * 60)
    logger.info("示例6：使用工厂模式创建服务")
    logger.info("=" * 60)

    # 方式1：使用默认配置（从环境变量读取）
    service = VideoServiceFactory.create_service()
    logger.info(f"Created service using defaults: {type(service).__name__}")

    # 方式2：明确指定Sora2
    service = VideoServiceFactory.create_service(service_type="sora2")
    logger.info(f"Created Sora2 service explicitly: {type(service).__name__}")

    # 方式3：覆盖配置
    service = VideoServiceFactory.create_service(
        service_type="sora2",
        config_override={
            'model': 'sora-2-pro',
            'default_duration': 12,
            'default_style': 'anime'
        }
    )
    logger.info(f"Created Sora2 service with custom config")
    logger.info(f"Model: {service.model}, Style: {service.default_style}")

    # 使用服务
    image_path = "examples/images/sample_scene.png"

    async with service:
        try:
            result = await service.image_to_video(
                image_path=image_path,
                prompt="High quality cinematic video"
            )
            logger.info(f"Video generated: {result['id']}")

            save_path = Path("output/examples/factory_video.mp4")
            save_path.parent.mkdir(parents=True, exist_ok=True)

            await service.download_video(result['video_url'], save_path)
            logger.info(f"Video saved to: {save_path}")

        except FileNotFoundError:
            logger.warning(f"Image file not found: {image_path}")
        except ServiceException as e:
            logger.error(f"Video generation failed: {e.message}")


async def example7_multiple_images():
    """示例7：多图片模式（场景连续性）"""
    logger.info("=" * 60)
    logger.info("示例7：多图片模式（场景连续性）")
    logger.info("=" * 60)

    # 使用两张图片：第一张作为主参考，第二张用于连续性
    image_paths = [
        "examples/images/scene1.png",  # 前一场景的最后一帧
        "examples/images/scene2.png"   # 当前场景的参考图
    ]

    async with Sora2Service() as service:
        try:
            result = await service.image_to_video(
                image_path=image_paths,
                duration=8,
                size="1280x720",
                prompt="Smooth transition between scenes"
            )

            save_path = Path("output/examples/continuity_video.mp4")
            save_path.parent.mkdir(parents=True, exist_ok=True)

            await service.download_video(result['video_url'], save_path)
            logger.info(f"Scene continuity video saved to: {save_path}")

        except FileNotFoundError as e:
            logger.warning(f"Image file not found: {e}")


async def example8_batch_generation():
    """示例8：批量生成多个视频"""
    logger.info("=" * 60)
    logger.info("示例8：批量生成多个视频")
    logger.info("=" * 60)

    # 多个场景
    scenes = [
        {
            'image': 'examples/images/scene1.png',
            'prompt': 'A sunrise over the mountains',
            'style': 'nostalgic'
        },
        {
            'image': 'examples/images/scene2.png',
            'prompt': 'A bustling city street at night',
            'style': 'news'
        },
        {
            'image': 'examples/images/scene3.png',
            'prompt': 'A magical forest with glowing trees',
            'style': 'anime'
        }
    ]

    async with Sora2Service() as service:
        # 使用并发限制（Semaphore）避免过多并发请求
        semaphore = asyncio.Semaphore(2)  # 最多2个并发

        async def generate_one(scene, index):
            async with semaphore:
                try:
                    logger.info(f"Generating video {index + 1}/{len(scenes)}...")
                    result = await service.image_to_video(
                        image_path=scene['image'],
                        duration=8,
                        style=scene['style'],
                        prompt=scene['prompt']
                    )

                    save_path = Path(f"output/examples/batch_video_{index + 1}.mp4")
                    save_path.parent.mkdir(parents=True, exist_ok=True)

                    await service.download_video(result['video_url'], save_path)
                    logger.info(f"Video {index + 1} saved to: {save_path}")

                    return {'index': index, 'success': True, 'path': save_path}

                except FileNotFoundError:
                    logger.warning(f"Image not found: {scene['image']}")
                    return {'index': index, 'success': False, 'error': 'File not found'}
                except ServiceException as e:
                    logger.error(f"Video {index + 1} failed: {e.message}")
                    return {'index': index, 'success': False, 'error': e.message}

        # 并发生成所有视频
        tasks = [generate_one(scene, i) for i, scene in enumerate(scenes)]
        results = await asyncio.gather(*tasks)

        # 统计结果
        success_count = sum(1 for r in results if r['success'])
        logger.info(f"Batch generation completed: {success_count}/{len(scenes)} successful")


async def example9_all_styles():
    """示例9：测试所有支持的风格"""
    logger.info("=" * 60)
    logger.info("示例9：测试所有支持的风格")
    logger.info("=" * 60)

    image_path = "examples/images/sample_scene.png"

    # 所有支持的风格
    styles = Sora2Service.SUPPORTED_STYLES

    async with Sora2Service() as service:
        for style in styles:
            try:
                logger.info(f"Testing style: {style}")

                result = await service.image_to_video(
                    image_path=image_path,
                    duration=4,  # 使用最短时长加快测试
                    size="1280x720",
                    style=style,
                    prompt=f"A scene in {style} style"
                )

                save_path = Path(f"output/examples/style_{style}.mp4")
                save_path.parent.mkdir(parents=True, exist_ok=True)

                await service.download_video(result['video_url'], save_path)
                logger.info(f"Style {style} video saved to: {save_path}")

                # 避免API速率限制
                await asyncio.sleep(2)

            except FileNotFoundError:
                logger.warning(f"Image file not found: {image_path}")
                break
            except ServiceException as e:
                logger.error(f"Style {style} failed: {e.message}")


async def example10_duration_adjustment():
    """示例10：测试时长自动调整"""
    logger.info("=" * 60)
    logger.info("示例10：测试时长自动调整")
    logger.info("=" * 60)

    image_path = "examples/images/sample_scene.png"

    # 测试不同的时长值，观察自动调整
    test_durations = [3, 5, 7, 10, 15]

    async with Sora2Service() as service:
        for duration in test_durations:
            try:
                logger.info(f"\nTesting duration: {duration}s")

                result = await service.image_to_video(
                    image_path=image_path,
                    duration=duration,  # 会被自动调整
                    size="1280x720",
                    prompt="A peaceful scene"
                )

                logger.info(f"Duration {duration}s request completed successfully")
                # 注意查看日志中的WARNING信息，显示实际使用的时长

            except FileNotFoundError:
                logger.warning(f"Image file not found: {image_path}")
                break
            except ServiceException as e:
                logger.error(f"Duration {duration}s failed: {e.message}")


async def main():
    """运行所有示例"""
    logger.info("Sora2 Service Examples")
    logger.info("=" * 60)

    # 确保输出目录存在
    Path("output/examples").mkdir(parents=True, exist_ok=True)

    # 可以选择运行特定示例或运行所有示例
    # 注意：运行所有示例可能需要较长时间和API配额

    try:
        # 基础示例
        await example1_basic_usage()
        await asyncio.sleep(2)

        # 风格示例
        await example2_with_style()
        await asyncio.sleep(2)

        # 角色一致性（需要两张图片）
        # await example3_character_consistency()
        # await asyncio.sleep(2)

        # 故事板模式
        # await example4_storyboard_mode()
        # await asyncio.sleep(2)

        # 错误处理
        await example5_error_handling()
        await asyncio.sleep(2)

        # 工厂模式
        await example6_factory_pattern()
        await asyncio.sleep(2)

        # 多图片模式（需要两张图片）
        # await example7_multiple_images()
        # await asyncio.sleep(2)

        # 批量生成（需要多张图片）
        # await example8_batch_generation()
        # await asyncio.sleep(2)

        # 测试所有风格（需要较多API调用）
        # await example9_all_styles()

        # 时长调整测试
        await example10_duration_adjustment()

        logger.info("=" * 60)
        logger.info("Examples completed!")
        logger.info("=" * 60)

        logger.info("\nNote: Some examples are commented out because they require:")
        logger.info("  - Multiple image files")
        logger.info("  - More API quota")
        logger.info("Uncomment them if you have the required resources.")

    except Exception as e:
        logger.error(f"Example failed with unexpected error: {e}", exc_info=True)


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
