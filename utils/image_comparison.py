"""Image comparison utility for character consistency judging"""
import base64
from pathlib import Path
from typing import List, Union
from PIL import Image
import io
import logging


class ImageComparator:
    """图片对比工具 - 用于拼接参考图和场景图供LLM评分"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def stitch_images_horizontal(
        self,
        reference_image_path: Union[str, Path],
        scene_image_path: Union[str, Path],
        max_width: int = 2048,
        padding: int = 20
    ) -> Image.Image:
        """
        水平拼接参考图和场景图

        Args:
            reference_image_path: 参考角色图片路径
            scene_image_path: 场景图片路径
            max_width: 最大宽度（像素）
            padding: 图片间距（像素）

        Returns:
            拼接后的PIL Image对象
        """
        try:
            # 加载图片
            ref_img = Image.open(reference_image_path).convert('RGB')
            scene_img = Image.open(scene_image_path).convert('RGB')

            # 计算缩放比例以适应最大宽度
            total_width = ref_img.width + scene_img.width + padding
            if total_width > max_width:
                scale = (max_width - padding) / (ref_img.width + scene_img.width)
                new_ref_width = int(ref_img.width * scale)
                new_ref_height = int(ref_img.height * scale)
                new_scene_width = int(scene_img.width * scale)
                new_scene_height = int(scene_img.height * scale)

                ref_img = ref_img.resize((new_ref_width, new_ref_height), Image.Resampling.LANCZOS)
                scene_img = scene_img.resize((new_scene_width, new_scene_height), Image.Resampling.LANCZOS)

            # 创建拼接画布
            max_height = max(ref_img.height, scene_img.height)
            canvas_width = ref_img.width + scene_img.width + padding
            canvas = Image.new('RGB', (canvas_width, max_height), color=(255, 255, 255))

            # 粘贴图片（垂直居中）
            ref_y = (max_height - ref_img.height) // 2
            scene_y = (max_height - scene_img.height) // 2

            canvas.paste(ref_img, (0, ref_y))
            canvas.paste(scene_img, (ref_img.width + padding, scene_y))

            self.logger.debug(f"Stitched images: {canvas.size}")
            return canvas

        except Exception as e:
            self.logger.error(f"Failed to stitch images: {e}")
            raise

    def stitch_images_vertical(
        self,
        reference_image_path: Union[str, Path],
        scene_image_path: Union[str, Path],
        max_height: int = 2048,
        padding: int = 20
    ) -> Image.Image:
        """
        垂直拼接参考图和场景图

        Args:
            reference_image_path: 参考角色图片路径
            scene_image_path: 场景图片路径
            max_height: 最大高度（像素）
            padding: 图片间距（像素）

        Returns:
            拼接后的PIL Image对象
        """
        try:
            # 加载图片
            ref_img = Image.open(reference_image_path).convert('RGB')
            scene_img = Image.open(scene_image_path).convert('RGB')

            # 计算缩放比例以适应最大高度
            total_height = ref_img.height + scene_img.height + padding
            if total_height > max_height:
                scale = (max_height - padding) / (ref_img.height + scene_img.height)
                new_ref_width = int(ref_img.width * scale)
                new_ref_height = int(ref_img.height * scale)
                new_scene_width = int(scene_img.width * scale)
                new_scene_height = int(scene_img.height * scale)

                ref_img = ref_img.resize((new_ref_width, new_ref_height), Image.Resampling.LANCZOS)
                scene_img = scene_img.resize((new_scene_width, new_scene_height), Image.Resampling.LANCZOS)

            # 创建拼接画布
            max_width = max(ref_img.width, scene_img.width)
            canvas_height = ref_img.height + scene_img.height + padding
            canvas = Image.new('RGB', (max_width, canvas_height), color=(255, 255, 255))

            # 粘贴图片（水平居中）
            ref_x = (max_width - ref_img.width) // 2
            scene_x = (max_width - scene_img.width) // 2

            canvas.paste(ref_img, (ref_x, 0))
            canvas.paste(scene_img, (scene_x, ref_img.height + padding))

            self.logger.debug(f"Stitched images vertically: {canvas.size}")
            return canvas

        except Exception as e:
            self.logger.error(f"Failed to stitch images vertically: {e}")
            raise

    def image_to_base64(self, image: Image.Image, format: str = "PNG") -> str:
        """
        将PIL Image转换为base64字符串

        Args:
            image: PIL Image对象
            format: 图片格式（PNG, JPEG等）

        Returns:
            base64编码的图片字符串
        """
        try:
            buffer = io.BytesIO()
            image.save(buffer, format=format)
            buffer.seek(0)
            img_bytes = buffer.read()
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')
            return img_base64

        except Exception as e:
            self.logger.error(f"Failed to convert image to base64: {e}")
            raise

    def file_to_base64(self, file_path: Union[str, Path]) -> str:
        """
        将图片文件直接转换为base64字符串

        Args:
            file_path: 图片文件路径

        Returns:
            base64编码的图片字符串
        """
        try:
            with open(file_path, 'rb') as f:
                img_bytes = f.read()
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')
            return img_base64

        except Exception as e:
            self.logger.error(f"Failed to convert file to base64: {e}")
            raise

    def create_comparison_image(
        self,
        reference_image_path: Union[str, Path],
        scene_image_path: Union[str, Path],
        layout: str = "horizontal",
        save_path: Union[str, Path] = None
    ) -> Image.Image:
        """
        创建对比图片（可选保存）

        Args:
            reference_image_path: 参考角色图片路径
            scene_image_path: 场景图片路径
            layout: 布局方式（horizontal或vertical）
            save_path: 保存路径（可选）

        Returns:
            拼接后的PIL Image对象
        """
        if layout == "horizontal":
            stitched = self.stitch_images_horizontal(reference_image_path, scene_image_path)
        elif layout == "vertical":
            stitched = self.stitch_images_vertical(reference_image_path, scene_image_path)
        else:
            raise ValueError(f"Invalid layout: {layout}. Must be 'horizontal' or 'vertical'")

        if save_path:
            stitched.save(save_path)
            self.logger.info(f"Comparison image saved to: {save_path}")

        return stitched

    def prepare_for_llm_judge(
        self,
        reference_image_path: Union[str, Path],
        scene_image_path: Union[str, Path],
        layout: str = "horizontal"
    ) -> str:
        """
        准备用于LLM评分的图片（拼接并转换为base64）

        Args:
            reference_image_path: 参考角色图片路径
            scene_image_path: 场景图片路径
            layout: 布局方式（horizontal或vertical）

        Returns:
            base64编码的拼接图片字符串
        """
        stitched = self.create_comparison_image(
            reference_image_path,
            scene_image_path,
            layout=layout
        )
        return self.image_to_base64(stitched)
