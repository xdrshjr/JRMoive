"""
角色一致性评分功能使用示例

演示如何使用LLM评分系统来提高角色一致性
"""
import asyncio
from pathlib import Path
from agents.image_generator_agent import ImageGenerationAgent
from models.script_models import Scene, Character, Script, ShotType, CameraMovement
from utils.character_enhancer import CharacterDescriptionEnhancer
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_with_judging():
    """使用LLM评分的完整示例"""

    # 1. 创建角色
    character = Character(
        name="小明",
        description="25岁的年轻程序员",
        age=25,
        gender="male",
        appearance="黑框眼镜，短发，白色T恤"
    )

    # 2. 创建场景
    scenes = [
        Scene(
            scene_id="scene_001",
            location="办公室",
            time="白天",
            description="小明坐在电脑前专注地写代码",
            characters=["小明"],
            shot_type=ShotType.MEDIUM_SHOT,
            camera_movement=CameraMovement.STATIC,
            action="typing on keyboard"
        ),
        Scene(
            scene_id="scene_002",
            location="咖啡厅",
            time="下午",
            description="小明在咖啡厅里喝咖啡休息",
            characters=["小明"],
            shot_type=ShotType.CLOSE_UP,
            camera_movement=CameraMovement.STATIC,
            action="drinking coffee"
        ),
        Scene(
            scene_id="scene_003",
            location="会议室",
            time="下午",
            description="小明在会议室里向同事展示代码",
            characters=["小明"],
            shot_type=ShotType.LONG_SHOT,
            camera_movement=CameraMovement.PAN,
            action="presenting to colleagues"
        )
    ]

    # 3. 创建剧本
    script = Script(
        title="程序员的一天",
        author="AI编剧",
        description="展示程序员日常工作的短剧",
        characters=[character],
        scenes=scenes
    )

    # 4. 配置Agent（启用评分功能）
    config = {
        'enable_character_consistency_judge': True,  # 启用LLM评分
        'candidate_images_per_scene': 3,  # 每个场景生成3个候选
        'save_all_candidates': False,  # 不保存其他候选
        'max_concurrent': 2,  # 并发控制
        'width': 1920,
        'height': 1080,
        'enable_image_to_image': True,
        'reference_image_weight': 0.7
    }

    output_dir = Path("./output/examples/character_consistency")
    output_dir.mkdir(parents=True, exist_ok=True)

    agent = ImageGenerationAgent(
        agent_id="image_gen_with_judge",
        config=config,
        output_dir=output_dir
    )

    # 5. 准备角色参考数据（假设已有参考图）
    # 实际使用中，这些参考图应该是预先生成或提供的
    reference_data = {
        "小明": {
            "seed": 12345,
            "reference_images": [
                str(output_dir / "xiaoming_reference.png")  # 需要预先存在
            ]
        }
    }

    logger.info("=" * 60)
    logger.info("开始生成图片（启用LLM评分）")
    logger.info(f"场景数量: {len(scenes)}")
    logger.info(f"每场景候选数: {config['candidate_images_per_scene']}")
    logger.info(f"总计将生成: {len(scenes) * config['candidate_images_per_scene']} 张图片")
    logger.info("=" * 60)

    try:
        # 6. 执行生成（自动进行评分和选择）
        results = await agent.execute_concurrent(
            scenes=scenes,
            script=script,
            reference_data=reference_data
        )

        # 7. 输出结果
        logger.info("\n" + "=" * 60)
        logger.info("生成完成！评分结果：")
        logger.info("=" * 60)

        for result in results:
            logger.info(f"\n场景: {result['scene_id']}")
            logger.info(f"  最终图片: {result['image_path']}")

            if 'judge_score' in result:
                logger.info(f"  评分: {result['judge_score']}/100")
                logger.info(f"  选择: 候选 {result['candidate_index']}/{result['total_candidates']}")
                logger.info(f"  理由: {result['judge_reasoning'][:100]}...")

                if 'consistency_aspects' in result:
                    aspects = result['consistency_aspects']
                    logger.info(f"  详细评分:")
                    logger.info(f"    - 面部特征: {aspects.get('facial_features', 0)}/30")
                    logger.info(f"    - 发型: {aspects.get('hairstyle', 0)}/20")
                    logger.info(f"    - 服装: {aspects.get('clothing', 0)}/20")
                    logger.info(f"    - 整体气质: {aspects.get('overall_temperament', 0)}/15")
                    logger.info(f"    - 场景融合: {aspects.get('scene_integration', 0)}/15")
            else:
                logger.info(f"  (未启用评分)")

        logger.info("\n" + "=" * 60)
        logger.info("所有图片已保存到: " + str(output_dir))
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"生成失败: {e}", exc_info=True)

    finally:
        await agent.close()


async def example_without_judging():
    """不使用LLM评分的对比示例"""

    character = Character(
        name="小明",
        description="25岁的年轻程序员",
        age=25,
        gender="male",
        appearance="黑框眼镜，短发，白色T恤"
    )

    scene = Scene(
        scene_id="scene_001",
        location="办公室",
        time="白天",
        description="小明坐在电脑前专注地写代码",
        characters=["小明"],
        shot_type=ShotType.MEDIUM_SHOT,
        camera_movement=CameraMovement.STATIC
    )

    script = Script(
        title="程序员的一天",
        characters=[character],
        scenes=[scene]
    )

    # 配置Agent（禁用评分功能）
    config = {
        'enable_character_consistency_judge': False,  # 禁用评分
        'max_concurrent': 1,
        'width': 1920,
        'height': 1080
    }

    output_dir = Path("./output/examples/no_judging")
    output_dir.mkdir(parents=True, exist_ok=True)

    agent = ImageGenerationAgent(
        agent_id="image_gen_no_judge",
        config=config,
        output_dir=output_dir
    )

    logger.info("=" * 60)
    logger.info("开始生成图片（不使用评分）")
    logger.info("=" * 60)

    try:
        results = await agent.execute_concurrent(
            scenes=[scene],
            script=script
        )

        logger.info("\n生成完成！")
        logger.info(f"图片路径: {results[0]['image_path']}")

    finally:
        await agent.close()


async def compare_with_and_without_judging():
    """对比启用和不启用评分的效果"""

    logger.info("\n" + "=" * 80)
    logger.info("对比测试：启用评分 vs 不启用评分")
    logger.info("=" * 80)

    logger.info("\n[1/2] 不启用评分（快速模式）")
    logger.info("-" * 80)
    import time
    start = time.time()
    await example_without_judging()
    time_without = time.time() - start
    logger.info(f"耗时: {time_without:.2f}秒")

    logger.info("\n[2/2] 启用评分（高质量模式）")
    logger.info("-" * 80)
    start = time.time()
    await example_with_judging()
    time_with = time.time() - start
    logger.info(f"耗时: {time_with:.2f}秒")

    logger.info("\n" + "=" * 80)
    logger.info("对比结果:")
    logger.info(f"  不启用评分: {time_without:.2f}秒")
    logger.info(f"  启用评分: {time_with:.2f}秒")
    logger.info(f"  时间增加: {time_with/time_without:.2f}x")
    logger.info("=" * 80)


if __name__ == "__main__":
    # 选择要运行的示例
    import sys

    if len(sys.argv) > 1:
        mode = sys.argv[1]
    else:
        mode = "with_judging"

    if mode == "with_judging":
        asyncio.run(example_with_judging())
    elif mode == "without_judging":
        asyncio.run(example_without_judging())
    elif mode == "compare":
        asyncio.run(compare_with_and_without_judging())
    else:
        print("Usage: python example_character_consistency.py [with_judging|without_judging|compare]")
        print("Default: with_judging")
