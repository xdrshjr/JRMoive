"""测试剧本解析Agent"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.script_parser_agent import ScriptParserAgent
from utils.storyboard_optimizer import StoryboardOptimizer


async def test_script_parser():
    """测试剧本解析功能"""

    # 读取示例剧本
    script_path = project_root / "examples" / "sample_scripts" / "programmer_day.txt"

    if not script_path.exists():
        print(f"错误：剧本文件不存在: {script_path}")
        return

    with open(script_path, 'r', encoding='utf-8') as f:
        script_text = f.read()

    print("=" * 60)
    print("开始测试剧本解析Agent")
    print("=" * 60)

    # 创建解析器
    parser = ScriptParserAgent()

    try:
        # 执行解析
        script = await parser.execute(script_text)

        # 输出解析结果
        print(f"\n✓ 剧本解析成功!")
        print(f"\n剧本信息:")
        print(f"  标题: {script.title}")
        print(f"  作者: {script.author}")
        print(f"  简介: {script.description}")
        print(f"  角色数量: {len(script.characters)}")
        print(f"  场景数量: {len(script.scenes)}")
        print(f"  总时长: {script.total_duration}秒")

        # 输出角色信息
        print(f"\n角色列表:")
        for char in script.characters:
            print(f"  - {char.name}: {char.description}")
            if char.age:
                print(f"    年龄: {char.age}")
            if char.gender:
                print(f"    性别: {char.gender}")

        # 输出场景详情
        print(f"\n场景详情:")
        for i, scene in enumerate(script.scenes, 1):
            print(f"\n  场景 {i} ({scene.scene_id}):")
            print(f"    地点: {scene.location}")
            print(f"    时间: {scene.time}")
            print(f"    镜头类型: {scene.shot_type.value}")
            print(f"    时长: {scene.duration}秒")
            print(f"    角色: {', '.join(scene.characters) if scene.characters else '无'}")

            if scene.dialogues:
                print(f"    对话:")
                for dialogue in scene.dialogues:
                    emotion = f"（{dialogue.emotion}）" if dialogue.emotion else ""
                    print(f"      {dialogue.character}{emotion}: {dialogue.content}")

            # 输出图片生成提示词
            print(f"    图片提示词: {scene.to_image_prompt()}")

        # 验证剧本
        errors = script.validate_script()
        if errors:
            print(f"\n⚠ 剧本验证警告:")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"\n✓ 剧本验证通过，无错误")

        # 测试分镜优化
        print("\n" + "=" * 60)
        print("测试分镜优化功能")
        print("=" * 60)

        # 优化镜头序列
        print("\n优化前的镜头序列:")
        for i, scene in enumerate(script.scenes, 1):
            print(f"  场景{i}: {scene.shot_type.value}")

        optimized_scenes = StoryboardOptimizer.optimize_shot_sequence(script.scenes)

        print("\n优化后的镜头序列:")
        for i, scene in enumerate(optimized_scenes, 1):
            print(f"  场景{i}: {scene.shot_type.value}")

        # 测试时长调整
        print("\n测试时长调整:")
        print(f"  当前总时长: {sum(s.duration for s in script.scenes)}秒")

        target_duration = 25.0
        adjusted_scenes = StoryboardOptimizer.adjust_scene_durations(
            script.scenes.copy(),
            target_duration
        )

        print(f"  目标总时长: {target_duration}秒")
        print(f"  调整后总时长: {sum(s.duration for s in adjusted_scenes):.2f}秒")

        # 测试摄像机动态
        print("\n测试摄像机动态:")
        dynamic_scenes = StoryboardOptimizer.add_camera_dynamics(script.scenes.copy())
        for i, scene in enumerate(dynamic_scenes, 1):
            print(f"  场景{i}: {scene.camera_movement.value}")

        print("\n" + "=" * 60)
        print("✓ 所有测试通过!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_simple_script():
    """测试简单剧本"""

    simple_script = """
# 测试剧本

## 角色
- 小明: 程序员

## 场景1：咖啡馆
地点: 咖啡馆
时间: 清晨
描述: 阳光洒满咖啡馆

小明（开心）：新的一天开始了！

## 场景2：办公室
地点: 办公室
时间: 下午
描述: 忙碌的工作场景
镜头: 特写
时长: 4.5

小明（专注）：继续工作吧。
    """

    print("\n" + "=" * 60)
    print("测试简单剧本解析")
    print("=" * 60)

    parser = ScriptParserAgent()

    try:
        script = await parser.execute(simple_script)

        print(f"\n✓ 简单剧本解析成功!")
        print(f"  标题: {script.title}")
        print(f"  场景数: {len(script.scenes)}")
        print(f"  总时长: {script.total_duration}秒")

        for scene in script.scenes:
            print(f"\n  {scene.scene_id}:")
            print(f"    提示词: {scene.to_image_prompt()}")

    except Exception as e:
        print(f"\n✗ 简单剧本测试失败: {e}")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_script_parser())
    asyncio.run(test_simple_script())
