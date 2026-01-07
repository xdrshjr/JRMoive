"""Reference sheet composer - 合成角色多视图参考图"""
from PIL import Image
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging


class ReferenceSheetComposer:
    """将多个角色视图合成为单张参考表"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def create_composite_sheet(
        self,
        views: Dict[str, str],
        output_path: Path,
        grid_size: Tuple[int, int] = (2, 2),
        cell_size: int = 1024,
        background_color: Tuple[int, int, int] = (255, 255, 255)
    ) -> Path:
        """
        合成参考表 - 将多个视图拼接成网格布局

        Args:
            views: 视图字典 {view_name: image_path, ...}
            output_path: 输出路径
            grid_size: 网格大小 (rows, cols)，默认2x2
            cell_size: 每个单元格的大小（像素）
            background_color: 背景颜色RGB

        Returns:
            合成后的图片路径
        """
        self.logger.info(f"Creating composite reference sheet: {output_path}")

        # 过滤掉非图片键（如'seed'）
        image_paths = [
            v for k, v in views.items()
            if k != 'seed' and k != 'error' and isinstance(v, str) and v is not None
        ]

        if not image_paths:
            raise ValueError("No valid image paths in views")

        # 加载图片
        images = []
        for path in image_paths:
            try:
                img = Image.open(path)
                images.append(img)
            except Exception as e:
                self.logger.warning(f"Failed to load image {path}: {e}")

        if not images:
            raise ValueError("No images could be loaded")

        # 确定网格尺寸
        rows, cols = grid_size
        max_images = rows * cols

        # 限制图片数量
        images = images[:max_images]

        # 创建画布
        canvas_width = cols * cell_size
        canvas_height = rows * cell_size
        composite = Image.new('RGB', (canvas_width, canvas_height), color=background_color)

        # 排列图片
        for idx, img in enumerate(images):
            row = idx // cols
            col = idx % cols

            # 计算位置
            x = col * cell_size
            y = row * cell_size

            # 调整图片大小
            img_resized = img.resize((cell_size, cell_size), Image.Resampling.LANCZOS)

            # 粘贴到画布
            composite.paste(img_resized, (x, y))

            self.logger.debug(f"Placed image {idx} at position ({x}, {y})")

        # 保存
        output_path.parent.mkdir(parents=True, exist_ok=True)
        composite.save(output_path, quality=95)

        self.logger.info(f"Composite sheet saved: {output_path}")

        return output_path

    def create_labeled_sheet(
        self,
        views: Dict[str, str],
        output_path: Path,
        labels: Optional[Dict[str, str]] = None,
        grid_size: Tuple[int, int] = (2, 2),
        cell_size: int = 1024
    ) -> Path:
        """
        创建带标签的参考表

        Args:
            views: 视图字典 {view_name: image_path}
            output_path: 输出路径
            labels: 标签字典 {view_name: label_text}（可选）
            grid_size: 网格大小
            cell_size: 单元格大小

        Returns:
            合成后的图片路径
        """
        from PIL import ImageDraw, ImageFont

        self.logger.info(f"Creating labeled reference sheet: {output_path}")

        # 先创建基础合成图
        composite_path = output_path.with_stem(output_path.stem + "_temp")
        self.create_composite_sheet(views, composite_path, grid_size, cell_size)

        # 加载合成图
        composite = Image.open(composite_path)
        draw = ImageDraw.Draw(composite)

        # 尝试加载字体
        try:
            # 使用系统字体（可根据系统调整）
            font = ImageFont.truetype("arial.ttf", 32)
        except:
            # 如果加载失败，使用默认字体
            font = ImageFont.load_default()
            self.logger.warning("Using default font (truetype font not available)")

        # 添加标签
        view_names = [k for k in views.keys() if k != 'seed' and k != 'error' and views[k] is not None]
        rows, cols = grid_size

        for idx, view_name in enumerate(view_names[:rows * cols]):
            row = idx // cols
            col = idx % cols

            # 获取标签文本
            label_text = labels.get(view_name, view_name) if labels else view_name

            # 计算标签位置（左上角）
            x = col * cell_size + 10
            y = row * cell_size + 10

            # 绘制背景框
            bbox = draw.textbbox((x, y), label_text, font=font)
            draw.rectangle(bbox, fill=(0, 0, 0, 128))

            # 绘制文字
            draw.text((x, y), label_text, fill=(255, 255, 255), font=font)

        # 保存最终图片
        composite.save(output_path, quality=95)

        # 删除临时文件
        composite_path.unlink(missing_ok=True)

        self.logger.info(f"Labeled reference sheet saved: {output_path}")

        return output_path

    def create_character_portfolio(
        self,
        character_name: str,
        views: Dict[str, str],
        output_dir: Path
    ) -> Dict[str, Path]:
        """
        为单个角色创建完整的参考作品集

        Args:
            character_name: 角色名称
            views: 视图字典
            output_dir: 输出目录

        Returns:
            生成的文件路径字典 {type: path}
        """
        self.logger.info(f"Creating portfolio for character: {character_name}")

        output_dir = output_dir / character_name.replace(" ", "_")
        output_dir.mkdir(parents=True, exist_ok=True)

        results = {}

        # 1. 创建基础网格合成图
        composite_path = output_dir / f"{character_name}_reference_sheet.png"
        try:
            self.create_composite_sheet(views, composite_path)
            results['composite'] = composite_path
        except Exception as e:
            self.logger.error(f"Failed to create composite sheet: {e}")

        # 2. 创建带标签的版本
        labeled_path = output_dir / f"{character_name}_labeled_sheet.png"
        try:
            self.create_labeled_sheet(views, labeled_path)
            results['labeled'] = labeled_path
        except Exception as e:
            self.logger.error(f"Failed to create labeled sheet: {e}")

        return results
