"""Configuration management module"""
from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    """应用配置"""

    # Nano Banana Pro配置
    nano_banana_api_key: str = ""
    nano_banana_base_url: str = "https://api.nanobananapro.com/v1"
    nano_banana_endpoint: str = "/generate"  # API 端点路径
    nano_banana_model: str = "dall-e-3"  # 图像生成模型名称

    # Veo3配置
    veo3_api_key: str = ""
    veo3_base_url: str = "https://api.kuai.host"
    veo3_endpoint: str = "/v1/videos"  # OpenAI 格式的视频生成端点
    veo3_model: str = "veo_3_1"  # 视频生成模型：veo_3_1 或 veo_3_1-fast
    veo3_upload_endpoint: Optional[str] = None  # OpenAI 格式不需要单独上传
    veo3_skip_upload: bool = True  # OpenAI 格式使用 multipart，无需单独上传

    # 应用配置
    output_dir: str = "./output"
    temp_dir: str = "./temp"
    log_level: str = "INFO"
    max_concurrent_requests: int = 5

    # 角色一致性配置
    enable_character_references: bool = True  # 是否启用角色参考图生成
    reference_views: List[str] = [  # 要生成的参考视图列表
        "front_view",
        "side_view",
        "close_up",
        "full_body"
    ]
    reference_image_size: int = 1024  # 参考图尺寸（像素）
    reference_cfg_scale: float = 8.0  # 参考图生成的CFG引导强度
    reference_steps: int = 60  # 参考图生成的推理步数

    # 场景图片一致性配置
    scene_cfg_scale: float = 7.5  # 场景图生成的CFG引导强度
    scene_steps: int = 50  # 场景图生成的推理步数

    # 可选配置
    openai_api_key: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
settings = Settings()
