"""
豆包（Doubao）图生图示例

演示如何使用豆包API进行角色参考图生成和基于参考图的场景图生成
"""
import asyncio
from pathlib import Path
from config.settings import settings
from agents.character_reference_agent import CharacterReferenceAgent
from agents.image_generator_agent import ImageGenerationAgent
from models.script_models import Character, Scene, Script


async def example_doubao_workflow():
    """完整的豆包工作流示例：角色参考图生成 + 场景图生图"""

    # 1. 创建角色
    characters = [
        Character(
            name="李明",
            age=28,
            gender="male",
            appearance="短发，戴眼镜，穿白色T恤和牛仔裤，清秀的面容",
            description="一名程序员，热爱编程"
        ),
        Character(
            name="王芳",
            age=26,
            gender="female",
            appearance="长发，穿连衣裙，温柔的笑容",
            description="一名设计师"
        )
    ]

    # 2. 生成角色参考图（单张多视角）
    print("\n=== 步骤 1: 生成角色参考图 ===")
    reference_agent = CharacterReferenceAgent(
        config={
            'character_reference_mode': 'single_multi_view',  # 单张多视角模式
            'reference_image_size': 1024,
            'reference_cfg_scale': 8.0,
            'reference_steps': 60,
            'enable_image_to_image': True,
            'image_service_type': 'doubao'  # 使用豆包
        }
    )

    try:
        reference_data = await reference_agent.execute(characters)

        print("\n角色参考图生成结果:")
        for char_name, data in reference_data.items():
            if 'error' in data:
                print(f"  {char_name}: 生成失败 - {data['error']}")
            else:
                print(f"  {char_name}:")
                print(f"    - 参考图: {data.get('reference_image')}")
                print(f"    - Seed: {data.get('seed')}")
                print(f"    - 模式: {data.get('mode')}")

        # 3. 创建测试场景
        print("\n=== 步骤 2: 生成场景图（图生图） ===")
        scenes = [
            Scene(
                scene_id="scene_001",
                location="办公室",
                time="白天",
                characters=["李明"],
                action="李明坐在电脑前专注地写代码",
                shot_type="MEDIUM_SHOT",
                duration=5
            ),
            Scene(
                scene_id="scene_002",
                location="咖啡厅",
                time="下午",
                characters=["李明", "王芳"],
                action="李明和王芳在咖啡厅讨论项目",
                shot_type="FULL_SHOT",
                duration=6
            )
        ]

        # 4. 使用参考图生成场景图（图生图）
        script = Script(
            title="测试剧本",
            characters=characters,
            scenes=scenes
        )

        image_agent = ImageGenerationAgent(
            config={
                'width': 1920,
                'height': 1080,
                'cfg_scale': 7.5,
                'steps': 50,
                'enable_image_to_image': True,  # 启用图生图
                'reference_image_weight': 0.7,   # 参考图权重
                'max_concurrent': 2,
                'image_service_type': 'doubao'  # 使用豆包
            }
        )

        # 设置参考数据
        results = await image_agent.execute_concurrent(
            scenes=scenes,
            script=script,
            reference_data=reference_data
        )

        print("\n场景图生成结果:")
        for result in results:
            scene_id = result.get('scene_id')
            image_path = result.get('image_path')
            reference_image = result.get('reference_image')

            print(f"\n  场景 {scene_id}:")
            print(f"    - 图片路径: {image_path}")
            print(f"    - 使用参考图: {reference_image or '未使用'}")
            print(f"    - 提示词: {result.get('prompt')[:100]}...")

        print("\n=== 完成！===")
        print(f"角色参考图保存在: ./output/character_references/")
        print(f"场景图保存在: ./output/images/")

    finally:
        await reference_agent.close()
        await image_agent.close()


async def example_compare_services():
    """对比豆包和Nano Banana两种服务"""

    character = Character(
        name="测试角色",
        age=25,
        gender="female",
        appearance="短发，现代装扮",
        description="测试角色"
    )

    # 使用豆包生成
    print("\n=== 使用豆包服务 ===")
    doubao_agent = CharacterReferenceAgent(
        config={
            'character_reference_mode': 'single_multi_view',
            'image_service_type': 'doubao'
        }
    )

    try:
        doubao_results = await doubao_agent.execute([character])
        print(f"豆包结果: {doubao_results}")
    finally:
        await doubao_agent.close()

    # 使用Nano Banana生成（如果配置了）
    if settings.nano_banana_api_key:
        print("\n=== 使用Nano Banana服务 ===")
        nano_agent = CharacterReferenceAgent(
            config={
                'character_reference_mode': 'multiple_single_view',
                'image_service_type': 'nano_banana'
            }
        )

        try:
            nano_results = await nano_agent.execute([character])
            print(f"Nano Banana结果: {nano_results}")
        finally:
            await nano_agent.close()


async def example_image_to_image_only():
    """仅演示图生图功能"""
    from services.doubao_service import DoubaoService

    service = DoubaoService()

    try:
        # 假设已有角色参考图
        reference_image_path = "./output/character_references/李明/李明_reference_sheet.png"

        # 检查文件是否存在
        if not Path(reference_image_path).exists():
            print(f"参考图不存在: {reference_image_path}")
            print("请先运行 example_doubao_workflow() 生成参考图")
            return

        # 使用参考图生成新场景
        print("\n=== 图生图示例 ===")
        result = await service.generate_and_save(
            prompt="Based on the character in the reference image, the character is walking in a park, sunny day, full body shot",
            save_path=Path("./output/images/test_image_to_image.png"),
            reference_image=reference_image_path,
            reference_image_weight=0.7,
            width=1920,
            height=1080
        )

        print(f"图生图结果:")
        print(f"  - 图片路径: {result['image_path']}")
        print(f"  - 参考图: {result['reference_image']}")

    finally:
        await service.close()


if __name__ == "__main__":
    # 确保配置了豆包API key
    if not settings.doubao_api_key or settings.doubao_api_key == "your_doubao_api_key_here":
        print("错误: 请在 .env 文件中配置 DOUBAO_API_KEY")
        print("复制 .env.example 为 .env 并填入您的API密钥")
        exit(1)

    print("豆包图生图示例")
    print("=" * 50)

    # 运行示例
    asyncio.run(example_doubao_workflow())

    # 可选：运行其他示例
    # asyncio.run(example_compare_services())
    # asyncio.run(example_image_to_image_only())
