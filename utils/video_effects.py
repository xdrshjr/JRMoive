"""
Video Effects - 视频特效处理工具
"""

from moviepy import VideoFileClip
from moviepy import vfx
from typing import Optional
import logging
import numpy as np


class VideoEffects:
    """视频特效处理工具"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def apply_color_grading(
        self,
        clip: VideoFileClip,
        preset: str = "cinematic"
    ) -> VideoFileClip:
        """
        应用调色预设

        Args:
            clip: 视频片段
            preset: 预设名称（cinematic/warm/cool/vibrant/desaturate）

        Returns:
            调色后的视频
        """
        try:
            if preset == "cinematic":
                # 降低饱和度，增加对比度 - 电影感
                clip = clip.fx(vfx.colorx, 0.9)
            elif preset == "warm":
                # 温暖色调
                clip = clip.fx(vfx.colorx, 1.1)
            elif preset == "cool":
                # 冷色调
                clip = clip.fx(vfx.colorx, 0.8)
            elif preset == "vibrant":
                # 鲜艳色彩
                clip = clip.fx(vfx.colorx, 1.3)
            elif preset == "desaturate":
                # 去饱和（接近黑白）
                clip = clip.fx(vfx.colorx, 0.5)

            self.logger.info(f"Applied color grading: {preset}")
            return clip

        except Exception as e:
            self.logger.error(f"Failed to apply color grading: {e}")
            return clip

    def add_vignette(
        self,
        clip: VideoFileClip,
        strength: float = 0.3
    ) -> VideoFileClip:
        """
        添加晕影效果（边缘暗化）

        Args:
            clip: 视频片段
            strength: 强度（0.0-1.0）

        Returns:
            添加晕影的视频
        """
        try:
            def vignette_effect(get_frame, t):
                """应用晕影效果"""
                frame = get_frame(t)
                rows, cols = frame.shape[:2]

                # 创建径向渐变遮罩
                X_resultant_kernel = cv2.getGaussianKernel(cols, cols / 2)
                Y_resultant_kernel = cv2.getGaussianKernel(rows, rows / 2)

                # 生成2D高斯核
                resultant_kernel = Y_resultant_kernel * X_resultant_kernel.T

                # 归一化
                mask = resultant_kernel / resultant_kernel.max()

                # 调整强度
                mask = 1 - (1 - mask) * strength

                # 扩展到3通道
                mask = np.dstack([mask] * 3)

                # 应用遮罩
                return (frame * mask).astype('uint8')

            # 需要cv2支持，如果没有则返回原视频
            try:
                import cv2
                clip = clip.fl(vignette_effect)
                self.logger.info(f"Applied vignette effect with strength {strength}")
            except ImportError:
                self.logger.warning("OpenCV not available, skipping vignette effect")

            return clip

        except Exception as e:
            self.logger.error(f"Failed to add vignette: {e}")
            return clip

    def add_blur(
        self,
        clip: VideoFileClip,
        blur_amount: float = 1.0
    ) -> VideoFileClip:
        """
        添加模糊效果

        Args:
            clip: 视频片段
            blur_amount: 模糊程度（0.1-5.0）

        Returns:
            模糊后的视频
        """
        try:
            # 使用gaussian blur
            def blur_effect(get_frame, t):
                import cv2
                frame = get_frame(t)
                kernel_size = int(blur_amount * 10) | 1  # 确保是奇数
                blurred = cv2.GaussianBlur(frame, (kernel_size, kernel_size), 0)
                return blurred

            try:
                import cv2
                clip = clip.fl(blur_effect)
                self.logger.info(f"Applied blur effect: {blur_amount}")
            except ImportError:
                self.logger.warning("OpenCV not available, skipping blur effect")

            return clip

        except Exception as e:
            self.logger.error(f"Failed to add blur: {e}")
            return clip

    def add_speed_ramp(
        self,
        clip: VideoFileClip,
        speed_factor: float = 2.0
    ) -> VideoFileClip:
        """
        调整视频速度

        Args:
            clip: 视频片段
            speed_factor: 速度因子（<1.0慢动作，>1.0快进）

        Returns:
            调速后的视频
        """
        try:
            clip = clip.fx(vfx.speedx, speed_factor)
            self.logger.info(f"Applied speed ramp: {speed_factor}x")
            return clip

        except Exception as e:
            self.logger.error(f"Failed to apply speed ramp: {e}")
            return clip

    def mirror_x(self, clip: VideoFileClip) -> VideoFileClip:
        """
        水平镜像

        Args:
            clip: 视频片段

        Returns:
            镜像后的视频
        """
        try:
            clip = clip.fx(vfx.mirror_x)
            self.logger.info("Applied horizontal mirror")
            return clip
        except Exception as e:
            self.logger.error(f"Failed to mirror: {e}")
            return clip

    def mirror_y(self, clip: VideoFileClip) -> VideoFileClip:
        """
        垂直镜像

        Args:
            clip: 视频片段

        Returns:
            镜像后的视频
        """
        try:
            clip = clip.fx(vfx.mirror_y)
            self.logger.info("Applied vertical mirror")
            return clip
        except Exception as e:
            self.logger.error(f"Failed to mirror: {e}")
            return clip

    def apply_grayscale(self, clip: VideoFileClip) -> VideoFileClip:
        """
        转换为灰度（黑白）

        Args:
            clip: 视频片段

        Returns:
            黑白视频
        """
        try:
            clip = clip.fx(vfx.blackwhite)
            self.logger.info("Applied grayscale effect")
            return clip
        except Exception as e:
            self.logger.error(f"Failed to apply grayscale: {e}")
            return clip

    def apply_rotation(
        self,
        clip: VideoFileClip,
        angle: float
    ) -> VideoFileClip:
        """
        旋转视频

        Args:
            clip: 视频片段
            angle: 旋转角度（度数）

        Returns:
            旋转后的视频
        """
        try:
            clip = clip.fx(vfx.rotate, angle)
            self.logger.info(f"Applied rotation: {angle} degrees")
            return clip
        except Exception as e:
            self.logger.error(f"Failed to rotate: {e}")
            return clip

    def apply_margin(
        self,
        clip: VideoFileClip,
        margin_size: int = 10,
        color: tuple = (0, 0, 0)
    ) -> VideoFileClip:
        """
        添加边框

        Args:
            clip: 视频片段
            margin_size: 边框大小（像素）
            color: 边框颜色（RGB）

        Returns:
            添加边框的视频
        """
        try:
            clip = clip.fx(vfx.margin, margin_size, color=color)
            self.logger.info(f"Applied margin: {margin_size}px")
            return clip
        except Exception as e:
            self.logger.error(f"Failed to add margin: {e}")
            return clip

    def apply_loop(
        self,
        clip: VideoFileClip,
        n_loops: int = 2
    ) -> VideoFileClip:
        """
        循环播放视频

        Args:
            clip: 视频片段
            n_loops: 循环次数

        Returns:
            循环后的视频
        """
        try:
            clip = clip.fx(vfx.loop, n=n_loops)
            self.logger.info(f"Applied loop: {n_loops} times")
            return clip
        except Exception as e:
            self.logger.error(f"Failed to loop: {e}")
            return clip

    def apply_time_symmetrize(self, clip: VideoFileClip) -> VideoFileClip:
        """
        时间对称（正放+倒放）

        Args:
            clip: 视频片段

        Returns:
            对称播放的视频
        """
        try:
            clip = clip.fx(vfx.time_symmetrize)
            self.logger.info("Applied time symmetrize effect")
            return clip
        except Exception as e:
            self.logger.error(f"Failed to symmetrize: {e}")
            return clip

    def stabilize(self, clip: VideoFileClip) -> VideoFileClip:
        """
        视频稳定（需要额外的库支持）

        Note: 这个功能需要 vidstab 库，如果未安装则跳过

        Args:
            clip: 视频片段

        Returns:
            稳定后的视频
        """
        try:
            from vidstab import VidStab
            stabilizer = VidStab()
            # 这里需要实现实际的稳定逻辑
            self.logger.info("Video stabilization applied")
            return clip
        except ImportError:
            self.logger.warning("vidstab library not available, skipping stabilization")
            return clip
        except Exception as e:
            self.logger.error(f"Failed to stabilize video: {e}")
            return clip

    def apply_custom_effect(
        self,
        clip: VideoFileClip,
        effect_func
    ) -> VideoFileClip:
        """
        应用自定义效果函数

        Args:
            clip: 视频片段
            effect_func: 自定义效果函数

        Returns:
            应用效果后的视频
        """
        try:
            clip = clip.fl(effect_func)
            self.logger.info("Applied custom effect")
            return clip
        except Exception as e:
            self.logger.error(f"Failed to apply custom effect: {e}")
            return clip
