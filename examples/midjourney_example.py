"""
Midjourney图片生成示例

演示如何使用MidjourneyService和ImageGenerationAgent生成高质量图片
"""
import asyncio
from pathlib import Path
from agents.image_generator_agent import ImageGenerationAgent
from services.midjourney_service import MidjourneyService
from models.script_models import Scene, ShotType, CameraMovement


async def example_1_direct_service():
    """示例1: 直接使用MidjourneyService"""
    print("=" * 50)
    print("示例1: 直接使用MidjourneyService")
    print("=" * 50)

    service = MidjourneyService(
        # API配置将从环境变量读取
        # 或者可以显式传入：
        # api_key="your_api_key",
        # base_url="https://api.kuai.host",
        bot_type="MID_JOURNEY",
        poll_interval=3.0
    )

    try:
        # 定义进度回调
        def on_progress(progress: str, status: str):
            print(f"  进度: {progress} | 状态: {status}")

        print("\n正在生成图片: 一只可爱的猫...")

        # 生成并保存图片
        result = await service.generate_and_save(
            prompt="a cute cat sitting on a windowsill, sunset lighting, digital art, highly detailed",
            save_path=Path("./output/examples/midjourney_cat.png"),
            progress_callback=on_progress
        )

        print(f"\n✓ 图片已保存到: {result['image_path']}")
        print(f"  任务ID: {result['task_id']}")

    except Exception as e:
        print(f"\n✗ 生成失败: {e}")

    finally:
        await service.close()


async def example_2_with_reference_image():
    """示例2: 使用垫图生成"""
    print("\n" + "=" * 50)
    print("示例2: 使用垫图（base64）生成")
    print("=" * 50)

    service = MidjourneyService()

    try:
        # 读取参考图片并转换为base64
        reference_image_path = Path("./examples/reference.png")

        if reference_image_path.exists():
            import base64

            with open(reference_image_path, 'rb') as f:
                image_data = f.read()
                base64_image = base64.b64encode(image_data).decode('utf-8')

            print("\n正在使用参考图生成...")

            result = await service.generate_and_save(
                prompt="same style, but a dog instead of cat",
                save_path=Path("./output/examples/midjourney_dog_ref.png"),
                base64_array=[base64_image]
            )

            print(f"\n✓ 图片已保存到: {result['image_path']}")
        else:
            print(f"\n⚠ 参考图不存在: {reference_image_path}")
            print("  跳过此示例")

    except Exception as e:
        print(f"\n✗ 生成失败: {e}")

    finally:
        await service.close()


async def example_3_batch_generation():
    """示例3: 使用ImageGenerationAgent批量生成"""
    print("\n" + "=" * 50)
    print("示例3: 使用ImageGenerationAgent批量生成场景图")
    print("=" * 50)

    # 创建多个场景
    scenes = [
        Scene(
            scene_id="scene_001",
            location="古老的城堡",
            time="夜晚",
            description="月光照耀下的神秘城堡，城墙上长满藤蔓",
            duration=3.0,
            shot_type=ShotType.LONG_SHOT,
            camera_movement=CameraMovement.DOLLY,
            visual_style="哥特式",
            color_tone="冷色调",
            atmosphere="神秘"
        ),
        Scene(
            scene_id="scene_002",
            location="城堡大厅",
            time="夜晚",
            description="华丽的水晶吊灯悬挂在高高的天花板上，发出柔和的光芒",
            duration=2.5,
            shot_type=ShotType.CLOSE_UP,
            camera_movement=CameraMovement.STATIC,
            visual_style="古典奢华",
            color_tone="暖色调",
            atmosphere="华丽"
        ),
        Scene(
            scene_id="scene_003",
            location="城堡阳台",
            time="黎明",
            description="远处的群山在晨曦中若隐若现",
            duration=4.0,
            shot_type=ShotType.MEDIUM_SHOT,
            camera_movement=CameraMovement.PAN,
            visual_style="浪漫主义",
            color_tone="柔和",
            atmosphere="宁静"
        )
    ]

    # 创建Agent，显式指定使用Midjourney
    agent = ImageGenerationAgent(
        service_type="midjourney",
        output_dir=Path("./output/examples/midjourney_scenes"),
        config={
            'max_concurrent': 2,  # 并发限制
            'width': 1920,
            'height': 1080
        }
    )

    try:
        print(f"\n正在生成 {len(scenes)} 个场景的图片...")

        # 定义进度回调
        async def on_progress(progress: float, message: str):
            print(f"  总体进度: {progress:.1f}% - {message}")

        # 批量生成
        results = await agent.execute_concurrent(
            scenes,
            progress_callback=on_progress
        )

        print("\n✓ 批量生成完成!")
        print("\n生成结果:")
        for i, result in enumerate(results, 1):
            print(f"\n  场景 {i}: {result['scene_id']}")
            print(f"    图片: {result['image_path']}")
            print(f"    提示词: {result['prompt'][:60]}...")

    except Exception as e:
        print(f"\n✗ 批量生成失败: {e}")

    finally:
        await agent.close()


async def example_4_niji_style():
    """示例4: 使用Niji风格（动漫风格）"""
    print("\n" + "=" * 50)
    print("示例4: 使用Niji Journey（动漫风格）")
    print("=" * 50)

    service = MidjourneyService(
        bot_type="NIJI_JOURNEY"  # 切换到Niji模式
    )

    try:
        print("\n正在生成动漫风格图片...")

        result = await service.generate_and_save(
            prompt="anime girl with blue hair, standing in cherry blossom garden, soft lighting, beautiful eyes, high quality anime art",
            save_path=Path("./output/examples/niji_anime_girl.png")
        )

        print(f"\n✓ 动漫风格图片已保存到: {result['image_path']}")

    except Exception as e:
        print(f"\n✗ 生成失败: {e}")

    finally:
        await service.close()


async def example_5_step_by_step():
    """示例5: 分步操作（提交、轮询、下载）"""
    print("\n" + "=" * 50)
    print("示例5: 分步操作演示")
    print("=" * 50)

    service = MidjourneyService()

    try:
        # 步骤1: 提交任务
        print("\n步骤1: 提交Imagine任务...")
        task_id = await service.submit_imagine(
            prompt="a fantasy castle on a floating island, clouds below, epic landscape"
        )
        print(f"  任务ID: {task_id}")

        # 步骤2: 手动轮询状态
        print("\n步骤2: 轮询任务状态...")
        for i in range(5):  # 最多查询5次作为示例
            await asyncio.sleep(3)
            task_info = await service.fetch_task(task_id)
            status = task_info.get('status')
            progress = task_info.get('progress', '0%')

            print(f"  查询 {i+1}: 状态={status}, 进度={progress}")

            if status == 'SUCCESS':
                print("\n  ✓ 任务完成!")

                # 步骤3: 下载图片
                print("\n步骤3: 下载生成的图片...")
                image_url = task_info.get('imageUrl')
                save_path = Path("./output/examples/floating_castle.png")

                downloaded_path = await service.download_image(image_url, save_path)
                print(f"  ✓ 图片已保存到: {downloaded_path}")
                break

            elif status in ['FAILURE', 'FAILED']:
                fail_reason = task_info.get('failReason', 'Unknown error')
                print(f"\n  ✗ 任务失败: {fail_reason}")
                break

    except Exception as e:
        print(f"\n✗ 操作失败: {e}")

    finally:
        await service.close()


async def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("Midjourney 图片生成完整示例")
    print("=" * 60)

    # 创建输出目录
    output_dir = Path("./output/examples")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 运行示例（根据需要选择）
    try:
        # 示例1: 基础用法
        await example_1_direct_service()

        # 示例2: 使用垫图（需要参考图）
        # await example_2_with_reference_image()

        # 示例3: 批量生成
        await example_3_batch_generation()

        # 示例4: Niji风格
        await example_4_niji_style()

        # 示例5: 分步操作
        await example_5_step_by_step()

    except KeyboardInterrupt:
        print("\n\n⚠ 用户中断")
    except Exception as e:
        print(f"\n\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("示例执行完成")
    print("=" * 60)


if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())
