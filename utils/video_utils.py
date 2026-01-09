"""
FFmpeg video processing utilities
"""

import ffmpeg
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
import subprocess
import os


class FFmpegProcessor:
    """FFmpeg视频处理工具类"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """
        获取视频信息

        Args:
            video_path: 视频文件路径

        Returns:
            视频元数据字典
        """
        try:
            probe = ffmpeg.probe(video_path)
            video_stream = next(
                (s for s in probe['streams'] if s['codec_type'] == 'video'),
                None
            )

            if not video_stream:
                raise ValueError("No video stream found")

            return {
                'duration': float(probe['format']['duration']),
                'width': int(video_stream['width']),
                'height': int(video_stream['height']),
                'fps': eval(video_stream['r_frame_rate']),
                'codec': video_stream['codec_name'],
                'bitrate': int(probe['format'].get('bit_rate', 0))
            }

        except ffmpeg.Error as e:
            self.logger.error(f"Failed to probe video: {e.stderr.decode()}")
            raise

    def convert_video(
        self,
        input_path: str,
        output_path: str,
        vcodec: str = 'libx264',
        acodec: str = 'aac',
        preset: str = 'medium',
        crf: int = 23
    ) -> str:
        """
        转换视频格式

        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            vcodec: 视频编码器
            acodec: 音频编码器
            preset: 编码预设
            crf: 质量参数（0-51，越小质量越高）

        Returns:
            输出文件路径
        """
        try:
            stream = ffmpeg.input(input_path)
            stream = ffmpeg.output(
                stream,
                output_path,
                vcodec=vcodec,
                acodec=acodec,
                preset=preset,
                crf=crf
            )
            ffmpeg.run(stream, overwrite_output=True, quiet=True)

            self.logger.info(f"Video converted: {output_path}")
            return output_path

        except ffmpeg.Error as e:
            self.logger.error(f"Conversion failed: {e.stderr.decode()}")
            raise

    def resize_video(
        self,
        input_path: str,
        output_path: str,
        width: int,
        height: int
    ) -> str:
        """
        调整视频分辨率

        Args:
            input_path: 输入视频
            output_path: 输出视频
            width: 目标宽度
            height: 目标高度

        Returns:
            输出文件路径
        """
        try:
            stream = ffmpeg.input(input_path)
            stream = ffmpeg.filter(stream, 'scale', width, height)
            stream = ffmpeg.output(stream, output_path)
            ffmpeg.run(stream, overwrite_output=True, quiet=True)

            return output_path

        except ffmpeg.Error as e:
            self.logger.error(f"Resize failed: {e.stderr.decode()}")
            raise

    def add_audio(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        audio_volume: float = 1.0
    ) -> str:
        """
        为视频添加音频

        Args:
            video_path: 视频文件
            audio_path: 音频文件
            output_path: 输出文件
            audio_volume: 音频音量（0.0-1.0）

        Returns:
            输出文件路径
        """
        try:
            video = ffmpeg.input(video_path)
            audio = ffmpeg.input(audio_path)

            # 调整音量
            if audio_volume != 1.0:
                audio = ffmpeg.filter(audio, 'volume', audio_volume)

            stream = ffmpeg.output(
                video,
                audio,
                output_path,
                vcodec='copy',
                acodec='aac',
                shortest=None
            )

            ffmpeg.run(stream, overwrite_output=True, quiet=True)
            return output_path

        except ffmpeg.Error as e:
            self.logger.error(f"Add audio failed: {e.stderr.decode()}")
            raise

    def concatenate_videos_filter(
        self,
        video_paths: List[str],
        output_path: str
    ) -> str:
        """
        使用filter方式拼接视频（适合需要转场效果的场景）

        Args:
            video_paths: 视频文件路径列表
            output_path: 输出文件路径

        Returns:
            输出文件路径
        """
        try:
            self.logger.info(f"Starting video concatenation for {len(video_paths)} videos")
            
            # 检测每个输入视频的音频流
            has_audio_streams = []
            for i, video_path in enumerate(video_paths):
                try:
                    probe = ffmpeg.probe(video_path)
                    has_audio = any(s['codec_type'] == 'audio' for s in probe['streams'])
                    has_audio_streams.append(has_audio)
                    self.logger.debug(f"Video {i+1}/{len(video_paths)} ({Path(video_path).name}): has_audio={has_audio}")
                    if not has_audio:
                        self.logger.warning(f"Video {i+1} has no audio stream: {video_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to probe video {i+1}: {e}")
                    has_audio_streams.append(False)
            
            # 创建输入流并提取视频和音频流
            video_streams = []
            audio_streams = []
            
            for i, video_path in enumerate(video_paths):
                input_stream = ffmpeg.input(video_path)
                video_streams.append(input_stream.video)
                
                # 只有当视频有音频流时才添加
                if has_audio_streams[i]:
                    audio_streams.append(input_stream.audio)
                else:
                    # 为没有音频的视频创建静音音频流
                    silent_audio = ffmpeg.filter(
                        input_stream,
                        'anullsrc',
                        channel_layout='stereo',
                        sample_rate=44100
                    )
                    silent_audio = ffmpeg.filter(
                        [silent_audio, input_stream],
                        'atrim',
                        duration='shortest'
                    )
                    audio_streams.append(silent_audio)
            
            # 拼接所有视频流和音频流
            joined_video = ffmpeg.concat(*video_streams, v=1, a=0)
            joined_audio = ffmpeg.concat(*audio_streams, v=0, a=1)

            stream = ffmpeg.output(
                joined_video,
                joined_audio,
                output_path,
                vcodec='libx264',
                acodec='aac',
                preset='medium',
                audio_bitrate='192k'
            )

            ffmpeg.run(stream, overwrite_output=True, quiet=True)

            self.logger.info(f"Videos concatenated with audio successfully: {output_path}")
            return output_path

        except ffmpeg.Error as e:
            self.logger.error(f"Concatenation failed: {e.stderr.decode()}")
            raise

    def concatenate_videos_demuxer(
        self,
        video_paths: List[str],
        output_path: str
    ) -> str:
        """
        使用demuxer方式拼接视频（更快，但要求视频参数一致）

        Args:
            video_paths: 视频文件路径列表
            output_path: 输出文件路径

        Returns:
            输出文件路径
        """
        try:
            # 创建临时文件列表
            temp_list_file = Path(output_path).parent / "concat_list.txt"

            with open(temp_list_file, 'w', encoding='utf-8') as f:
                for video_path in video_paths:
                    # 使用绝对路径
                    abs_path = os.path.abspath(video_path)
                    f.write(f"file '{abs_path}'\n")

            # 使用concat demuxer
            stream = ffmpeg.input(str(temp_list_file), format='concat', safe=0)
            stream = ffmpeg.output(stream, output_path, c='copy')
            ffmpeg.run(stream, overwrite_output=True, quiet=True)

            # 删除临时文件
            temp_list_file.unlink()

            self.logger.info(f"Videos concatenated (demuxer): {output_path}")
            return output_path

        except ffmpeg.Error as e:
            self.logger.error(f"Concatenation failed: {e.stderr.decode()}")
            raise
        finally:
            # 确保临时文件被删除
            if temp_list_file.exists():
                temp_list_file.unlink()

    def trim_video(
        self,
        input_path: str,
        output_path: str,
        start_time: float,
        end_time: float
    ) -> str:
        """
        裁剪视频

        Args:
            input_path: 输入视频
            output_path: 输出视频
            start_time: 开始时间（秒）
            end_time: 结束时间（秒）

        Returns:
            输出文件路径
        """
        try:
            stream = ffmpeg.input(input_path, ss=start_time, to=end_time)
            stream = ffmpeg.output(stream, output_path, c='copy')
            ffmpeg.run(stream, overwrite_output=True, quiet=True)

            self.logger.info(f"Video trimmed: {output_path}")
            return output_path

        except ffmpeg.Error as e:
            self.logger.error(f"Trim failed: {e.stderr.decode()}")
            raise

    def extract_audio(
        self,
        video_path: str,
        output_path: str,
        audio_format: str = 'mp3'
    ) -> str:
        """
        从视频中提取音频

        Args:
            video_path: 视频文件路径
            output_path: 输出音频路径
            audio_format: 音频格式

        Returns:
            输出文件路径
        """
        try:
            stream = ffmpeg.input(video_path)
            stream = ffmpeg.output(stream, output_path, acodec='libmp3lame' if audio_format == 'mp3' else 'aac')
            ffmpeg.run(stream, overwrite_output=True, quiet=True)

            self.logger.info(f"Audio extracted: {output_path}")
            return output_path

        except ffmpeg.Error as e:
            self.logger.error(f"Audio extraction failed: {e.stderr.decode()}")
            raise

    def add_watermark(
        self,
        video_path: str,
        watermark_path: str,
        output_path: str,
        position: str = 'bottom-right',
        opacity: float = 0.5
    ) -> str:
        """
        添加水印

        Args:
            video_path: 视频文件路径
            watermark_path: 水印图片路径
            output_path: 输出文件路径
            position: 水印位置 (top-left, top-right, bottom-left, bottom-right, center)
            opacity: 不透明度 (0.0-1.0)

        Returns:
            输出文件路径
        """
        try:
            video = ffmpeg.input(video_path)
            watermark = ffmpeg.input(watermark_path)

            # 设置水印透明度
            watermark = ffmpeg.filter(watermark, 'format', 'rgba')
            watermark = ffmpeg.filter(watermark, 'colorchannelmixer', aa=opacity)

            # 设置水印位置
            position_map = {
                'top-left': '10:10',
                'top-right': 'W-w-10:10',
                'bottom-left': '10:H-h-10',
                'bottom-right': 'W-w-10:H-h-10',
                'center': '(W-w)/2:(H-h)/2'
            }
            overlay_pos = position_map.get(position, 'W-w-10:H-h-10')

            # 叠加水印
            stream = ffmpeg.overlay(video, watermark, x=overlay_pos.split(':')[0], y=overlay_pos.split(':')[1])
            stream = ffmpeg.output(stream, output_path, vcodec='libx264', preset='medium')
            ffmpeg.run(stream, overwrite_output=True, quiet=True)

            self.logger.info(f"Watermark added: {output_path}")
            return output_path

        except ffmpeg.Error as e:
            self.logger.error(f"Add watermark failed: {e.stderr.decode()}")
            raise

    def create_thumbnail(
        self,
        video_path: str,
        output_path: str,
        timestamp: float = 1.0
    ) -> str:
        """
        创建视频缩略图

        Args:
            video_path: 视频文件路径
            output_path: 输出图片路径
            timestamp: 截图时间点（秒）

        Returns:
            输出文件路径
        """
        try:
            stream = ffmpeg.input(video_path, ss=timestamp)
            stream = ffmpeg.output(stream, output_path, vframes=1)
            ffmpeg.run(stream, overwrite_output=True, quiet=True)

            self.logger.info(f"Thumbnail created: {output_path}")
            return output_path

        except ffmpeg.Error as e:
            self.logger.error(f"Thumbnail creation failed: {e.stderr.decode()}")
            raise

    def extract_frame(
        self,
        video_path: str,
        frame_index: int,
        output_path: str
    ) -> str:
        """
        从视频中提取指定帧作为图片
        
        Args:
            video_path: 视频文件路径
            frame_index: 帧索引（负数表示从末尾倒数，如-5表示倒数第5帧）
            output_path: 输出图片路径
            
        Returns:
            输出文件路径
        """
        try:
            # 获取视频信息
            video_info = self.get_video_info(video_path)
            fps = video_info['fps']
            duration = video_info['duration']
            total_frames = int(duration * fps)
            
            # 处理负数索引（从末尾倒数）
            if frame_index < 0:
                actual_frame_index = total_frames + frame_index
            else:
                actual_frame_index = frame_index
            
            # 确保帧索引在有效范围内
            actual_frame_index = max(0, min(actual_frame_index, total_frames - 1))
            
            # 计算时间戳
            timestamp = actual_frame_index / fps
            
            self.logger.info(
                f"Extracting frame {actual_frame_index} (original index: {frame_index}) "
                f"at timestamp {timestamp:.2f}s from {video_path}"
            )
            
            # 使用ffmpeg提取帧
            stream = ffmpeg.input(video_path, ss=timestamp)
            stream = ffmpeg.output(
                stream, 
                output_path, 
                vframes=1,
                format='image2',
                vcodec='png'
            )
            ffmpeg.run(stream, overwrite_output=True, quiet=True)
            
            self.logger.info(f"Frame extracted successfully: {output_path}")
            return output_path
            
        except ffmpeg.Error as e:
            self.logger.error(f"Frame extraction failed: {e.stderr.decode()}")
            raise
        except Exception as e:
            self.logger.error(f"Frame extraction failed: {str(e)}")
            raise
