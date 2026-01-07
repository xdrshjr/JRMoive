"""Video generation agent"""
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from agents.base_agent import BaseAgent
from services.veo3_service import Veo3Service
from models.script_models import Scene, CameraMovement
from utils.concurrency import ConcurrencyLimiter
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

        # 并发限制（Veo3生成较慢，建议降低并发数）
        max_concurrent = self.config.get('max_concurrent', 2)
        self.limiter = ConcurrencyLimiter(max_concurrent)

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
        生成单个视频片段

        Args:
            task_data: 包含image_result、scene和character_dict的字典

        Returns:
            视频生成结果
        """
        image_result = task_data['image_result']
        scene = task_data['scene']
        character_dict = task_data.get('character_dict')

        image_path = image_result['image_path']
        scene_id = scene.scene_id

        self.logger.info(f"Generating video for scene: {scene_id}")

        # 生成视频提示词（包含对话信息）
        video_prompt = scene.to_video_prompt(character_dict)
        self.logger.debug(f"Video prompt: {video_prompt}")

        # 配置视频参数
        video_config = {
            'fps': self.config.get('fps', 30),
            'resolution': self.config.get('resolution', '1920x1080'),
            'motion_strength': self.config.get('motion_strength', 0.5),
            'camera_motion': self._map_camera_motion(scene.camera_movement),
            'prompt': video_prompt  # 新增：传递视频提示词
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
