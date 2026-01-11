"""Character reference generation agent"""
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from agents.base_agent import BaseAgent
from services.image_service_factory import ImageServiceFactory
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

        # 使用工厂创建服务
        self.service = ImageServiceFactory.create_service()
        self.logger = logging.getLogger(__name__)

        # 并发控制
        max_concurrent = self.config.get('max_concurrent', 2)
        self.limiter = ConcurrencyLimiter(max_concurrent)

        # 参考图配置
        self.reference_mode = self.config.get('character_reference_mode', 'single_multi_view')
        self.reference_views = self.config.get('reference_views', [
            'front_view',
            'side_view',
            'close_up',
            'full_body'
        ])
        self.reference_size = self.config.get('reference_image_size', 1024)
        self.reference_cfg_scale = self.config.get('reference_cfg_scale', 8.0)
        self.reference_steps = self.config.get('reference_steps', 60)
        self.art_style = self.config.get('character_art_style', 'realistic')

    async def execute(
        self,
        characters: List[Character],
        character_images: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        为角色列表生成参考图集或加载已有参考图

        Args:
            characters: 角色列表
            character_images: 角色图片配置字典 (可选)
                格式: {
                    "character_name": {
                        "mode": "load" | "generate",
                        "images": [paths],  # for mode=load
                        "views": [views]     # for mode=generate
                    }
                }

        Returns:
            角色参考数据字典: {character_name: {mode: str, reference_image: path, ...}}
        """
        if not await self.validate_input(characters):
            raise ValueError("Invalid characters data")

        self.logger.info(
            f"CharacterReferenceAgent | Starting reference processing | "
            f"total_characters={len(characters)} | "
            f"has_character_images_config={character_images is not None}"
        )
        
        if character_images:
            self.logger.info(
                f"CharacterReferenceAgent | Character images config provided | "
                f"configured_characters={list(character_images.keys())} | "
                f"count={len(character_images)}"
            )
            for char_name, char_config in character_images.items():
                self.logger.debug(
                    f"CharacterReferenceAgent | Character config details | "
                    f"character={char_name} | "
                    f"mode={char_config.get('mode', 'not_specified')} | "
                    f"images_count={len(char_config.get('images', []))} | "
                    f"views={char_config.get('views', [])}"
                )

        reference_data = {}

        for character in characters:
            char_config = character_images.get(character.name, {}) if character_images else {}
            mode = char_config.get('mode', 'generate')

            self.logger.info(
                f"CharacterReferenceAgent | Processing character | "
                f"name={character.name} | "
                f"mode={mode} | "
                f"has_config={bool(char_config)}"
            )

            try:
                if mode == 'load':
                    # 加载已有图片
                    self.logger.info(
                        f"CharacterReferenceAgent | Loading custom image | "
                        f"character={character.name} | "
                        f"images_to_load={len(char_config.get('images', []))}"
                    )
                    views = await self._load_character_images(character, char_config)
                    self.logger.info(
                        f"CharacterReferenceAgent | Successfully loaded custom images | "
                        f"character={character.name} | "
                        f"images_count={len(char_config.get('images', []))} | "
                        f"reference_image={views.get('reference_image', 'none')}"
                    )
                else:
                    # 生成新参考图
                    self.logger.info(
                        f"CharacterReferenceAgent | Generating new reference images | "
                        f"character={character.name} | "
                        f"reference_mode={self.reference_mode}"
                    )
                    custom_views = char_config.get('views')
                    views = await self._generate_character_views(character, custom_views)
                    self.logger.info(
                        f"CharacterReferenceAgent | Successfully generated reference images | "
                        f"character={character.name} | "
                        f"reference_image={views.get('reference_image', 'none')}"
                    )

                reference_data[character.name] = views

            except Exception as e:
                self.logger.error(
                    f"CharacterReferenceAgent | Failed to process references | "
                    f"character={character.name} | "
                    f"mode={mode} | "
                    f"error={type(e).__name__}: {str(e)}"
                )
                await self.on_error(e)
                # 继续处理其他角色，不中断整个流程
                reference_data[character.name] = {
                    'mode': mode,
                    'error': str(e),
                    'reference_image': None
                }

        # Log final summary
        success_count = sum(1 for char_data in reference_data.values() if 'error' not in char_data)
        # Count loaded (directly loaded without generation) vs generated (including from custom base)
        loaded_fallback_count = sum(1 for char_data in reference_data.values() if char_data.get('mode') == 'loaded_fallback')
        generated_from_custom_count = sum(1 for char_data in reference_data.values() if char_data.get('mode') == 'generated_from_custom')
        generated_count = sum(1 for char_data in reference_data.values() if char_data.get('mode') in ['single_multi_view', 'multiple_single_view'])
        
        self.logger.info(
            f"CharacterReferenceAgent | Reference processing completed | "
            f"total={len(characters)} | "
            f"success={success_count} | "
            f"generated_from_ai={generated_count} | "
            f"generated_from_custom={generated_from_custom_count} | "
            f"loaded_fallback={loaded_fallback_count} | "
            f"failed={len(characters) - success_count}"
        )

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

    async def _load_character_images(
        self,
        character: Character,
        char_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        加载用户上传的角色图片，并基于该图片生成角色建模参考图
        
        正确流程：
        1. 验证用户上传的基准图存在
        2. 使用图生图技术，基于用户上传的基准图生成角色建模图（多视角参考表）
        3. 将生成的角色建模图保存到character_references目录
        4. 返回生成的角色建模图路径

        Args:
            character: 角色对象
            char_config: 角色配置，包含images列表（用户上传的基准图）

        Returns:
            视图数据字典: {mode: 'generated_from_custom', reference_image: path, seed: int, base_image: original_path}
        """
        images = char_config.get('images', [])

        if not images:
            raise ValueError(f"No images specified for character '{character.name}' in load mode")

        # 验证所有图片文件存在
        missing_images = []
        for image_path in images:
            if not Path(image_path).exists():
                missing_images.append(image_path)

        if missing_images:
            raise FileNotFoundError(
                f"Character '{character.name}': image files not found: {', '.join(missing_images)}"
            )

        # 使用第一张图片作为基准图
        base_image_path = images[0]
        self.logger.info(
            f"CharacterReferenceAgent | Using custom base image | "
            f"character={character.name} | "
            f"base_image={base_image_path}"
        )

        # 基于用户上传的基准图生成角色建模参考图
        self.logger.info(
            f"CharacterReferenceAgent | Generating character modeling sheet from custom image | "
            f"character={character.name} | "
            f"reference_mode={self.reference_mode}"
        )
        
        try:
            # 生成角色专用seed（保持一致性）
            char_seed = hash(character.name) % (2**32)
            
            # 调用图生图生成角色建模参考图
            modeling_sheet = await self._generate_modeling_sheet_from_base_image(
                character=character,
                base_image_path=base_image_path,
                char_seed=char_seed
            )
            
            self.logger.info(
                f"CharacterReferenceAgent | Successfully generated modeling sheet from custom image | "
                f"character={character.name} | "
                f"modeling_sheet={modeling_sheet.get('reference_image', 'none')} | "
                f"seed={char_seed}"
            )
            
            # 添加原始基准图信息
            modeling_sheet['base_image'] = base_image_path
            modeling_sheet['mode'] = 'generated_from_custom'
            
            return modeling_sheet
            
        except Exception as e:
            self.logger.error(
                f"CharacterReferenceAgent | Failed to generate modeling sheet from custom image | "
                f"character={character.name} | "
                f"error={type(e).__name__}: {str(e)}"
            )
            # 降级：如果生成失败，仍然返回原始图片
            self.logger.warning(
                f"CharacterReferenceAgent | Falling back to original custom image | "
                f"character={character.name}"
            )
            return {
                'mode': 'loaded_fallback',
                'reference_image': base_image_path,
                'images': images,
                'character_name': character.name,
                'error': str(e)
            }

    async def _generate_character_views(
        self,
        character: Character,
        custom_views: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        为单个角色生成参考图（单张多视角 或 多张单视角）

        Args:
            character: 角色对象
            custom_views: 自定义视图列表（可选，仅用于multiple_single_view模式）

        Returns:
            视图数据字典: {view_name: image_path, 'seed': int, 'reference_image': main_image_path}
        """
        # 生成角色专用seed
        char_seed = hash(character.name) % (2**32)

        if self.reference_mode == 'single_multi_view':
            # 单张多视角模式
            return await self._generate_single_multi_view(character, char_seed)
        else:
            # 多张单视角模式（原有逻辑）
            views_to_generate = custom_views or self.reference_views
            return await self._generate_multiple_single_views(character, char_seed, views_to_generate)

    async def _generate_modeling_sheet_from_base_image(
        self,
        character: Character,
        base_image_path: str,
        char_seed: int
    ) -> Dict[str, Any]:
        """
        基于用户上传的基准图，生成角色建模参考图（使用图生图技术）
        
        这是修复后的正确流程：用户上传的图片作为输入，
        生成包含多个视角的角色建模图，保存到character_references目录

        Args:
            character: 角色对象
            base_image_path: 用户上传的基准图路径
            char_seed: 角色专用seed

        Returns:
            视图数据字典: {'reference_image': image_path, 'seed': int, 'mode': 'generated_from_custom'}
        """
        self.logger.info(
            f"CharacterReferenceAgent | Generating modeling sheet using image-to-image | "
            f"character={character.name} | "
            f"base_image={base_image_path} | "
            f"seed={char_seed}"
        )
        
        # 构建基础提示词
        base_prompt = self._build_character_base_prompt(character)

        # 创建角色专用目录
        char_dir = self.output_dir / character.name.replace(" ", "_")
        char_dir.mkdir(parents=True, exist_ok=True)

        # 构建用于图生图的提示词 - 强调基于原图生成多视角参考表
        background_style = "clean white background" if self.art_style != 'realistic' else "studio lighting, neutral background"
        modeling_prompt = (
            f"Based on the character in the reference image, create a character reference sheet. "
            f"{base_prompt}, "
            f"character design sheet with multiple views in one image, "
            f"showing: front view, side profile view, close-up portrait, full body view, "
            f"professional character turnaround sheet, {background_style}, "
            f"maintain the exact same character appearance from the reference image, "
            f"consistent character design, high detail, 8k quality"
        )

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{character.name}_modeling_sheet_{timestamp}.png"
        save_path = char_dir / filename

        self.logger.debug(
            f"CharacterReferenceAgent | Image-to-image generation params | "
            f"prompt_preview={modeling_prompt[:100]}... | "
            f"reference_image={base_image_path} | "
            f"output_path={save_path}"
        )

        try:
            # 使用图生图生成角色建模参考表
            result = await self.service.generate_and_save(
                prompt=modeling_prompt,
                save_path=save_path,
                width=self.reference_size * 2,  # 更宽以容纳多个视角
                height=self.reference_size,
                quality='high',
                seed=char_seed,
                cfg_scale=self.reference_cfg_scale,
                steps=self.reference_steps,
                reference_image=base_image_path,  # 关键：使用用户上传的图片作为参考
                reference_image_weight=0.8  # 较高的权重以保持角色一致性
            )

            self.logger.info(
                f"CharacterReferenceAgent | Successfully generated modeling sheet | "
                f"character={character.name} | "
                f"output={result['image_path']}"
            )

            return {
                'reference_image': result['image_path'],
                'seed': char_seed,
                'mode': 'generated_from_custom',
                'character_name': character.name
            }

        except Exception as e:
            self.logger.error(
                f"CharacterReferenceAgent | Image-to-image generation failed | "
                f"character={character.name} | "
                f"error={type(e).__name__}: {str(e)}"
            )
            raise

    async def _generate_single_multi_view(self, character: Character, char_seed: int) -> Dict[str, Any]:
        """
        生成单张包含多个视角的参考图

        Args:
            character: 角色对象
            char_seed: 角色专用seed

        Returns:
            视图数据字典: {'reference_image': image_path, 'seed': int}
        """
        # 构建基础提示词
        base_prompt = self._build_character_base_prompt(character)

        # 创建角色专用目录
        char_dir = self.output_dir / character.name.replace(" ", "_")
        char_dir.mkdir(parents=True, exist_ok=True)

        # 构建多视角参考图提示词
        background_style = "clean white background" if self.art_style != 'realistic' else "studio lighting, neutral background"
        multi_view_prompt = (
            f"{base_prompt}, "
            f"character reference sheet, multiple views in one image, "
            f"showing: front view, side profile view, close-up portrait, full body view, "
            f"professional character design sheet, {background_style}, "
            f"consistent character across all views, turnaround reference, "
            f"high detail, 8k quality"
        )

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{character.name}_reference_sheet_{timestamp}.png"
        save_path = char_dir / filename

        try:
            # 生成参考图（使用更高的质量参数）
            result = await self.service.generate_and_save(
                prompt=multi_view_prompt,
                save_path=save_path,
                width=self.reference_size * 2,  # 更宽以容纳多个视角
                height=self.reference_size,
                quality='high',
                seed=char_seed,  # 使用固定seed确保一致性
                cfg_scale=self.reference_cfg_scale,  # 更高的引导强度
                steps=self.reference_steps  # 更多推理步数
            )

            self.logger.info(f"Generated multi-view reference sheet for {character.name}")

            return {
                'reference_image': result['image_path'],
                'seed': char_seed,
                'mode': 'single_multi_view'
            }

        except Exception as e:
            self.logger.error(f"Failed to generate multi-view reference for {character.name}: {e}")
            return {
                'reference_image': None,
                'seed': char_seed,
                'mode': 'single_multi_view',
                'error': str(e)
            }

    async def _generate_multiple_single_views(
        self,
        character: Character,
        char_seed: int,
        views_to_generate: List[str]
    ) -> Dict[str, Any]:
        """
        生成多张单视角参考图（原有逻辑）

        Args:
            character: 角色对象
            char_seed: 角色专用seed
            views_to_generate: 要生成的视图列表

        Returns:
            视图数据字典: {view_name: image_path, 'seed': int}
        """
        # 构建基础提示词
        base_prompt = self._build_character_base_prompt(character)

        # 创建角色专用目录
        char_dir = self.output_dir / character.name.replace(" ", "_")
        char_dir.mkdir(parents=True, exist_ok=True)

        views = {'seed': char_seed, 'mode': 'multiple_single_view'}

        # 根据风格选择背景样式
        background_style = "white background" if self.art_style != 'realistic' else "studio lighting, neutral background"

        # 视图提示词模板
        view_prompts = {
            'front_view': f"{base_prompt}, front view, neutral expression, {background_style}",
            'side_view': f"{base_prompt}, side profile view, neutral expression, {background_style}",
            'close_up': f"{base_prompt}, close-up portrait, detailed facial features, professional headshot, {background_style}",
            'full_body': f"{base_prompt}, full body view, standing pose, {background_style}"
        }

        # 只生成指定的视图
        for view_name in views_to_generate:
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

        # 使用front_view作为主参考图
        views['reference_image'] = views.get('front_view')

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

        # 风格关键词（放在最前面，确保优先级）
        style_keywords = self._get_style_keywords()
        prompt_parts.append(style_keywords)

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

    def _get_style_keywords(self) -> str:
        """
        根据艺术风格配置获取对应的提示词关键词

        Returns:
            风格相关的提示词
        """
        style_keywords = {
            'realistic': (
                "photorealistic, realistic photography, real person, "
                "cinematic lighting, professional photography, "
                "highly detailed, natural skin texture, realistic features"
            ),
            'anime': (
                "anime style, manga style, 2D illustration, "
                "anime character design, cel shaded, vibrant colors"
            ),
            'semi_realistic': (
                "semi-realistic style, stylized realistic, "
                "detailed illustration, painterly style, artistic rendering"
            )
        }
        return style_keywords.get(self.art_style, style_keywords['realistic'])

    async def close(self):
        """关闭资源"""
        await self.service.close()
