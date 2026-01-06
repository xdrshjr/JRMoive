"""
Video Composer Agent - 视频合成Agent
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from agents.base_agent import BaseAgent
from moviepy import (
    VideoFileClip,
    concatenate_videoclips,
    CompositeVideoClip,
    AudioFileClip,
    TextClip
)
from utils.video_utils import FFmpegProcessor
import logging


class VideoComposerAgent(BaseAgent):
    """视频合成Agent - 将所有片段合成为完整短剧"""

    def __init__(
        self,
        agent_id: str = "video_composer",
        config: Dict[str, Any] = None,
        output_dir: Optional[Path] = None
    ):
        super().__init__(agent_id, config or {})
        self.output_dir = output_dir or Path("./output/final")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.ffmpeg = FFmpegProcessor()
        self.logger = logging.getLogger(__name__)

    async def execute(
        self,
        video_results: List[Dict[str, Any]],
        output_filename: str = "final_drama.mp4",
        bgm_path: Optional[str] = None,
        add_subtitles: bool = False
    ) -> str:
        """
        执行视频合成

        Args:
            video_results: 视频片段结果列表
            output_filename: 输出文件名
            bgm_path: 背景音乐路径（可选）
            add_subtitles: 是否添加字幕

        Returns:
            最终视频路径
        """
        if not await self.validate_input(video_results):
            raise ValueError("Invalid video results")

        self.logger.info(f"Starting video composition with {len(video_results)} clips")

        try:
            # 按scene_id排序
            video_results = sorted(video_results, key=lambda x: x['scene_id'])

            # 加载视频片段
            clips = self._load_video_clips(video_results)

            # 添加转场效果
            if self.config.get('add_transitions', False):
                clips = self._add_transitions(clips)

            # 拼接视频
            final_clip = concatenate_videoclips(clips, method="compose")

            # 添加背景音乐
            if bgm_path:
                final_clip = self._add_background_music(final_clip, bgm_path)

            # 添加字幕
            if add_subtitles:
                final_clip = self._add_subtitles(final_clip, video_results)

            # 输出最终视频
            output_path = self.output_dir / output_filename
            final_clip.write_videofile(
                str(output_path),
                codec='libx264',
                audio_codec='aac',
                fps=self.config.get('fps', 30),
                preset=self.config.get('preset', 'medium'),
                threads=self.config.get('threads', 4)
            )

            # 清理资源
            final_clip.close()
            for clip in clips:
                clip.close()

            self.logger.info(f"Video composition completed: {output_path}")

            await self.on_complete(str(output_path))
            return str(output_path)

        except Exception as e:
            await self.on_error(e)
            raise

    async def validate_input(self, video_results: List[Dict[str, Any]]) -> bool:
        """验证输入数据"""
        if not video_results:
            return False

        # 检查所有视频文件是否存在
        for result in video_results:
            video_path = result.get('video_path')
            if not video_path or not Path(video_path).exists():
                self.logger.error(f"Video file not found: {video_path}")
                return False

        return True

    def _load_video_clips(self, video_results: List[Dict[str, Any]]) -> List[VideoFileClip]:
        """加载视频片段"""
        clips = []

        for result in video_results:
            video_path = result['video_path']
            self.logger.info(f"Loading clip: {video_path}")

            clip = VideoFileClip(video_path)
            clips.append(clip)

        return clips

    def _add_transitions(self, clips: List[VideoFileClip]) -> List[VideoFileClip]:
        """
        添加转场效果

        支持的转场类型：
        - fade: 淡入淡出
        - crossfade: 交叉淡化
        """
        transition_type = self.config.get('transition_type', 'fade')
        transition_duration = self.config.get('transition_duration', 0.5)

        if transition_type == 'crossfade':
            return self._apply_crossfade(clips, transition_duration)
        elif transition_type == 'fade':
            return self._apply_fade(clips, transition_duration)
        else:
            return clips

    def _apply_fade(
        self,
        clips: List[VideoFileClip],
        duration: float
    ) -> List[VideoFileClip]:
        """应用淡入淡出效果"""
        processed = []

        for clip in clips:
            # 添加淡入淡出
            clip = clip.fadein(duration).fadeout(duration)
            processed.append(clip)

        return processed

    def _apply_crossfade(
        self,
        clips: List[VideoFileClip],
        duration: float
    ) -> List[VideoFileClip]:
        """应用交叉淡化效果"""
        if len(clips) <= 1:
            return clips

        processed = [clips[0].fadein(duration)]

        for i in range(1, len(clips)):
            # 当前片段淡入，前一片段会淡出
            clip = clips[i].fadein(duration)
            processed.append(clip)

        processed[-1] = processed[-1].fadeout(duration)

        return processed

    def _add_background_music(
        self,
        video_clip: VideoFileClip,
        bgm_path: str
    ) -> VideoFileClip:
        """
        添加背景音乐

        Args:
            video_clip: 视频片段
            bgm_path: 背景音乐路径

        Returns:
            添加了BGM的视频片段
        """
        self.logger.info(f"Adding background music: {bgm_path}")

        try:
            audio = AudioFileClip(bgm_path)

            # 如果音乐较短，循环播放
            if audio.duration < video_clip.duration:
                n_loops = int(video_clip.duration / audio.duration) + 1
                audio = audio.loop(n_loops)

            # 截取到视频长度
            audio = audio.subclip(0, video_clip.duration)

            # 降低音量（避免盖过对话）
            audio = audio.volumex(self.config.get('bgm_volume', 0.3))

            # 合并音频
            if video_clip.audio:
                # 混合原音频和BGM
                from moviepy.audio.AudioClip import CompositeAudioClip
                final_audio = CompositeAudioClip([video_clip.audio, audio])
                video_clip = video_clip.set_audio(final_audio)
            else:
                video_clip = video_clip.set_audio(audio)

            return video_clip

        except Exception as e:
            self.logger.error(f"Failed to add BGM: {e}")
            return video_clip

    def _add_subtitles(
        self,
        video_clip: VideoFileClip,
        video_results: List[Dict[str, Any]]
    ) -> VideoFileClip:
        """
        添加字幕

        Args:
            video_clip: 视频片段
            video_results: 视频结果（包含字幕信息）

        Returns:
            添加了字幕的视频片段
        """
        self.logger.info("Adding subtitles")

        # 这里需要根据实际的字幕数据格式实现
        # 示例：假设video_results中包含字幕文本和时间戳

        subtitle_clips = []
        current_time = 0

        for result in video_results:
            # 从scene数据中提取对话
            if 'dialogues' in result:
                for dialogue in result['dialogues']:
                    txt_clip = TextClip(
                        dialogue['content'],
                        fontsize=self.config.get('subtitle_fontsize', 24),
                        color='white',
                        font=self.config.get('subtitle_font', 'Arial'),
                        stroke_color='black',
                        stroke_width=2
                    )

                    # 设置字幕位置和时长
                    txt_clip = txt_clip.set_position(('center', 'bottom'))
                    txt_clip = txt_clip.set_start(current_time)
                    txt_clip = txt_clip.set_duration(dialogue.get('duration', 2.0))

                    subtitle_clips.append(txt_clip)
                    current_time += dialogue.get('duration', 2.0)

        if subtitle_clips:
            # 合成字幕和视频
            video_clip = CompositeVideoClip([video_clip] + subtitle_clips)

        return video_clip

    async def close(self):
        """关闭资源"""
        pass
