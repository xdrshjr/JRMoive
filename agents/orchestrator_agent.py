"""
Drama Generation Orchestrator - 主控Agent协调器
"""

import asyncio
from typing import Dict, Any, Optional, Callable
from pathlib import Path
from agents.base_agent import BaseAgent
from agents.script_parser_agent import ScriptParserAgent
from agents.image_generator_agent import ImageGenerationAgent
from agents.video_generator_agent import VideoGenerationAgent
from agents.video_composer_agent import VideoComposerAgent
from models.script_models import Script
import logging
import json
from datetime import datetime


class DramaGenerationOrchestrator(BaseAgent):
    """主控Agent - 协调整个短剧生成流程"""

    def __init__(
        self,
        agent_id: str = "orchestrator",
        config: Dict[str, Any] = None
    ):
        super().__init__(agent_id, config or {})
        self.logger = logging.getLogger(__name__)

        # 初始化子Agent
        self.script_parser = ScriptParserAgent()
        self.image_generator = ImageGenerationAgent(config=config.get('image', {}))
        self.video_generator = VideoGenerationAgent(config=config.get('video', {}))
        self.video_composer = VideoComposerAgent(config=config.get('composer', {}))

        # 进度回调
        self.progress_callback: Optional[Callable] = None

        # 任务状态
        self.current_task_id: Optional[str] = None
        self.start_time: Optional[datetime] = None

    async def execute(
        self,
        script_text: str,
        output_filename: str = "drama.mp4",
        progress_callback: Optional[Callable] = None
    ) -> str:
        """
        执行完整的短剧生成流程

        Args:
            script_text: 剧本文本
            output_filename: 输出文件名
            progress_callback: 进度回调函数

        Returns:
            最终视频文件路径
        """
        self.progress_callback = progress_callback
        self.start_time = datetime.now()
        self.current_task_id = f"drama_{self.start_time.strftime('%Y%m%d_%H%M%S')}"

        try:
            # 步骤1：解析剧本 (0% -> 10%)
            await self._update_progress(0, "Starting drama generation...")
            await self._update_progress(1, "Parsing script...")

            script = await self.script_parser.execute(script_text)

            await self._update_progress(
                10,
                f"Script parsed: {script.total_scenes} scenes, "
                f"{script.total_duration:.1f}s duration"
            )

            # 步骤2：生成分镜图片 (10% -> 40%)
            await self._update_progress(10, "Generating storyboard images...")

            image_results = await self.image_generator.execute_concurrent(
                script.scenes,
                progress_callback=self._create_sub_progress_callback(10, 40)
            )

            await self._update_progress(
                40,
                f"Generated {len(image_results)} images successfully"
            )

            # 步骤3：生成视频片段 (40% -> 70%)
            await self._update_progress(40, "Converting images to videos...")

            video_results = await self.video_generator.execute(
                image_results,
                script.scenes
            )

            await self._update_progress(
                70,
                f"Generated {len(video_results)} video clips"
            )

            # 步骤4：合成最终视频 (70% -> 95%)
            await self._update_progress(70, "Composing final video...")

            final_video_path = await self.video_composer.execute(
                video_results,
                output_filename=output_filename,
                bgm_path=self.config.get('bgm_path'),
                add_subtitles=self.config.get('add_subtitles', False)
            )

            await self._update_progress(95, "Saving metadata...")

            # 步骤5：保存元数据 (95% -> 100%)
            await self._save_metadata(script, final_video_path)

            await self._update_progress(100, "Drama generation completed!")

            # 计算总耗时
            elapsed_time = (datetime.now() - self.start_time).total_seconds()
            self.logger.info(f"Total generation time: {elapsed_time:.2f}s")

            await self.on_complete(final_video_path)
            return final_video_path

        except Exception as e:
            self.logger.error(f"Drama generation failed: {e}")
            await self.on_error(e)
            raise

    async def validate_input(self, script_text: str) -> bool:
        """验证输入剧本"""
        if not script_text or not isinstance(script_text, str):
            return False

        if len(script_text.strip()) < 10:
            self.logger.error("Script text too short")
            return False

        return True

    async def _update_progress(self, percent: float, message: str):
        """
        更新进度

        Args:
            percent: 进度百分比（0-100）
            message: 进度消息
        """
        self.logger.info(f"Progress: {percent}% - {message}")

        if self.progress_callback:
            if asyncio.iscoroutinefunction(self.progress_callback):
                await self.progress_callback(percent, message)
            else:
                self.progress_callback(percent, message)

    def _create_sub_progress_callback(
        self,
        start_percent: float,
        end_percent: float
    ) -> Callable:
        """
        创建子任务的进度回调

        Args:
            start_percent: 起始百分比
            end_percent: 结束百分比

        Returns:
            进度回调函数
        """
        async def sub_progress_callback(sub_percent: float, message: str):
            # 将子任务进度映射到总进度
            total_percent = start_percent + (end_percent - start_percent) * (sub_percent / 100)
            await self._update_progress(total_percent, message)

        return sub_progress_callback

    async def _save_metadata(self, script: Script, video_path: str):
        """
        保存生成元数据

        Args:
            script: 剧本对象
            video_path: 视频文件路径
        """
        try:
            metadata = {
                'task_id': self.current_task_id,
                'generated_at': datetime.now().isoformat(),
                'script_info': {
                    'title': script.title,
                    'total_scenes': script.total_scenes,
                    'total_duration': script.total_duration,
                    'character_count': len(script.characters)
                },
                'output': {
                    'video_path': video_path,
                    'filename': Path(video_path).name
                },
                'config': self.config,
                'generation_time': (datetime.now() - self.start_time).total_seconds()
            }

            # 保存元数据
            metadata_path = Path(video_path).with_suffix('.json')

            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Metadata saved: {metadata_path}")

        except Exception as e:
            self.logger.error(f"Failed to save metadata: {e}")
            # 不抛出异常，因为元数据保存失败不应影响主流程

    async def get_task_status(self) -> Dict[str, Any]:
        """
        获取当前任务状态

        Returns:
            任务状态信息
        """
        if not self.current_task_id:
            return {
                'status': 'idle',
                'message': 'No task running'
            }

        elapsed_time = (datetime.now() - self.start_time).total_seconds()

        return {
            'task_id': self.current_task_id,
            'status': self.state.value,
            'elapsed_time': elapsed_time,
            'start_time': self.start_time.isoformat()
        }

    async def cancel_task(self):
        """取消当前任务"""
        if self.current_task_id:
            self.logger.warning(f"Canceling task: {self.current_task_id}")
            self.current_task_id = None
            # 这里可以添加更多的清理逻辑

    async def close(self):
        """关闭所有子Agent资源"""
        try:
            await self.image_generator.close()
            await self.video_generator.close()
            await self.video_composer.close()
            self.logger.info("Orchestrator closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing orchestrator: {e}")


class SimpleDramaGenerator:
    """简化的短剧生成接口（用于快速使用）"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化生成器

        Args:
            config: 配置字典
        """
        self.orchestrator = DramaGenerationOrchestrator(config=config or {})
        self.logger = logging.getLogger(__name__)

    async def generate_from_file(
        self,
        script_file: str,
        output_file: str = "output.mp4",
        progress_callback: Optional[Callable] = None
    ) -> str:
        """
        从剧本文件生成视频

        Args:
            script_file: 剧本文件路径
            output_file: 输出视频文件名
            progress_callback: 进度回调

        Returns:
            生成的视频文件路径
        """
        # 读取剧本文件
        with open(script_file, 'r', encoding='utf-8') as f:
            script_text = f.read()

        # 生成视频
        return await self.generate(script_text, output_file, progress_callback)

    async def generate(
        self,
        script_text: str,
        output_file: str = "output.mp4",
        progress_callback: Optional[Callable] = None
    ) -> str:
        """
        从剧本文本生成视频

        Args:
            script_text: 剧本文本
            output_file: 输出视频文件名
            progress_callback: 进度回调

        Returns:
            生成的视频文件路径
        """
        try:
            return await self.orchestrator.execute(
                script_text,
                output_filename=output_file,
                progress_callback=progress_callback
            )
        except Exception as e:
            self.logger.error(f"Generation failed: {e}")
            raise

    async def close(self):
        """关闭生成器"""
        await self.orchestrator.close()
