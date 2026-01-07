"""Character description enhancer for scene consistency"""
from typing import Dict, Any, Optional, List
from models.script_models import Scene, Character
import logging


class CharacterDescriptionEnhancer:
    """角色描述增强器 - 基于参考数据增强场景提示词以保持一致性"""

    def __init__(self, reference_data: Dict[str, Dict[str, Any]]):
        """
        初始化增强器

        Args:
            reference_data: 角色参考数据 {character_name: {view_name: path, 'seed': int}}
        """
        self.reference_data = reference_data
        self.logger = logging.getLogger(__name__)

    def enhance_scene_prompt(
        self,
        scene: Scene,
        base_prompt: str,
        character_dict: Dict[str, Character]
    ) -> str:
        """
        增强场景提示词，添加详细的角色外貌描述

        Args:
            scene: 场景对象
            base_prompt: 基础提示词
            character_dict: 角色字典 {name: Character}

        Returns:
            增强后的提示词
        """
        if not scene.characters:
            return base_prompt

        # 构建增强部分
        enhanced_parts = []

        # 添加详细的角色描述
        char_descriptions = []
        for char_name in scene.characters:
            if char_name in character_dict:
                char = character_dict[char_name]
                desc = self._build_character_description(char, char_name)
                if desc:
                    char_descriptions.append(desc)

        if char_descriptions:
            char_section = "Characters: " + ", ".join(char_descriptions)
            enhanced_parts.append(char_section)

        # 添加一致性提示
        if self.reference_data:
            enhanced_parts.append("consistent with character reference sheets")
            enhanced_parts.append("maintaining character appearance")

        # 组合提示词：基础部分 + 增强部分
        # 将角色描述插入到prompt的前半部分，以提高权重
        prompt_components = [part.strip() for part in base_prompt.split(',')]

        # 找到合适的插入位置（在"characters:"之后，或者动作描述之前）
        insert_index = self._find_character_insert_index(prompt_components)

        # 插入增强的角色描述
        if enhanced_parts:
            for i, part in enumerate(enhanced_parts):
                prompt_components.insert(insert_index + i, part)

        return ", ".join(prompt_components)

    def _find_character_insert_index(self, prompt_parts: List[str]) -> int:
        """
        找到插入角色详细描述的最佳位置

        Args:
            prompt_parts: 提示词各部分列表

        Returns:
            插入索引
        """
        # 寻找"characters:"关键词
        for i, part in enumerate(prompt_parts):
            if 'characters:' in part.lower() or 'character:' in part.lower():
                # 替换这一行
                return i

        # 如果没找到，插入到场景描述之后（通常是前2-3个元素）
        return min(3, len(prompt_parts))

    def _build_character_description(self, character: Character, char_name: str) -> str:
        """
        构建单个角色的详细描述

        Args:
            character: 角色对象
            char_name: 角色名称

        Returns:
            角色描述字符串
        """
        desc_parts = [char_name]

        # 从参考数据获取seed信息
        if char_name in self.reference_data:
            ref_data = self.reference_data[char_name]
            if 'seed' in ref_data:
                seed = ref_data['seed']
                desc_parts.append(f"(ref:{seed})")

        # 添加外貌特征
        if character.appearance:
            desc_parts.append(character.appearance)
        elif character.description:
            # 提取外貌相关的描述
            appearance_desc = self._extract_appearance_keywords(character.description)
            if appearance_desc:
                desc_parts.append(appearance_desc)

        # 添加年龄和性别
        age_gender = []
        if character.age:
            age_gender.append(f"{character.age} years old")
        if character.gender:
            age_gender.append(character.gender)

        if age_gender:
            desc_parts.append(" ".join(age_gender))

        return " ".join(desc_parts)

    def _extract_appearance_keywords(self, description: str) -> str:
        """
        从描述中提取外貌关键词

        Args:
            description: 角色描述

        Returns:
            提取的外貌特征
        """
        # 外貌相关关键词
        appearance_keywords = [
            'hair', 'eyes', 'glasses', 'beard', 'mustache',
            'tall', 'short', 'thin', 'muscular',
            'wearing', 'dressed', 'clothes', 'shirt', 'pants',
            '头发', '眼睛', '眼镜', '胡子', '身高',
            '穿', '衣服', 'T恤', '裤子', '外套'
        ]

        # 简单的关键词匹配（可以改进为NLP方法）
        relevant_parts = []
        for keyword in appearance_keywords:
            if keyword.lower() in description.lower():
                # 找到包含关键词的句子片段
                sentences = description.split('，')
                for sentence in sentences:
                    if keyword.lower() in sentence.lower():
                        relevant_parts.append(sentence.strip())
                        break

        return ", ".join(relevant_parts[:3]) if relevant_parts else description

    def get_character_seed(self, character_name: str) -> Optional[int]:
        """
        获取角色的参考seed

        Args:
            character_name: 角色名称

        Returns:
            角色seed，如果不存在则返回None
        """
        if character_name in self.reference_data:
            ref_data = self.reference_data[character_name]
            return ref_data.get('seed')
        return None

    def get_character_seeds(self, character_names: List[str]) -> List[int]:
        """
        获取多个角色的seed列表

        Args:
            character_names: 角色名称列表

        Returns:
            seed列表
        """
        seeds = []
        for name in character_names:
            seed = self.get_character_seed(name)
            if seed is not None:
                seeds.append(seed)
        return seeds

    def blend_character_seeds(self, character_names: List[str]) -> Optional[int]:
        """
        混合多个角色的seed（用于多角色场景）

        Args:
            character_names: 角色名称列表

        Returns:
            混合后的seed
        """
        seeds = self.get_character_seeds(character_names)

        if not seeds:
            return None

        if len(seeds) == 1:
            return seeds[0]

        # 使用XOR混合多个seed
        blended = seeds[0]
        for seed in seeds[1:]:
            blended ^= seed

        # 确保在有效范围内
        return blended % (2**32)

    def has_reference(self, character_name: str) -> bool:
        """
        检查角色是否有参考数据

        Args:
            character_name: 角色名称

        Returns:
            是否存在参考数据
        """
        return character_name in self.reference_data and 'error' not in self.reference_data[character_name]

    def get_reference_info(self, character_name: str) -> Optional[Dict[str, Any]]:
        """
        获取角色的完整参考信息

        Args:
            character_name: 角色名称

        Returns:
            参考信息字典，如果不存在则返回None
        """
        if self.has_reference(character_name):
            return self.reference_data[character_name]
        return None
