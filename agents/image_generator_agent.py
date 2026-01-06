"""Image generation agent"""
import asyncio
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
from datetime import datetime

from agents.base_agent import BaseAgent
from services.nano_banana_service import NanoBananaService
from models.script_models import Scene
from utils.concurrency import ConcurrencyLimiter, RateLimiter, TaskStats
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
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """
        执行批量图片生成（并发执行）

        Args:
            scenes: 场景列表
            progress_callback: 进度回调函数

        Returns:
            图片生成结果列表
        """
        if not await self.validate_input(scenes):
            raise ValueError("Invalid scenes data")

        self.progress_callback = progress_callback
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
        prompt = scene.to_image_prompt()

        # 配置图片参数
        image_config = {
            'width': self.config.get('width', 1920),
            'height': self.config.get('height', 1080),
            'quality': self.config.get('quality', 'high'),
            'style': scene.visual_style if scene.visual_style else None,
            'negative_prompt': self.config.get('negative_prompt')
        }

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{scene.scene_id}_{timestamp}.png"
        save_path = self.output_dir / filename

        # 调用服务生成并保存图片
        result = await self.service.generate_and_save(
            prompt=prompt,
            save_path=save_path,
            **image_config
        )

        return {
            'scene_id': scene.scene_id,
            'image_path': result['image_path'],
            'prompt': prompt,
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
