"""Image generation agent"""
import asyncio
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
from datetime import datetime

from agents.base_agent import BaseAgent
from services.nano_banana_service import NanoBananaService
from models.script_models import Scene, Character, Script
from utils.concurrency import ConcurrencyLimiter, RateLimiter, TaskStats
from utils.character_enhancer import CharacterDescriptionEnhancer
import logging


class ImageGenerationAgent(BaseAgent):
    """图片生成Agent - 根据分镜场景生成图片"""

    def __init__(
        self,
        agent_id: str = "image_generator",
        config: Dict[str, Any] = None,
        output_dir: Optional[Path] = None
    ):
        super().__init__(agent_id, config or {})
        self.output_dir = output_dir or Path("./output/images")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.service = NanoBananaService()
        self.logger = logging.getLogger(__name__)

        # 并发控制
        max_concurrent = self.config.get('max_concurrent', 3)
        self.limiter = ConcurrencyLimiter(max_concurrent)

        # 速率限制（可选）
        if self.config.get('enable_rate_limit', False):
            max_requests = self.config.get('max_requests_per_minute', 10)
            self.rate_limiter = RateLimiter(
                max_requests=max_requests,
                time_window=60.0
            )
        else:
            self.rate_limiter = None

        # 进度回调
        self.progress_callback: Optional[Callable] = None

        # 一致性增强器（由外部设置）
        self.character_enhancer: Optional[CharacterDescriptionEnhancer] = None
        self.character_dict: Optional[Dict[str, Character]] = None

    async def execute(self, scenes: List[Scene]) -> List[Dict[str, Any]]:
        """
        执行批量图片生成（顺序执行）

        Args:
            scenes: 场景列表

        Returns:
            图片生成结果列表
        """
        if not await self.validate_input(scenes):
            raise ValueError("Invalid scenes data")

        self.logger.info(f"Starting image generation for {len(scenes)} scenes")

        results = []
        for i, scene in enumerate(scenes):
            result = await self._generate_image_for_scene(scene)
            results.append(result)

            # 进度回调
            if self.progress_callback:
                progress = (i + 1) / len(scenes) * 100
                await self._call_progress_callback(progress, f"Generated image {i+1}/{len(scenes)}")

        await self.on_complete(results)
        return results

    async def execute_concurrent(
        self,
        scenes: List[Scene],
        script: Optional[Script] = None,
        reference_data: Optional[Dict[str, Dict[str, Any]]] = None,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """
        执行批量图片生成（并发执行）

        Args:
            scenes: 场景列表
            script: 完整脚本对象（可选，用于一致性增强）
            reference_data: 角色参考数据（可选，用于一致性增强）
            progress_callback: 进度回调函数

        Returns:
            图片生成结果列表
        """
        if not await self.validate_input(scenes):
            raise ValueError("Invalid scenes data")

        self.progress_callback = progress_callback

        # 初始化一致性增强器
        if reference_data and script:
            self.logger.info("Initializing character consistency enhancer")
            self.character_enhancer = CharacterDescriptionEnhancer(reference_data)
            self.character_dict = {c.name: c for c in script.characters}
        elif script:
            # 即使没有参考数据，也可以使用角色字典来增强prompt
            self.logger.info("Using character dictionary for prompt enhancement")
            self.character_dict = {c.name: c for c in script.characters}
        else:
            self.character_enhancer = None
            self.character_dict = None

        self.logger.info(f"Starting concurrent image generation for {len(scenes)} scenes")

        try:
            # 使用并发限制器批量执行
            results = await self.limiter.run_batch(
                self._generate_image_for_scene,
                scenes,
                show_progress=True
            )

            await self.on_complete(results)
            return results

        except Exception as e:
            await self.on_error(e)
            raise

    async def validate_input(self, scenes: List[Scene]) -> bool:
        """验证输入数据"""
        if not scenes:
            self.logger.error("Scenes list is empty")
            return False

        if not all(isinstance(scene, Scene) for scene in scenes):
            self.logger.error("Invalid scene objects in list")
            return False

        return True

    async def _generate_image_for_scene(self, scene: Scene) -> Dict[str, Any]:
        """
        为单个场景生成图片

        Args:
            scene: 场景对象

        Returns:
            图片生成结果
        """
        self.logger.info(f"Generating image for scene: {scene.scene_id}")

        # 使用速率限制（如果启用）
        if self.rate_limiter:
            await self.rate_limiter.acquire()

        # 生成图片提示词
        base_prompt = scene.to_image_prompt(self.character_dict)

        # 使用一致性增强器增强提示词（如果可用）
        enhanced_prompt = base_prompt
        scene_seed = None

        if self.character_enhancer and self.character_dict:
            # 使用增强器进一步优化提示词
            enhanced_prompt = self.character_enhancer.enhance_scene_prompt(
                scene,
                base_prompt,
                self.character_dict
            )

            # 获取场景seed
            if len(scene.characters) == 1:
                # 单角色场景：使用角色专属seed
                scene_seed = self.character_enhancer.get_character_seed(scene.characters[0])
                self.logger.info(f"Using character seed {scene_seed} for {scene.characters[0]}")
            elif len(scene.characters) > 1:
                # 多角色场景：混合seed
                scene_seed = self.character_enhancer.blend_character_seeds(scene.characters)
                self.logger.info(f"Using blended seed {scene_seed} for multi-character scene")

        # 配置图片参数
        image_config = {
            'width': self.config.get('width', 1920),
            'height': self.config.get('height', 1080),
            'quality': self.config.get('quality', 'high'),
            'style': scene.visual_style if scene.visual_style else None,
            'negative_prompt': self.config.get('negative_prompt'),
            'seed': scene_seed,
            'cfg_scale': self.config.get('cfg_scale', 7.5),
            'steps': self.config.get('steps', 50),
        }

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{scene.scene_id}_{timestamp}.png"
        save_path = self.output_dir / filename

        # 调用服务生成并保存图片
        result = await self.service.generate_and_save(
            prompt=enhanced_prompt,
            save_path=save_path,
            **image_config
        )

        return {
            'scene_id': scene.scene_id,
            'image_path': result['image_path'],
            'prompt': enhanced_prompt,
            'original_prompt': base_prompt,
            'seed': scene_seed,
            'config': image_config,
            'api_response': result.get('api_response')
        }

    async def _call_progress_callback(self, progress: float, message: str):
        """调用进度回调"""
        if self.progress_callback:
            if asyncio.iscoroutinefunction(self.progress_callback):
                await self.progress_callback(progress, message)
            else:
                self.progress_callback(progress, message)

    async def batch_generate_with_stats(
        self,
        scenes: List[Scene]
    ) -> tuple[List[Dict[str, Any]], TaskStats]:
        """
        批量生成图片并返回统计信息

        Args:
            scenes: 场景列表

        Returns:
            (结果列表, 统计信息)
        """
        import time

        stats = TaskStats(
            total_tasks=len(scenes),
            start_time=time.time()
        )

        results = []
        for scene in scenes:
            try:
                result = await self._generate_image_for_scene(scene)
                results.append(result)
                stats.completed_tasks += 1
            except Exception as e:
                self.logger.error(f"Failed to generate image for scene {scene.scene_id}: {e}")
                stats.failed_tasks += 1
                results.append({
                    'scene_id': scene.scene_id,
                    'error': str(e),
                    'success': False
                })

        stats.end_time = time.time()

        self.logger.info(f"Batch generation completed: {stats}")

        return results, stats

    async def close(self):
        """关闭资源"""
        await self.service.close()
