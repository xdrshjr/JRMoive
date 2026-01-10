"""
Drama Generation Orchestrator - 主控Agent协调器
"""

import asyncio
from typing import Dict, Any, Optional, Callable
from pathlib import Path
from agents.base_agent import BaseAgent
from agents.script_parser_agent import ScriptParserAgent
from agents.character_reference_agent import CharacterReferenceAgent
from agents.image_generator_agent import ImageGenerationAgent
from agents.video_generator_agent import VideoGenerationAgent
from agents.video_composer_agent import VideoComposerAgent
from models.script_models import Script
from config.settings import settings
import logging
import json
from datetime import datetime


class DramaGenerationOrchestrator(BaseAgent):
    """主控Agent - 协调整个短剧生成流程"""

    def __init__(
        self,
        agent_id: str = "orchestrator",
        config: Dict[str, Any] = None,
        output_dir: Optional[Path] = None,
        project_path: Optional[Path] = None
    ):
        super().__init__(agent_id, config or {})
        self.logger = logging.getLogger(__name__)

        # 设置输出目录（如果提供）
        self.output_dir = output_dir or Path("./output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置项目路径（用于加载自定义场景图）
        self.project_path = project_path

        # 设置项目特定日志
        self._setup_logging()

        # 构建各子目录路径
        char_ref_dir = self.output_dir / "character_references"
        images_dir = self.output_dir / "images"
        videos_dir = self.output_dir / "videos"
        final_dir = self.output_dir / "final"

        # 构建角色参考配置（合并settings和config）
        character_reference_config = {
            'character_reference_mode': settings.character_reference_mode,
            'reference_views': settings.reference_views,
            'reference_image_size': settings.reference_image_size,
            'reference_cfg_scale': settings.reference_cfg_scale,
            'reference_steps': settings.reference_steps,
            'character_art_style': settings.character_art_style,
            'max_reference_images': settings.max_reference_images,
        }
        # 允许config覆盖settings
        character_reference_config.update(self.config.get('character_reference', {}))

        # 初始化子Agent，传递输出目录
        self.script_parser = ScriptParserAgent()
        self.character_reference_agent = CharacterReferenceAgent(
            config=character_reference_config,
            output_dir=char_ref_dir
        )
        self.image_generator = ImageGenerationAgent(
            config=self.config.get('image', {}),
            output_dir=images_dir
        )
        self.video_generator = VideoGenerationAgent(
            config=self.config.get('video', {}),
            output_dir=videos_dir
        )
        self.video_composer = VideoComposerAgent(
            config=self.config.get('composer', {}),
            output_dir=final_dir
        )
        
        # 传递项目路径到agents（如果可用）
        if self.project_path:
            self.image_generator.set_project_path(self.project_path)
            self.video_generator.set_project_path(self.project_path)
            self.logger.info(f"Project path passed to agents: {self.project_path}")

        # 一致性控制开关
        self.enable_character_references = self.config.get(
            'enable_character_references',
            settings.enable_character_references
        )

        # 进度回调
        self.progress_callback: Optional[Callable] = None

        # 任务状态
        self.current_task_id: Optional[str] = None
        self.start_time: Optional[datetime] = None

    async def execute(
        self,
        script_text: str,
        output_filename: str = "drama.mp4",
        progress_callback: Optional[Callable] = None,
        character_images: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        执行完整的短剧生成流程

        Args:
            script_text: 剧本文本
            output_filename: 输出文件名
            progress_callback: 进度回调函数
            character_images: 角色图片配置字典（可选）
                格式: {character_name: {mode: "load"|"generate", images: [...], views: [...]}}

        Returns:
            最终视频文件路径
        """
        self.progress_callback = progress_callback
        self.start_time = datetime.now()
        self.current_task_id = f"drama_{self.start_time.strftime('%Y%m%d_%H%M%S')}"

        # 启动全局进度条（如果启用）
        if self.config.get('enable_global_progress_bar', False):
            from utils.global_progress_display import get_global_progress_display
            progress_display = get_global_progress_display()
            progress_display.start()

        try:
            # 步骤1：解析剧本 (0% -> 5%)
            await self._update_progress(0, "Starting drama generation...")
            await self._update_progress(1, "Parsing script...")

            script = await self.script_parser.execute(script_text)

            await self._update_progress(
                5,
                f"Script parsed: {script.total_scenes} scenes, "
                f"{len(script.characters)} characters"
                + (f", {script.total_duration:.1f}s duration" if script.total_duration else "")
            )

            # 步骤2：生成或加载角色参考图 (5% -> 15%)
            reference_data = None
            if self.enable_character_references and script.characters:
                if character_images:
                    # 检查是否有需要加载的图片
                    load_count = sum(
                        1 for cfg in character_images.values()
                        if cfg.get('mode') == 'load'
                    )
                    if load_count > 0:
                        await self._update_progress(
                            5, f"Processing character references ({load_count} load, "
                            f"{len(character_images) - load_count} generate)..."
                        )
                    else:
                        await self._update_progress(5, "Generating character reference sheets...")
                else:
                    await self._update_progress(5, "Generating character reference sheets...")

                try:
                    reference_data = await self.character_reference_agent.execute(
                        script.characters,
                        character_images=character_images
                    )

                    # 统计成功生成/加载的参考图数量
                    success_count = sum(
                        1 for char_data in reference_data.values()
                        if 'error' not in char_data
                    )

                    await self._update_progress(
                        15,
                        f"Processed references for {success_count}/{len(script.characters)} characters"
                    )

                except Exception as e:
                    self.logger.warning(f"Character reference processing failed: {e}")
                    self.logger.warning("Continuing with prompt-only enhancement")
                    reference_data = None
                    await self._update_progress(15, "Skipped character references (using prompt enhancement)")
            else:
                await self._update_progress(15, "Character references disabled, using prompt enhancement only")

            # 步骤3：生成分镜图片 (15% -> 45%)
            await self._update_progress(15, "Generating storyboard images with character consistency...")

            image_results = await self.image_generator.execute_concurrent(
                script.scenes,
                script=script,
                reference_data=reference_data,
                progress_callback=self._create_sub_progress_callback(15, 45)
            )
            
            # 统计使用自定义基础图的场景数量
            custom_image_count = sum(1 for result in image_results if result.get('from_custom_base', False))
            ai_generated_count = len(image_results) - custom_image_count
            
            if custom_image_count > 0:
                self.logger.info(
                    f"Image generation complete: {ai_generated_count} AI-generated, "
                    f"{custom_image_count} from custom base images"
                )

            await self._update_progress(
                45,
                f"Generated {len(image_results)} consistent images "
                f"({custom_image_count} custom)" if custom_image_count > 0 else f"Generated {len(image_results)} consistent images"
            )

            # 步骤4：生成视频片段 (45% -> 75%)
            await self._update_progress(45, "Converting images to videos...")

            # 构建角色字典，用于生成视频提示词
            character_dict = {char.name: char for char in script.characters}

            video_results = await self.video_generator.execute(
                image_results,
                script.scenes,
                character_dict=character_dict
            )

            await self._update_progress(
                75,
                f"Generated {len(video_results)} video clips"
            )

            # 步骤5：合成最终视频 (75% -> 95%)
            await self._update_progress(75, "Composing final video...")

            final_video_path = await self.video_composer.execute(
                video_results,
                output_filename=output_filename,
                bgm_path=self.config.get('bgm_path'),
                add_subtitles=self.config.get('add_subtitles', False)
            )

            await self._update_progress(95, "Saving metadata...")

            # 步骤6：保存元数据 (95% -> 100%)
            await self._save_metadata(script, final_video_path, reference_data)

            await self._update_progress(100, "Drama generation completed!")

            # 计算总耗时
            elapsed_time = (datetime.now() - self.start_time).total_seconds()
            self.logger.info(f"Total generation time: {elapsed_time:.2f}s")

            # 完成全局进度条（如果启用）
            if self.config.get('enable_global_progress_bar', False):
                from utils.global_progress_display import get_global_progress_display
                progress_display = get_global_progress_display()
                progress_display.finish()

            await self.on_complete(final_video_path)
            return final_video_path

        except Exception as e:
            self.logger.error(f"Drama generation failed: {e}")

            # 完成全局进度条（如果启用）
            if self.config.get('enable_global_progress_bar', False):
                from utils.global_progress_display import get_global_progress_display
                progress_display = get_global_progress_display()
                progress_display.finish()

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

    def _setup_logging(self):
        """
        设置项目特定日志配置

        根据config中的log_file和log_level配置日志处理器
        """
        log_file = self.config.get('log_file')
        log_level = self.config.get('log_level', 'INFO')

        if not log_file:
            # 如果未指定日志文件，使用默认路径
            log_file = self.output_dir / "generation.log"
        else:
            log_file = Path(log_file)

        # 确保日志文件的父目录存在
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # 配置根日志记录器
        root_logger = logging.getLogger()

        # 设置日志级别
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)
        root_logger.setLevel(numeric_level)

        # 检查是否已经存在文件处理器（避免重复添加）
        has_file_handler = any(
            isinstance(h, logging.FileHandler) and h.baseFilename == str(log_file.absolute())
            for h in root_logger.handlers
        )

        if not has_file_handler:
            # 创建文件处理器
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(numeric_level)

            # 设置格式
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)

            # 添加到根记录器
            root_logger.addHandler(file_handler)

            self.logger.info(f"Logging configured: level={log_level}, file={log_file}")

        # 如果启用了全局进度条，配置日志系统
        if self.config.get('enable_global_progress_bar', False):
            from utils.global_progress_display import configure_logging_with_progress_bar
            configure_logging_with_progress_bar(
                log_level=numeric_level,
                log_file=str(log_file)
            )

    async def _update_progress(self, percent: float, message: str):
        """
        更新进度

        Args:
            percent: 进度百分比（0-100）
            message: 进度消息
        """
        self.logger.info(f"Progress: {percent}% - {message}")

        # 更新全局进度条（如果启用）
        if self.config.get('enable_global_progress_bar', False):
            from utils.global_progress_display import get_global_progress_display
            progress_display = get_global_progress_display()
            progress_display.update(percent, message)

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

    async def _save_metadata(self, script: Script, video_path: str, reference_data: Optional[Dict] = None):
        """
        保存生成元数据

        Args:
            script: 剧本对象
            video_path: 视频文件路径
            reference_data: 角色参考数据（可选）
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
                'consistency': {
                    'character_references_enabled': self.enable_character_references,
                    'references_generated': reference_data is not None,
                    'character_reference_count': len(reference_data) if reference_data else 0
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
            await self.character_reference_agent.close()
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
