"""Video generation agent"""
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from agents.base_agent import BaseAgent
from services.veo3_service import Veo3Service, VideoGenerationError
from models.script_models import Scene, SubScene, CameraMovement
from utils.concurrency import ConcurrencyLimiter
from utils.prompt_optimizer import PromptOptimizer
from utils.video_utils import FFmpegProcessor
from config.settings import settings
import logging


class VideoGenerationAgent(BaseAgent):
    """视频生成Agent - 将分镜图片转换为视频片段"""

    def __init__(
        self,
        agent_id: str = "video_generator",
        config: Dict[str, Any] = None,
        output_dir: Optional[Path] = None
    ):
        super().__init__(agent_id, config or {})
        self.output_dir = output_dir or Path("./output/videos")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.service = Veo3Service()
        self.logger = logging.getLogger(__name__)

        # 并发限制 - 优先使用config中的配置，其次使用settings中的默认值
        # Veo3生成较慢，建议降低并发数
        max_concurrent = self.config.get('max_concurrent', settings.video_max_concurrent)
        self.limiter = ConcurrencyLimiter(max_concurrent)
        self.logger.info(f"VideoGenerationAgent initialized with max_concurrent={max_concurrent}")

        # 提示词优化器
        self.prompt_optimizer = PromptOptimizer()
        
        # FFmpeg处理器（用于帧提取和视频拼接）
        self.ffmpeg_processor = FFmpegProcessor()
        
        # 项目路径（用于加载自定义场景图）
        self.project_path: Optional[Path] = None

        # 重试配置
        self.max_retries = self.config.get(
            'max_retries',
            settings.video_generation_max_retries
        )
        self.retry_delay = self.config.get(
            'retry_delay',
            settings.video_generation_retry_delay
        )
        self.retry_backoff = self.config.get(
            'retry_backoff',
            settings.video_generation_retry_backoff
        )
    
    def set_project_path(self, project_path: Path):
        """
        设置项目路径，用于加载自定义场景图
        
        Args:
            project_path: 项目文件夹路径
        """
        self.project_path = project_path
        self.logger.info(f"Project path set to: {project_path}")

    async def execute(
        self,
        image_results: List[Dict[str, Any]],
        scenes: List[Scene],
        character_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        执行批量视频生成

        Args:
            image_results: 图片生成结果列表
            scenes: 对应的场景列表
            character_dict: 可选的角色字典，用于生成视频提示词

        Returns:
            视频生成结果列表
        """
        if not await self.validate_input((image_results, scenes)):
            raise ValueError("Invalid input data")

        self.logger.info(f"Starting video generation for {len(image_results)} clips")

        try:
            # 构建任务列表
            tasks_data = []
            for img_result, scene in zip(image_results, scenes):
                tasks_data.append({
                    'image_result': img_result,
                    'scene': scene,
                    'character_dict': character_dict
                })

            # 并发执行
            results = await self.limiter.run_batch(
                self._generate_video_clip,
                tasks_data,
                show_progress=True
            )

            await self.on_complete(results)
            return results

        except Exception as e:
            await self.on_error(e)
            raise

    async def validate_input(self, input_data: tuple) -> bool:
        """验证输入数据"""
        image_results, scenes = input_data

        if not image_results or not scenes:
            return False

        if len(image_results) != len(scenes):
            self.logger.error("Image results and scenes count mismatch")
            return False

        return True

    async def _generate_video_clip(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成单个视频片段（带重试机制和智能提示词调整）
        支持带子场景的场景生成
        
        Args:
            task_data: 包含image_result、scene和character_dict的字典

        Returns:
            视频生成结果
        """
        image_result = task_data['image_result']
        scene = task_data['scene']
        character_dict = task_data.get('character_dict')

        # 检查是否有子场景
        if scene.sub_scenes:
            self.logger.info(f"Scene {scene.scene_id} has {len(scene.sub_scenes)} sub-scenes, using hierarchical generation")
            return await self._generate_scene_with_subscenes(
                image_result,
                scene,
                character_dict
            )
        else:
            # 普通场景，使用原有逻辑
            return await self._generate_simple_scene(
                image_result,
                scene,
                character_dict
            )

    async def _generate_simple_scene(
        self,
        image_result: Dict[str, Any],
        scene: Scene,
        character_dict: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        生成简单场景（无子场景）
        
        Args:
            image_result: 图片生成结果
            scene: 场景对象
            character_dict: 角色字典
            
        Returns:
            视频生成结果
        """
        image_path = image_result['image_path']
        scene_id = scene.scene_id

        # 跟踪是否遇到音频过滤错误
        audio_filtered_error = False

        # 带重试的视频生成
        for attempt in range(self.max_retries + 1):
            try:
                return await self._generate_video_clip_once(
                    image_path,
                    scene,
                    scene_id,
                    character_dict,
                    attempt,
                    remove_dialogues=audio_filtered_error  # 如果之前遇到音频过滤错误，移除台词
                )
            except VideoGenerationError as e:
                # 检查是否是音频过滤错误
                if e.error_type == 'audio_filtered':
                    audio_filtered_error = True
                    self.logger.warning(
                        f"Audio filtered error detected for scene {scene_id}. "
                        f"Will retry without dialogues in next attempt."
                    )

                # 检查是否可重试
                if not e.retryable:
                    self.logger.error(
                        f"Non-retryable error for scene {scene_id}: {e}"
                    )
                    raise

                # 检查是否还有重试次数
                if attempt < self.max_retries:
                    delay = self.retry_delay * (self.retry_backoff ** attempt)
                    retry_strategy = " (will remove dialogues)" if audio_filtered_error else ""
                    self.logger.warning(
                        f"Video generation failed for scene {scene_id} "
                        f"(attempt {attempt + 1}/{self.max_retries + 1}): {e}{retry_strategy}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(
                        f"Video generation failed for scene {scene_id} "
                        f"after {self.max_retries + 1} attempts"
                    )
                    raise
            except Exception as e:
                # 其他异常（网络错误等）也进行重试
                if attempt < self.max_retries:
                    delay = self.retry_delay * (self.retry_backoff ** attempt)
                    self.logger.warning(
                        f"Unexpected error for scene {scene_id} "
                        f"(attempt {attempt + 1}/{self.max_retries + 1}): {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(
                        f"Video generation failed for scene {scene_id} "
                        f"after {self.max_retries + 1} attempts with error: {e}"
                    )
                    raise

    async def _generate_scene_with_subscenes(
        self,
        image_result: Dict[str, Any],
        scene: Scene,
        character_dict: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        生成包含子场景的场景视频
        
        流程:
        1. 从图片生成基础场景视频
        2. 从基础视频提取指定帧
        3. 使用提取的帧生成所有子场景视频
        4. 拼接基础视频和所有子场景视频
        
        Args:
            image_result: 图片生成结果
            scene: 场景对象（包含子场景）
            character_dict: 角色字典
            
        Returns:
            最终拼接后的视频生成结果
        """
        scene_id = scene.scene_id
        self.logger.info(
            f"Generating hierarchical scene {scene_id} with {len(scene.sub_scenes)} sub-scenes"
        )
        
        # Step 1: 生成基础场景视频
        self.logger.info(f"Step 1/4: Generating base scene video for {scene_id}")
        base_video_result = await self._generate_simple_scene(
            image_result,
            scene,
            character_dict
        )
        base_video_path = base_video_result['video_path']
        self.logger.info(f"Base scene video generated: {base_video_path}")
        
        # Step 2: 从基础视频提取帧
        self.logger.info(
            f"Step 2/4: Extracting frame at index {scene.extract_frame_index} from base video"
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extracted_frame_path = self.output_dir / f"{scene_id}_extracted_frame_{timestamp}.png"
        
        try:
            self.ffmpeg_processor.extract_frame(
                video_path=base_video_path,
                frame_index=scene.extract_frame_index,
                output_path=str(extracted_frame_path)
            )
            self.logger.info(f"Frame extracted successfully: {extracted_frame_path}")
        except Exception as e:
            self.logger.error(f"Failed to extract frame from base video: {e}")
            raise
        
        # Step 3: 生成所有子场景视频
        self.logger.info(f"Step 3/4: Generating {len(scene.sub_scenes)} sub-scene videos")
        sub_scene_results = []
        
        for idx, sub_scene in enumerate(scene.sub_scenes, 1):
            self.logger.info(
                f"Generating sub-scene {idx}/{len(scene.sub_scenes)}: {sub_scene.sub_scene_id}"
            )
            
            try:
                sub_video_result = await self._generate_subscene_video(
                    extracted_frame_path=str(extracted_frame_path),
                    sub_scene=sub_scene,
                    parent_scene=scene,
                    character_dict=character_dict
                )
                sub_scene_results.append(sub_video_result)
                self.logger.info(
                    f"Sub-scene video generated: {sub_video_result['video_path']}"
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to generate sub-scene {sub_scene.sub_scene_id}: {e}"
                )
                # 继续生成其他子场景，不因为一个失败而中断
                continue
        
        # Step 4: 拼接所有视频
        self.logger.info(
            f"Step 4/4: Concatenating base video with {len(sub_scene_results)} sub-scene videos"
        )
        
        # 准备要拼接的视频路径列表
        video_paths_to_concat = [base_video_path]
        video_paths_to_concat.extend([r['video_path'] for r in sub_scene_results])
        
        # 生成最终拼接视频的路径
        final_video_path = self.output_dir / f"{scene_id}_final_{timestamp}.mp4"
        
        try:
            self.ffmpeg_processor.concatenate_videos_filter(
                video_paths=video_paths_to_concat,
                output_path=str(final_video_path)
            )
            self.logger.info(f"Final scene video created: {final_video_path}")
        except Exception as e:
            self.logger.error(f"Failed to concatenate videos: {e}")
            raise
        
        # 构建返回结果
        return {
            'scene_id': scene_id,
            'video_path': str(final_video_path),
            'duration': scene.duration,
            'config': base_video_result['config'],
            'api_response': base_video_result['api_response'],
            'dialogues': [d.model_dump() for d in scene.dialogues],
            'has_subscenes': True,
            'base_video_path': base_video_path,
            'sub_scene_videos': [r['video_path'] for r in sub_scene_results],
            'extracted_frame_path': str(extracted_frame_path)
        }

    async def _generate_subscene_video(
        self,
        extracted_frame_path: str,
        sub_scene: SubScene,
        parent_scene: Scene,
        character_dict: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        生成单个子场景视频
        
        Args:
            extracted_frame_path: 从基础视频提取的帧图片路径
            sub_scene: 子场景对象
            parent_scene: 父场景对象
            character_dict: 角色字典
            
        Returns:
            子场景视频生成结果
        """
        sub_scene_id = sub_scene.sub_scene_id
        self.logger.info(f"Generating sub-scene video: {sub_scene_id}")
        
        # 检查子场景是否有自定义基础图
        image_path_to_use = extracted_frame_path
        if sub_scene.base_image_filename:
            custom_image_path = await self._load_custom_subscene_image(sub_scene)
            if custom_image_path:
                image_path_to_use = custom_image_path
                self.logger.info(f"Using custom base image for sub-scene: {custom_image_path}")
            else:
                self.logger.warning(
                    f"Failed to load custom base image for sub-scene {sub_scene_id}, "
                    f"using extracted frame instead"
                )
        
        # 生成子场景视频提示词
        video_prompt = sub_scene.to_video_prompt(parent_scene, character_dict)
        self.logger.debug(f"Sub-scene original prompt: {video_prompt}")
        
        # 使用LLM优化子场景提示词
        optimized_prompt = await self.prompt_optimizer.optimize_video_prompt(video_prompt)
        self.logger.debug(f"Sub-scene optimized prompt: {optimized_prompt}")
        
        # 配置视频参数（继承或使用子场景的设置）
        camera_movement = sub_scene.camera_movement if sub_scene.camera_movement else parent_scene.camera_movement
        
        video_config = {
            'fps': self.config.get('fps', 30),
            'resolution': self.config.get('resolution', '1920x1080'),
            'motion_strength': self.config.get('motion_strength', 0.5),
            'camera_motion': self._map_camera_motion(camera_movement),
            'prompt': optimized_prompt
        }
        
        if sub_scene.duration is not None:
            video_config['duration'] = sub_scene.duration
        
        # 调用Veo3 API生成子场景视频
        api_result = await self.service.image_to_video(
            image_path=image_path_to_use,
            **video_config
        )
        
        # 下载视频
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{sub_scene_id}_{timestamp}.mp4"
        save_path = self.output_dir / filename
        
        video_path = await self.service.download_video(
            api_result['video_url'],
            save_path
        )
        
        return {
            'sub_scene_id': sub_scene_id,
            'video_path': str(video_path),
            'duration': sub_scene.duration,
            'config': video_config,
            'api_response': api_result,
            'dialogues': [d.model_dump() for d in sub_scene.dialogues]
        }
    
    async def _load_custom_subscene_image(self, sub_scene: SubScene) -> Optional[str]:
        """
        加载子场景的自定义基础图
        
        Args:
            sub_scene: 子场景对象
            
        Returns:
            自定义图片路径，如果加载失败返回None
        """
        if not self.project_path:
            self.logger.error(
                f"Sub-scene {sub_scene.sub_scene_id} specifies custom base image "
                f"'{sub_scene.base_image_filename}', but project_path is not set."
            )
            return None
        
        # 构建自定义场景图路径
        scenes_folder = self.project_path / "scenes"
        custom_image_path = scenes_folder / sub_scene.base_image_filename
        
        if not custom_image_path.exists():
            self.logger.error(
                f"Custom base image not found for sub-scene {sub_scene.sub_scene_id}: "
                f"{custom_image_path}"
            )
            return None
        
        self.logger.info(
            f"Loading custom base image for sub-scene {sub_scene.sub_scene_id}: "
            f"{custom_image_path}"
        )
        
        # 复制图片到输出目录
        import shutil
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{sub_scene.sub_scene_id}_{timestamp}_custom.png"
        save_path = self.output_dir / filename
        
        try:
            shutil.copy2(custom_image_path, save_path)
            self.logger.info(f"Custom base image copied to: {save_path}")
            return str(save_path)
        except Exception as e:
            self.logger.error(f"Failed to copy custom base image: {e}")
            return None

    async def _generate_video_clip_once(
        self,
        image_path: str,
        scene: Scene,
        scene_id: str,
        character_dict: Optional[Dict[str, Any]],
        attempt: int,
        remove_dialogues: bool = False
    ) -> Dict[str, Any]:
        """
        执行一次视频片段生成

        Args:
            image_path: 图片路径
            scene: 场景对象
            scene_id: 场景ID
            character_dict: 角色字典
            attempt: 当前尝试次数（从0开始）
            remove_dialogues: 是否移除台词（用于音频过滤错误重试）

        Returns:
            视频生成结果
        """
        log_prefix = f"[Attempt {attempt + 1}] " if attempt > 0 else ""
        self.logger.info(f"{log_prefix}Generating video for scene: {scene_id}")

        # 如果需要移除台词，创建场景副本并清空对话
        if remove_dialogues and scene.dialogues:
            self.logger.info(f"Removing {len(scene.dialogues)} dialogue(s) from prompt due to audio filter")
            # 创建场景副本
            from copy import deepcopy
            scene = deepcopy(scene)
            scene.dialogues = []  # 清空对话列表

        # 生成视频提示词（包含对话信息）
        video_prompt = scene.to_video_prompt(character_dict)
        self.logger.debug(f"Original video prompt: {video_prompt}")

        # 使用LLM优化视频提示词
        optimized_video_prompt = await self.prompt_optimizer.optimize_video_prompt(video_prompt)
        self.logger.debug(f"Optimized video prompt: {optimized_video_prompt}")

        # 配置视频参数
        video_config = {
            'fps': self.config.get('fps', 30),
            'resolution': self.config.get('resolution', '1920x1080'),
            'motion_strength': self.config.get('motion_strength', 0.5),
            'camera_motion': self._map_camera_motion(scene.camera_movement),
            'prompt': optimized_video_prompt  # 使用优化后的提示词
        }

        # 只在scene指定了duration时才添加该参数，否则让视频模型自己决定时长
        if scene.duration is not None:
            video_config['duration'] = scene.duration

        # 调用Veo3 API生成视频
        api_result = await self.service.image_to_video(
            image_path=image_path,
            **video_config
        )

        # 下载视频
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{scene_id}_{timestamp}.mp4"
        save_path = self.output_dir / filename

        video_path = await self.service.download_video(
            api_result['video_url'],
            save_path
        )

        return {
            'scene_id': scene_id,
            'video_path': str(video_path),
            'duration': scene.duration,
            'config': video_config,
            'api_response': api_result,
            'dialogues': [d.model_dump() for d in scene.dialogues]  # 新增：保留对话数据
        }

    def _map_camera_motion(self, movement: CameraMovement) -> str:
        """
        将Scene的camera_movement映射到Veo3的参数

        Args:
            movement: CameraMovement枚举

        Returns:
            Veo3 API支持的运动类型
        """
        motion_mapping = {
            CameraMovement.STATIC: 'static',
            CameraMovement.PAN: 'pan',
            CameraMovement.TILT: 'tilt',
            CameraMovement.ZOOM: 'zoom',
            CameraMovement.DOLLY: 'dolly',
            CameraMovement.TRACKING: 'tracking'
        }

        return motion_mapping.get(movement, 'static')

    async def close(self):
        """关闭资源"""
        await self.service.close()
        await self.prompt_optimizer.close()
