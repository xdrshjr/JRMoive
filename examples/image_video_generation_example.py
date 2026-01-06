"""
示例：图片和视频生成流程演示

演示如何使用ImageGenerationAgent和VideoGenerationAgent
从剧本场景生成图片和视频
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import logging

from agents.script_parser_agent import ScriptParserAgent
from agents.image_generator_agent import ImageGenerationAgent
from agents.video_generator_agent import VideoGenerationAgent


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def progress_callback(progress: float, message: str):
    """进度回调函数"""
    print(f"[{progress:.1f}%] {message}")


async def main():
    """主函数"""
    print("=" * 60)
    print("图片和视频生成示例")
    print("=" * 60)

    # 读取示例剧本
    script_path = Path("examples/sample_scripts/programmer_day.txt")

    if not script_path.exists():
        print(f"错误: 找不到剧本文件 {script_path}")
        return

    with open(script_path, 'r', encoding='utf-8') as f:
        script_text = f.read()

    # 步骤1: 解析剧本
    print("\n步骤1: 解析剧本...")
    print("-" * 60)

    parser = ScriptParserAgent()
    script = await parser.execute(script_text)

    print(f"剧本标题: {script.title}")
    print(f"场景数量: {len(script.scenes)}")
    print(f"总时长: {script.total_duration}秒")

    # 步骤2: 生成图片
    print("\n步骤2: 生成分镜图片...")
    print("-" * 60)

    # 配置图片生成参数
    image_config = {
        'max_concurrent': 3,  # 最大并发数
        'width': 1920,
        'height': 1080,
        'quality': 'high',
        'enable_rate_limit': False  # 示例中禁用速率限制
    }

    image_generator = ImageGenerationAgent(
        config=image_config,
        output_dir=Path("./output/images")
    )

    try:
        # 并发生成图片
        image_results = await image_generator.execute_concurrent(
            script.scenes,
            progress_callback=progress_callback
        )

        print(f"\n成功生成 {len(image_results)} 张图片:")
        for result in image_results:
            print(f"  - {result['scene_id']}: {result['image_path']}")

    finally:
        await image_generator.close()

    # 步骤3: 生成视频
    print("\n步骤3: 将图片转换为视频...")
    print("-" * 60)

    # 配置视频生成参数
    video_config = {
        'max_concurrent': 2,  # Veo3生成较慢，降低并发数
        'fps': 30,
        'resolution': '1920x1080',
        'motion_strength': 0.5
    }

    video_generator = VideoGenerationAgent(
        config=video_config,
        output_dir=Path("./output/videos")
    )

    try:
        # 生成视频片段
        video_results = await video_generator.execute(
            image_results,
            script.scenes
        )

        print(f"\n成功生成 {len(video_results)} 个视频片段:")
        for result in video_results:
            print(f"  - {result['scene_id']}: {result['video_path']} ({result['duration']}s)")

    finally:
        await video_generator.close()

    # 步骤4: 显示统计信息
    print("\n" + "=" * 60)
    print("生成完成!")
    print("=" * 60)

    total_duration = sum(r['duration'] for r in video_results)
    print(f"\n统计信息:")
    print(f"  场景数: {len(script.scenes)}")
    print(f"  图片数: {len(image_results)}")
    print(f"  视频片段数: {len(video_results)}")
    print(f"  总视频时长: {total_duration}秒")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
