"""Image generation agent"""
import asyncio
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
from datetime import datetime

from agents.base_agent import BaseAgent
from services.image_service_factory import ImageServiceFactory
from services.llm_judge_service import LLMJudgeService
from models.script_models import Scene, Character, Script
from utils.concurrency import ConcurrencyLimiter, RateLimiter, TaskStats
from utils.character_enhancer import CharacterDescriptionEnhancer
from utils.prompt_optimizer import PromptOptimizer
from config.settings import settings
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

        # 使用工厂创建服务
        self.service = ImageServiceFactory.create_service()
        self.logger = logging.getLogger(__name__)

        # 并发控制 - 优先使用config中的配置，其次使用settings中的默认值
        max_concurrent = self.config.get('max_concurrent', settings.image_max_concurrent)
        self.limiter = ConcurrencyLimiter(max_concurrent)
        self.logger.info(f"ImageGenerationAgent initialized with max_concurrent={max_concurrent}")

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

        # 图生图配置
        self.enable_image_to_image = self.config.get('enable_image_to_image', True)
        self.reference_image_weight = self.config.get('reference_image_weight', 0.7)

        # 提示词优化器
        self.prompt_optimizer = PromptOptimizer()

        # LLM评分服务（用于角色一致性评估）
        self.enable_judge = self.config.get('enable_character_consistency_judge', settings.enable_character_consistency_judge)
        self.candidate_count = self.config.get('candidate_images_per_scene', settings.candidate_images_per_scene)
        self.judge_service: Optional[LLMJudgeService] = None

        if self.enable_judge:
            try:
                self.judge_service = LLMJudgeService()
                self.logger.info(f"LLM judge service enabled, generating {self.candidate_count} candidates per scene")
            except Exception as e:
                self.logger.warning(f"Failed to initialize LLM judge service: {e}. Disabling judge.")
                self.enable_judge = False
                self.judge_service = None

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
        为单个场景生成图片（支持图生图和多候选评分）

        Args:
            scene: 场景对象

        Returns:
            图片生成结果
        """
        self.logger.info(f"Generating image for scene: {scene.scene_id}")

        # 检查是否需要生成多个候选并评分
        should_judge = (
            self.enable_judge and
            self.judge_service and
            self.candidate_count > 1 and
            self.character_enhancer and
            len(scene.characters) > 0
        )

        if should_judge:
            return await self._generate_with_judging(scene)
        else:
            return await self._generate_single_image(scene)

    async def _generate_single_image(self, scene: Scene, candidate_index: Optional[int] = None) -> Dict[str, Any]:
        """
        生成单张图片（原有逻辑）

        Args:
            scene: 场景对象
            candidate_index: 候选索引（可选），用于生成唯一文件名

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
        reference_image = None

        if self.character_enhancer and self.character_dict:
            # 使用增强器进一步优化提示词
            enhanced_prompt = self.character_enhancer.enhance_scene_prompt(
                scene,
                base_prompt,
                self.character_dict
            )

        # 使用LLM优化提示词（在character enhancer之后）
        optimized_prompt = await self.prompt_optimizer.optimize_image_prompt(enhanced_prompt)
        self.logger.debug(f"Prompt before LLM optimization: {enhanced_prompt[:100]}...")
        self.logger.debug(f"Prompt after LLM optimization: {optimized_prompt[:100]}...")

        # 使用优化后的提示词
        enhanced_prompt = optimized_prompt

        if self.character_enhancer and self.character_dict:

            # 获取场景seed
            if len(scene.characters) == 1:
                # 单角色场景：使用角色专属seed
                scene_seed = self.character_enhancer.get_character_seed(scene.characters[0])
                self.logger.info(f"Using character seed {scene_seed} for {scene.characters[0]}")

                # 获取角色参考图（用于图生图）
                if self.enable_image_to_image:
                    reference_image = self.character_enhancer.get_character_reference_image(scene.characters[0])
                    if reference_image:
                        self.logger.info(f"Using reference image for character: {scene.characters[0]}")
                        # 在提示词中说明基于参考图生成
                        enhanced_prompt = f"Based on the character in the reference image, {enhanced_prompt}"

            elif len(scene.characters) > 1:
                # 多角色场景：混合seed
                scene_seed = self.character_enhancer.blend_character_seeds(scene.characters)
                self.logger.info(f"Using blended seed {scene_seed} for multi-character scene")

                # 多角色场景：尝试获取主要角色的参考图
                if self.enable_image_to_image:
                    # 使用第一个角色的参考图
                    reference_image = self.character_enhancer.get_character_reference_image(scene.characters[0])
                    if reference_image:
                        self.logger.info(f"Using reference image for primary character: {scene.characters[0]}")
                        # 在提示词中说明基于参考图生成多角色场景
                        enhanced_prompt = f"Based on the characters in the reference image, {enhanced_prompt}"

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
            'watermark': self.config.get('watermark', settings.doubao_watermark),  # 传递水印参数
        }

        # 图生图参数
        if reference_image and self.enable_image_to_image:
            # 检查服务是否支持图生图
            if ImageServiceFactory.supports_image_to_image():
                image_config['reference_image'] = reference_image
                image_config['reference_image_weight'] = self.reference_image_weight
                self.logger.info(f"Image-to-image enabled with weight {self.reference_image_weight}")
            else:
                self.logger.warning(f"Current service does not support image-to-image, falling back to text-to-image")

        # 生成文件名（添加微秒和候选索引以确保唯一性）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")  # 添加微秒
        if candidate_index is not None:
            filename = f"{scene.scene_id}_{timestamp}_candidate_{candidate_index}.png"
        else:
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
            'reference_image': reference_image,
            'config': image_config,
            'api_response': result.get('api_response')
        }

    async def _generate_with_judging(self, scene: Scene) -> Dict[str, Any]:
        """
        生成多个候选图片并使用LLM评分选择最佳（并发生成和评分）

        Args:
            scene: 场景对象

        Returns:
            最佳图片生成结果（包含评分信息）
        """
        self.logger.info(f"Generating {self.candidate_count} candidates for scene: {scene.scene_id}")

        # 获取主要角色（用于评分）
        primary_character = scene.characters[0] if scene.characters else None
        if not primary_character:
            self.logger.warning("No character in scene, falling back to single generation")
            return await self._generate_single_image(scene)

        # 获取角色参考图
        reference_image_path = None
        if self.character_enhancer:
            reference_image_path = self.character_enhancer.get_character_reference_image(primary_character)

        if not reference_image_path or not Path(reference_image_path).exists():
            self.logger.warning(f"No reference image for character {primary_character}, falling back to single generation")
            return await self._generate_single_image(scene)

        # 并发生成多个候选图片
        self.logger.info(f"Generating {self.candidate_count} candidates concurrently")

        # 创建生成任务列表（传递候选索引）
        generation_tasks = [
            self._generate_single_image(scene, candidate_index=i)
            for i in range(self.candidate_count)
        ]

        # 并发执行所有生成任务
        candidates = await asyncio.gather(*generation_tasks)

        # 提取候选图片路径（无需重命名，文件名已包含候选索引）
        candidate_paths = []
        for i, result in enumerate(candidates):
            candidate_path = Path(result['image_path'])
            candidate_paths.append(candidate_path)
            self.logger.info(f"Generated candidate {i+1}/{self.candidate_count}: {candidate_path.name}")

        # 使用LLM并发评分
        self.logger.info(f"Judging {len(candidates)} candidates concurrently")

        # 获取场景提示词
        scene_prompt = scene.to_image_prompt(self.character_dict)

        # 并发批量评分
        judge_results = await self._concurrent_batch_judge(
            reference_image_path=Path(reference_image_path),
            candidate_images=candidate_paths,
            scene_prompt=scene_prompt,
            character_name=primary_character
        )

        # 选择最佳候选
        best_result = self.judge_service.select_best_candidate(judge_results)
        best_index = best_result['candidate_index']
        best_candidate = candidates[best_index]

        # 将最佳候选重命名为最终文件（移除候选索引和微秒）
        best_path = Path(best_candidate['image_path'])
        # 从文件名中移除 _微秒_candidate_索引 部分
        # 例如: scene_001_20260109_021920_123456_candidate_0.png -> scene_001_20260109_021920.png
        import re
        final_filename = re.sub(r'_\d{6}_candidate_\d+', '', best_path.stem) + best_path.suffix
        final_path = best_path.parent / final_filename

        # 如果目标文件已存在，添加时间戳避免覆盖
        if final_path.exists():
            timestamp_suffix = datetime.now().strftime("_%f")
            final_filename = re.sub(r'_\d{6}_candidate_\d+', timestamp_suffix, best_path.stem) + best_path.suffix
            final_path = best_path.parent / final_filename

        best_path.rename(final_path)

        # 删除其他候选图片（可选，根据配置决定）
        save_candidates = self.config.get('save_all_candidates', False)
        if not save_candidates:
            for i, candidate_path in enumerate(candidate_paths):
                if i != best_index and candidate_path.exists():
                    candidate_path.unlink()
                    self.logger.debug(f"Deleted candidate {i}: {candidate_path}")

        # 更新最佳候选的结果
        best_candidate['image_path'] = str(final_path)
        best_candidate['judge_score'] = best_result['score']
        best_candidate['judge_reasoning'] = best_result.get('reasoning', '')
        best_candidate['consistency_aspects'] = best_result.get('consistency_aspects', {})
        best_candidate['candidate_index'] = best_index
        best_candidate['total_candidates'] = self.candidate_count
        best_candidate['all_judge_results'] = judge_results if save_candidates else None

        self.logger.info(
            f"Selected best candidate {best_index} with score {best_result['score']}/100 for scene {scene.scene_id}"
        )

        return best_candidate

    async def _concurrent_batch_judge(
        self,
        reference_image_path: Path,
        candidate_images: List[Path],
        scene_prompt: str,
        character_name: str
    ) -> List[Dict[str, Any]]:
        """
        并发批量评估多个候选图片

        Args:
            reference_image_path: 角色参考图路径
            candidate_images: 候选场景图片路径列表
            scene_prompt: 场景提示词
            character_name: 角色名称

        Returns:
            评分结果列表
        """
        # 创建评分任务列表
        judge_tasks = [
            self.judge_service.judge_character_consistency(
                reference_image_path,
                scene_image_path,
                scene_prompt,
                character_name
            )
            for scene_image_path in candidate_images
        ]

        # 并发执行所有评分任务
        results = await asyncio.gather(*judge_tasks)

        # 添加候选索引和图片路径
        for i, result in enumerate(results):
            result['candidate_index'] = i
            result['image_path'] = str(candidate_images[i])
            self.logger.info(f"Candidate {i+1} judged with score: {result.get('score', 0)}/100")

        return results

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
        await self.prompt_optimizer.close()
        if self.judge_service:
            await self.judge_service.close()
