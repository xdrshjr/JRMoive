"""Character reference generation agent"""
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from agents.base_agent import BaseAgent
from services.nano_banana_service import NanoBananaService
from models.script_models import Character
from utils.concurrency import ConcurrencyLimiter
import logging


class CharacterReferenceAgent(BaseAgent):
    """角色参考图生成Agent - 为角色生成多视图参考图以确保一致性"""

    def __init__(
        self,
        agent_id: str = "character_reference_generator",
        config: Dict[str, Any] = None,
        output_dir: Optional[Path] = None
    ):
        super().__init__(agent_id, config or {})
        self.output_dir = output_dir or Path("./output/character_references")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.service = NanoBananaService()
        self.logger = logging.getLogger(__name__)

        # 并发控制
        max_concurrent = self.config.get('max_concurrent', 2)
        self.limiter = ConcurrencyLimiter(max_concurrent)

        # 参考图配置
        self.reference_views = self.config.get('reference_views', [
            'front_view',
            'side_view',
            'close_up',
            'full_body'
        ])
        self.reference_size = self.config.get('reference_image_size', 1024)
        self.reference_cfg_scale = self.config.get('reference_cfg_scale', 8.0)
        self.reference_steps = self.config.get('reference_steps', 60)

    async def execute(self, characters: List[Character]) -> Dict[str, Dict[str, Any]]:
        """
        为角色列表生成参考图集

        Args:
            characters: 角色列表

        Returns:
            角色参考数据字典: {character_name: {view_name: image_path, seed: int}}
        """
        if not await self.validate_input(characters):
            raise ValueError("Invalid characters data")

        self.logger.info(f"Starting reference generation for {len(characters)} characters")

        reference_data = {}

        for character in characters:
            self.logger.info(f"Generating references for character: {character.name}")

            try:
                views = await self._generate_character_views(character)
                reference_data[character.name] = views
                self.logger.info(f"Successfully generated {len(views)-1} views for {character.name}")

            except Exception as e:
                self.logger.error(f"Failed to generate references for {character.name}: {e}")
                await self.on_error(e)
                # 继续处理其他角色，不中断整个流程
                reference_data[character.name] = {'error': str(e)}

        await self.on_complete(reference_data)
        return reference_data

    async def validate_input(self, characters: List[Character]) -> bool:
        """验证输入数据"""
        if not characters:
            self.logger.error("Characters list is empty")
            return False

        if not all(isinstance(char, Character) for char in characters):
            self.logger.error("Invalid character objects in list")
            return False

        return True

    async def _generate_character_views(self, character: Character) -> Dict[str, Any]:
        """
        为单个角色生成多个视图参考图

        Args:
            character: 角色对象

        Returns:
            视图数据字典: {view_name: image_path, 'seed': int}
        """
        # 生成角色专用seed
        char_seed = hash(character.name) % (2**32)

        # 构建基础提示词
        base_prompt = self._build_character_base_prompt(character)

        # 创建角色专用目录
        char_dir = self.output_dir / character.name.replace(" ", "_")
        char_dir.mkdir(parents=True, exist_ok=True)

        views = {'seed': char_seed}

        # 视图提示词模板
        view_prompts = {
            'front_view': f"{base_prompt}, front view, neutral expression, character reference sheet style, white background",
            'side_view': f"{base_prompt}, side profile view, neutral expression, character reference sheet style, white background",
            'close_up': f"{base_prompt}, close-up portrait, detailed facial features, professional headshot, neutral background",
            'full_body': f"{base_prompt}, full body view, standing pose, character reference sheet style, white background"
        }

        # 只生成配置中指定的视图
        for view_name in self.reference_views:
            if view_name not in view_prompts:
                self.logger.warning(f"Unknown view type: {view_name}, skipping")
                continue

            prompt = view_prompts[view_name]

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{character.name}_{view_name}_{timestamp}.png"
            save_path = char_dir / filename

            try:
                # 生成参考图（使用更高的质量参数）
                result = await self.service.generate_and_save(
                    prompt=prompt,
                    save_path=save_path,
                    width=self.reference_size,
                    height=self.reference_size,
                    quality='high',
                    seed=char_seed,  # 使用固定seed确保一致性
                    cfg_scale=self.reference_cfg_scale,  # 更高的引导强度
                    steps=self.reference_steps  # 更多推理步数
                )

                views[view_name] = result['image_path']
                self.logger.info(f"Generated {view_name} for {character.name}")

            except Exception as e:
                self.logger.error(f"Failed to generate {view_name} for {character.name}: {e}")
                views[view_name] = None

        return views

    def _build_character_base_prompt(self, character: Character) -> str:
        """
        构建角色基础提示词

        Args:
            character: 角色对象

        Returns:
            详细的角色描述提示词
        """
        prompt_parts = []

        # 角色名称
        prompt_parts.append(character.name)

        # 年龄和性别
        if character.age and character.gender:
            age_descriptor = self._get_age_descriptor(character.age)
            prompt_parts.append(f"{age_descriptor} {character.age}-year-old {character.gender}")
        elif character.gender:
            prompt_parts.append(character.gender)

        # 外貌特征（优先使用appearance字段）
        if character.appearance:
            prompt_parts.append(character.appearance)
        elif character.description:
            # 使用description作为后备
            prompt_parts.append(character.description)

        # 一致性关键词
        prompt_parts.extend([
            "consistent character design",
            "professional character reference",
            "high detail",
            "clear features",
            "8k quality"
        ])

        return ", ".join(prompt_parts)

    def _get_age_descriptor(self, age: int) -> str:
        """
        根据年龄获取描述性词汇

        Args:
            age: 年龄

        Returns:
            年龄段描述词
        """
        if age < 13:
            return "young child"
        elif age < 20:
            return "teenage"
        elif age < 30:
            return "young adult"
        elif age < 50:
            return "middle-aged"
        elif age < 70:
            return "mature"
        else:
            return "elderly"

    async def close(self):
        """关闭资源"""
        await self.service.close()
