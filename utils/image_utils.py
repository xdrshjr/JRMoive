"""Image utility functions for reference image handling"""
import base64
from pathlib import Path
from typing import List, Optional, Union
import logging

logger = logging.getLogger(__name__)


def image_to_base64(image_path: Union[str, Path]) -> str:
    """
    将图片文件转换为base64编码字符串

    Args:
        image_path: 图片文件路径

    Returns:
        base64编码的字符串

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 文件读取失败
    """
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    try:
        with open(path, 'rb') as f:
            image_data = f.read()

        base64_str = base64.b64encode(image_data).decode('utf-8')
        logger.debug(f"Converted image to base64: {path} ({len(base64_str)} chars)")

        return base64_str

    except Exception as e:
        logger.error(f"Failed to convert image to base64: {e}")
        raise ValueError(f"Failed to read image file: {e}") from e


def images_to_base64_array(image_paths: List[Union[str, Path]]) -> List[str]:
    """
    将多个图片文件转换为base64编码字符串数组

    Args:
        image_paths: 图片文件路径列表

    Returns:
        base64编码字符串列表
    """
    base64_array = []

    for path in image_paths:
        try:
            base64_str = image_to_base64(path)
            base64_array.append(base64_str)
        except Exception as e:
            logger.warning(f"Skipping image {path}: {e}")
            continue

    logger.info(f"Converted {len(base64_array)}/{len(image_paths)} images to base64")
    return base64_array


def get_reference_images_for_characters(
    character_names: List[str],
    reference_data: dict,
    view_types: Optional[List[str]] = None
) -> List[str]:
    """
    从reference_data中获取角色character sheet图片路径

    注意：在多视角模式下，每个角色只有一张'character_sheet'图片
    包含所有视图（正面、侧面、特写）。

    Args:
        character_names: 角色名称列表
        reference_data: 角色参考数据字典
                       期望结构: {char_name: {'character_sheet': path, 'seed': int}}
        view_types: 已废弃 - 在多视角模式下被忽略，保留仅为向后兼容

    Returns:
        角色character sheet图片路径列表（每个角色一张图片）

    Example:
        >>> reference_data = {
        ...     "Alice": {"character_sheet": "path/to/alice_sheet.png", "seed": 12345},
        ...     "Bob": {"character_sheet": "path/to/bob_sheet.png", "seed": 67890}
        ... }
        >>> get_reference_images_for_characters(["Alice", "Bob"], reference_data)
        ["path/to/alice_sheet.png", "path/to/bob_sheet.png"]
    """
    # 废弃警告
    if view_types is not None:
        logger.warning(
            "参数'view_types'在多视角character sheet模式下已废弃。"
            "每个角色现在只有一张综合character sheet。"
            "此参数将被忽略。"
        )

    image_paths = []

    for char_name in character_names:
        # 检查角色是否存在于参考数据中
        if char_name not in reference_data:
            logger.warning(f"未找到角色的参考数据: {char_name}")
            continue

        char_ref = reference_data[char_name]

        # 检查生成错误
        if 'error' in char_ref:
            logger.warning(
                f"角色'{char_name}'的参考数据包含错误: {char_ref['error']}"
            )
            continue

        # 获取character sheet路径
        if 'character_sheet' in char_ref and char_ref['character_sheet']:
            sheet_path = char_ref['character_sheet']
            image_paths.append(sheet_path)
            logger.debug(f"添加角色'{char_name}'的character sheet: {sheet_path}")
        else:
            logger.warning(
                f"角色'{char_name}'未找到'character_sheet'键。"
                f"可用的键: {list(char_ref.keys())}"
            )

    logger.info(
        f"为{len(character_names)}个请求角色收集了{len(image_paths)}张character sheet"
    )

    return image_paths


def prepare_reference_base64_array(
    character_names: List[str],
    reference_data: dict,
    view_types: Optional[List[str]] = None,
    max_images: int = 4
) -> Optional[List[str]]:
    """
    为角色准备参考图片的base64数组（一站式函数）

    Args:
        character_names: 角色名称列表
        reference_data: 角色参考数据字典
        view_types: 已废弃 - 在多视角模式下被忽略
        max_images: 最大图片数量（限制character sheet数量，即角色数）

    Returns:
        base64编码字符串列表，如果没有有效图片则返回None
    """
    # 废弃警告
    if view_types is not None:
        logger.warning("'view_types'参数已废弃，将被忽略")

    if not character_names or not reference_data:
        return None

    # 获取参考图片路径
    image_paths = get_reference_images_for_characters(
        character_names,
        reference_data,
        view_types
    )

    if not image_paths:
        logger.warning("No valid reference images found")
        return None

    # 限制图片数量
    if len(image_paths) > max_images:
        logger.info(f"Limiting reference images from {len(image_paths)} to {max_images}")
        image_paths = image_paths[:max_images]

    # 转换为base64
    base64_array = images_to_base64_array(image_paths)

    if not base64_array:
        logger.warning("Failed to convert any images to base64")
        return None

    return base64_array
