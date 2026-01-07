"""Unit tests for character reference agent"""
import pytest
from pathlib import Path
from models.script_models import Character
from agents.character_reference_agent import CharacterReferenceAgent
from utils.character_enhancer import CharacterDescriptionEnhancer


@pytest.fixture
def sample_characters():
    """创建示例角色数据"""
    return [
        Character(
            name="小明",
            description="25岁的年轻程序员，戴眼镜，清秀",
            age=25,
            gender="male",
            appearance="黑框眼镜，短发，白色T恤"
        ),
        Character(
            name="小红",
            description="23岁的设计师，长发，活泼",
            age=23,
            gender="female",
            appearance="长黑发，大眼睛，蓝色连衣裙"
        )
    ]


@pytest.fixture
def sample_reference_data():
    """创建示例参考数据"""
    return {
        "小明": {
            "seed": 12345,
            "front_view": "output/character_references/小明/front.png",
            "side_view": "output/character_references/小明/side.png",
            "close_up": "output/character_references/小明/closeup.png",
            "full_body": "output/character_references/小明/full.png"
        },
        "小红": {
            "seed": 67890,
            "front_view": "output/character_references/小红/front.png",
            "side_view": "output/character_references/小红/side.png",
            "close_up": "output/character_references/小红/closeup.png",
            "full_body": "output/character_references/小红/full.png"
        }
    }


class TestCharacterReferenceAgent:
    """测试角色参考Agent"""

    @pytest.mark.asyncio
    async def test_validate_input_valid(self, sample_characters):
        """测试输入验证 - 有效输入"""
        agent = CharacterReferenceAgent()
        assert await agent.validate_input(sample_characters) is True

    @pytest.mark.asyncio
    async def test_validate_input_empty(self):
        """测试输入验证 - 空列表"""
        agent = CharacterReferenceAgent()
        assert await agent.validate_input([]) is False

    @pytest.mark.asyncio
    async def test_validate_input_invalid_type(self):
        """测试输入验证 - 无效类型"""
        agent = CharacterReferenceAgent()
        assert await agent.validate_input([{"name": "test"}]) is False

    def test_build_character_base_prompt(self, sample_characters):
        """测试角色基础提示词构建"""
        agent = CharacterReferenceAgent()
        prompt = agent._build_character_base_prompt(sample_characters[0])

        assert "小明" in prompt
        assert "25" in prompt or "25-year-old" in prompt
        assert "male" in prompt
        assert "黑框眼镜" in prompt or "短发" in prompt

    def test_get_age_descriptor(self):
        """测试年龄描述符"""
        agent = CharacterReferenceAgent()

        assert agent._get_age_descriptor(10) == "young child"
        assert agent._get_age_descriptor(15) == "teenage"
        assert agent._get_age_descriptor(25) == "young adult"
        assert agent._get_age_descriptor(40) == "middle-aged"
        assert agent._get_age_descriptor(65) == "mature"
        assert agent._get_age_descriptor(75) == "elderly"


class TestCharacterDescriptionEnhancer:
    """测试角色描述增强器"""

    def test_initialization(self, sample_reference_data):
        """测试初始化"""
        enhancer = CharacterDescriptionEnhancer(sample_reference_data)
        assert enhancer.reference_data == sample_reference_data

    def test_get_character_seed(self, sample_reference_data):
        """测试获取角色seed"""
        enhancer = CharacterDescriptionEnhancer(sample_reference_data)

        assert enhancer.get_character_seed("小明") == 12345
        assert enhancer.get_character_seed("小红") == 67890
        assert enhancer.get_character_seed("不存在的角色") is None

    def test_get_character_seeds(self, sample_reference_data):
        """测试获取多个角色的seeds"""
        enhancer = CharacterDescriptionEnhancer(sample_reference_data)

        seeds = enhancer.get_character_seeds(["小明", "小红"])
        assert seeds == [12345, 67890]

        seeds = enhancer.get_character_seeds(["小明", "不存在", "小红"])
        assert seeds == [12345, 67890]

    def test_blend_character_seeds(self, sample_reference_data):
        """测试seed混合"""
        enhancer = CharacterDescriptionEnhancer(sample_reference_data)

        # 单个角色
        blended = enhancer.blend_character_seeds(["小明"])
        assert blended == 12345

        # 多个角色
        blended = enhancer.blend_character_seeds(["小明", "小红"])
        assert blended is not None
        assert isinstance(blended, int)
        assert 0 <= blended < 2**32

        # 不存在的角色
        blended = enhancer.blend_character_seeds(["不存在"])
        assert blended is None

    def test_has_reference(self, sample_reference_data):
        """测试检查参考数据是否存在"""
        enhancer = CharacterDescriptionEnhancer(sample_reference_data)

        assert enhancer.has_reference("小明") is True
        assert enhancer.has_reference("小红") is True
        assert enhancer.has_reference("不存在") is False

    def test_get_reference_info(self, sample_reference_data):
        """测试获取参考信息"""
        enhancer = CharacterDescriptionEnhancer(sample_reference_data)

        info = enhancer.get_reference_info("小明")
        assert info is not None
        assert info["seed"] == 12345
        assert "front_view" in info

        info = enhancer.get_reference_info("不存在")
        assert info is None

    def test_build_character_description(self, sample_reference_data, sample_characters):
        """测试构建角色描述"""
        enhancer = CharacterDescriptionEnhancer(sample_reference_data)

        desc = enhancer._build_character_description(sample_characters[0], "小明")

        assert "小明" in desc
        assert "12345" in desc or "ref:12345" in desc  # seed信息
        assert "黑框眼镜" in desc or "短发" in desc or "白色T恤" in desc  # 外貌特征


class TestSceneToImagePromptEnhancement:
    """测试Scene.to_image_prompt()的增强功能"""

    def test_prompt_with_character_dict(self, sample_characters):
        """测试传入角色字典时的提示词生成"""
        from models.script_models import Scene, ShotType

        scene = Scene(
            scene_id="test_001",
            location="咖啡馆",
            time="上午",
            description="阳光明媚的咖啡馆",
            characters=["小明", "小红"],
            shot_type=ShotType.MEDIUM_SHOT
        )

        # 创建角色字典
        char_dict = {char.name: char for char in sample_characters}

        # 生成提示词
        prompt = scene.to_image_prompt(char_dict)

        # 验证包含角色详细信息
        assert "小明" in prompt
        assert "小红" in prompt
        assert "黑框眼镜" in prompt or "短发" in prompt  # 小明的外貌
        assert "长黑发" in prompt or "大眼睛" in prompt  # 小红的外貌
        assert "25 years old" in prompt or "25" in prompt
        assert "23 years old" in prompt or "23" in prompt

    def test_prompt_without_character_dict(self):
        """测试不传入角色字典时的提示词生成（向后兼容）"""
        from models.script_models import Scene, ShotType

        scene = Scene(
            scene_id="test_001",
            location="咖啡馆",
            time="上午",
            description="阳光明媚的咖啡馆",
            characters=["小明", "小红"],
            shot_type=ShotType.MEDIUM_SHOT
        )

        # 不传入角色字典
        prompt = scene.to_image_prompt()

        # 验证只包含角色名称
        assert "小明" in prompt
        assert "小红" in prompt
        # 不应包含详细外貌（因为没有传入字典）
        assert "characters:" in prompt.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
