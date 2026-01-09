"""
语言检测功能演示脚本

演示如何使用新的语言检测功能来优化中文和英文提示词
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.llm_service import LLMService, detect_language


async def demo_language_detection():
    """演示语言检测功能"""
    print("=" * 60)
    print("语言检测功能演示")
    print("=" * 60)
    print()

    # 测试用例
    test_cases = [
        {
            "name": "纯中文提示词",
            "prompt": "办公室，早晨，程序员小明坐在电脑前写代码"
        },
        {
            "name": "纯英文提示词",
            "prompt": "Office, morning, programmer sitting at computer coding"
        },
        {
            "name": "中文为主的混合提示词",
            "prompt": "办公室, morning, 程序员小明坐在电脑前coding"
        },
        {
            "name": "英文为主的混合提示词",
            "prompt": "Office, morning, programmer 小明 sitting at computer"
        }
    ]

    # 演示语言检测
    print("1. 语言检测测试")
    print("-" * 60)
    for case in test_cases:
        detected_lang = detect_language(case["prompt"])
        lang_name = "中文" if detected_lang == "zh" else "英文"
        print(f"\n测试用例: {case['name']}")
        print(f"提示词: {case['prompt']}")
        print(f"检测结果: {lang_name} ({detected_lang})")

    print("\n" + "=" * 60)
    print()

    # 演示提示词优化（需要配置API密钥）
    print("2. 提示词优化演示")
    print("-" * 60)
    print("\n注意: 此部分需要配置 fast_llm_api_key 才能运行")
    print("如果已配置API密钥，取消下面代码的注释即可测试\n")

    # 取消注释以下代码来测试实际的提示词优化
    """
    async with LLMService() as llm_service:
        for case in test_cases[:2]:  # 只测试前两个用例
            print(f"\n测试用例: {case['name']}")
            print(f"原始提示词: {case['prompt']}")

            optimized = await llm_service.optimize_prompt(
                original_prompt=case['prompt'],
                optimization_context="图片生成" if detect_language(case['prompt']) == "zh" else "image generation"
            )

            print(f"优化后提示词: {optimized}")
            print("-" * 60)
    """

    print("\n演示完成！")


if __name__ == "__main__":
    asyncio.run(demo_language_detection())
