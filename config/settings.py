"""Configuration management module"""
from pydantic_settings import BaseSettings
from typing import Optional, List, Literal


class Settings(BaseSettings):
    """应用配置"""

    # 图片生成服务选择 (默认使用豆包)
    image_service_type: Literal["doubao", "nano_banana"] = "doubao"

    # Doubao (豆包) 配置
    doubao_api_key: str = ""
    doubao_base_url: str = "https://ark.cn-beijing.volces.com"
    doubao_endpoint: str = "/api/v3/images/generations"
    doubao_model: str = "doubao-seedream-4-5-251128"
    doubao_watermark: bool = False  # 是否在生成的图片中添加水印（false: 不添加水印）

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

    # 视频生成重试配置
    video_generation_max_retries: int = 3  # 视频生成失败时最大重试次数
    video_generation_retry_delay: float = 5.0  # 重试间隔（秒）
    video_generation_retry_backoff: float = 2.0  # 重试延迟倍增因子

    # Midjourney配置
    midjourney_api_key: str = ""
    midjourney_base_url: str = "https://api.kuai.host"
    midjourney_bot_type: str = "MID_JOURNEY"  # MID_JOURNEY 或 NIJI_JOURNEY
    midjourney_poll_interval: float = 3.0  # 轮询间隔（秒）
    midjourney_max_poll_attempts: int = 100  # 最大轮询次数
    midjourney_auto_upscale: bool = False  # 是否自动upscale获取单张图
    midjourney_upscale_index: int = 1  # 选择upscale哪一张1-4

    # 应用配置
    output_dir: str = "./output"
    temp_dir: str = "./temp"
    log_level: str = "INFO"
    max_concurrent_requests: int = 5

    # 图片生成并发配置
    image_max_concurrent: int = 3  # 图片生成最大并发数 (1-10)

    # 视频生成并发配置
    video_max_concurrent: int = 2  # 视频生成最大并发数 (1-5)

    # 角色一致性配置
    enable_character_references: bool = True  # 是否启用角色参考图生成
    character_reference_mode: Literal["single_multi_view", "multiple_single_view"] = "single_multi_view"  # 单张多视角 or 多张单视角
    reference_views: List[str] = [  # 要生成的参考视图列表
        "front_view",
        "side_view",
        "close_up",
        "full_body"
    ]
    max_reference_images: int = 4  # 最大参考图数量
    reference_image_size: int = 1024  # 参考图尺寸（像素）
    reference_cfg_scale: float = 8.0  # 参考图生成的CFG引导强度
    reference_steps: int = 60  # 参考图生成的推理步数
    character_art_style: Literal["realistic", "anime", "semi_realistic"] = "realistic"  # 角色风格：realistic(写实), anime(动漫), semi_realistic(半写实)

    # 场景图片一致性配置
    enable_image_to_image: bool = True  # 是否启用图生图（基于角色参考图）
    scene_cfg_scale: float = 7.5  # 场景图生成的CFG引导强度
    scene_steps: int = 50  # 场景图生成的推理步数
    reference_image_weight: float = 0.7  # 参考图权重 (0.0-1.0)，控制对参考图的遵循程度

    # 智能时长计算配置
    enable_smart_duration: bool = True  # 是否启用智能时长计算
    duration_chinese_chars_per_sec: float = 3.5  # 中文朗读速度（字/秒）
    duration_english_words_per_sec: float = 2.5  # 英文朗读速度（词/秒）
    duration_base_time: float = 2.0  # 基础场景建立时长（秒）
    duration_min_guaranteed: float = 3.0  # 最小保障时长（秒）
    duration_action_base: float = 1.5  # 动作基础时长（秒）
    duration_emotion_padding: float = 0.3  # 情绪停顿填充（秒）
    duration_buffer_multiplier: float = 1.1  # 缓冲系数（1.1 = 10%余量）

    # LLM配置（用于提示词优化）
    fast_llm_api_key: str = ""
    fast_llm_api_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    fast_llm_model: str = "qwen3-next-80b-a3b-instruct"
    enable_prompt_optimization: bool = True  # 是否启用提示词优化

    # Judge LLM配置（用于图片质量评分）
    judge_llm_api_key: str = ""
    judge_llm_api_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    judge_llm_model: str = "doubao-seed-1-6-251015"
    enable_character_consistency_judge: bool = True  # 是否启用角色一致性评分
    candidate_images_per_scene: int = 3  # 每个场景生成的候选图片数量（1-5）
    judge_temperature: float = 0.3  # Judge LLM的温度参数（越低越稳定）

    # 可选配置
    openai_api_key: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
settings = Settings()
