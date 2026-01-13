"""
Video type definitions for AI drama generation system.

This module defines video types, subtypes, and their configurations
to customize prompt generation and visual style throughout the workflow.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class VideoType(str, Enum):
    """Main video type categories."""
    NEWS_BROADCAST = "news_broadcast"
    ANIME = "anime"
    MOVIE = "movie"
    SHORT_DRAMA = "short_drama"


class NewsSubtype(str, Enum):
    """News broadcast subtypes."""
    SOLO_ANCHOR = "solo_anchor"
    INTERVIEW = "interview"
    PANEL_DISCUSSION = "panel_discussion"
    FIELD_REPORTING = "field_reporting"


class AnimeSubtype(str, Enum):
    """Anime subtypes."""
    GHIBLI_STYLE = "ghibli_style"
    AMERICAN_STYLE = "american_style"
    CHIBI_SD = "chibi_sd"
    REALISTIC_ANIME = "realistic_anime"


class MovieSubtype(str, Enum):
    """Movie/Film subtypes."""
    ACTION = "action"
    DRAMA = "drama"
    SCI_FI = "sci_fi"
    HORROR = "horror"
    ROMANCE = "romance"


class ShortDramaSubtype(str, Enum):
    """Short drama subtypes."""
    MODERN_DRAMA = "modern_drama"
    PERIOD_DRAMA = "period_drama"
    COMEDY_SKETCH = "comedy_sketch"
    ROMANTIC_SHORT = "romantic_short"


# Union type for all subtypes
VideoSubtype = NewsSubtype | AnimeSubtype | MovieSubtype | ShortDramaSubtype


class VideoTypeConfig(BaseModel):
    """
    Configuration for video type and subtype.

    This configuration is used throughout the workflow to customize:
    - Script generation prompts
    - Image generation prompts
    - Video generation prompts
    - Visual style and aesthetic
    """

    type: VideoType = Field(
        description="Main video type category"
    )

    subtype: str = Field(
        description="Specific subtype within the video type"
    )

    description: str = Field(
        default="",
        description="Human-readable description of the video type/subtype combination"
    )

    style_keywords: List[str] = Field(
        default_factory=list,
        description="Keywords that describe the visual style"
    )

    recommended_settings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Recommended settings for shot types, camera movements, etc."
    )

    @classmethod
    def get_default(cls) -> "VideoTypeConfig":
        """Get default video type configuration (Short Drama - Modern Drama)."""
        return cls(
            type=VideoType.SHORT_DRAMA,
            subtype=ShortDramaSubtype.MODERN_DRAMA.value,
            description="Modern urban short drama with contemporary settings",
            style_keywords=["realistic", "contemporary", "dramatic", "character-focused"],
            recommended_settings={
                "shot_types": ["medium_shot", "close_up"],
                "camera_movements": ["static", "pan"],
                "visual_style": "realistic"
            }
        )

    def get_llm_context(self) -> str:
        """
        Generate LLM context string for prompt inclusion.

        Returns:
            Formatted string with video type context for LLM prompts
        """
        context_parts = [
            f"Video Type: {self.type.value}",
            f"Subtype: {self.subtype}",
        ]

        if self.description:
            context_parts.append(f"Description: {self.description}")

        if self.style_keywords:
            context_parts.append(f"Style Keywords: {', '.join(self.style_keywords)}")

        return "\n".join(context_parts)

    def get_prompt_prefix(self) -> str:
        """
        Generate a concise prompt prefix for image/video generation.

        Returns:
            Short prefix string to prepend to prompts
        """
        prefix_parts = [f"[{self.type.value.replace('_', ' ').title()} - {self.subtype.replace('_', ' ').title()}]"]

        if self.style_keywords:
            prefix_parts.append(f"({', '.join(self.style_keywords[:3])})")

        return " ".join(prefix_parts)


# Video type definitions with metadata
VIDEO_TYPE_DEFINITIONS = {
    VideoType.NEWS_BROADCAST: {
        "name_zh": "新闻播报",
        "name_en": "News Broadcast",
        "description_zh": "专业新闻播报视频",
        "description_en": "Professional news broadcast video",
        "subtypes": {
            NewsSubtype.SOLO_ANCHOR: {
                "name_zh": "单人播报",
                "name_en": "Solo Anchor",
                "description_zh": "单人新闻主播专业播报",
                "description_en": "Professional news anchor presenting alone",
                "style_keywords": ["professional", "formal", "clean lighting", "studio setup", "news desk"],
                "recommended_settings": {
                    "shot_types": ["medium_shot", "close_up"],
                    "camera_movements": ["static", "pan"],
                    "visual_style": "realistic"
                }
            },
            NewsSubtype.INTERVIEW: {
                "name_zh": "采访",
                "name_en": "Interview",
                "description_zh": "主播采访嘉宾对话形式",
                "description_en": "Anchor interviewing guest(s)",
                "style_keywords": ["professional", "conversational", "interview setup", "multiple angles"],
                "recommended_settings": {
                    "shot_types": ["medium_shot", "over_shoulder", "close_up"],
                    "camera_movements": ["static", "pan"],
                    "visual_style": "realistic"
                }
            },
            NewsSubtype.PANEL_DISCUSSION: {
                "name_zh": "多人讨论",
                "name_en": "Panel Discussion",
                "description_zh": "多位主播或专家讨论话题",
                "description_en": "Multiple anchors/experts discussing topics",
                "style_keywords": ["professional", "round table", "debate format", "multiple participants"],
                "recommended_settings": {
                    "shot_types": ["long_shot", "medium_shot", "close_up"],
                    "camera_movements": ["static", "pan"],
                    "visual_style": "realistic"
                }
            },
            NewsSubtype.FIELD_REPORTING: {
                "name_zh": "现场报道",
                "name_en": "Field Reporting",
                "description_zh": "记者现场实地报道",
                "description_en": "Reporter on location with live coverage",
                "style_keywords": ["on-location", "outdoor", "handheld camera", "dynamic", "live coverage"],
                "recommended_settings": {
                    "shot_types": ["medium_shot", "long_shot", "full_shot"],
                    "camera_movements": ["pan", "tracking", "handheld"],
                    "visual_style": "realistic"
                }
            }
        }
    },
    VideoType.ANIME: {
        "name_zh": "动漫",
        "name_en": "Anime",
        "description_zh": "动画风格视频",
        "description_en": "Animated style video",
        "subtypes": {
            AnimeSubtype.GHIBLI_STYLE: {
                "name_zh": "吉卜力风格",
                "name_en": "Ghibli Style",
                "description_zh": "手绘美学、柔和色彩、自然主题、奇幻风格",
                "description_en": "Hand-drawn aesthetic, soft colors, nature themes, whimsical",
                "style_keywords": ["hand-drawn", "soft colors", "nature", "whimsical", "Studio Ghibli style"],
                "recommended_settings": {
                    "shot_types": ["full_shot", "long_shot", "close_up"],
                    "camera_movements": ["pan", "tracking", "static"],
                    "visual_style": "anime"
                }
            },
            AnimeSubtype.AMERICAN_STYLE: {
                "name_zh": "欧美风格",
                "name_en": "American Style",
                "description_zh": "粗线条、鲜艳色彩、动作导向、漫画风格",
                "description_en": "Bold lines, vibrant colors, action-oriented, comic book feel",
                "style_keywords": ["bold lines", "vibrant colors", "action-packed", "comic book style"],
                "recommended_settings": {
                    "shot_types": ["full_shot", "medium_shot", "extreme_close_up"],
                    "camera_movements": ["zoom", "pan", "dynamic"],
                    "visual_style": "anime"
                }
            },
            AnimeSubtype.CHIBI_SD: {
                "name_zh": "Q版/SD",
                "name_en": "Chibi/SD",
                "description_zh": "超级变形角色、可爱、夸张表情",
                "description_en": "Super-deformed characters, cute, exaggerated expressions",
                "style_keywords": ["chibi", "cute", "super-deformed", "exaggerated", "kawaii"],
                "recommended_settings": {
                    "shot_types": ["full_shot", "medium_shot", "close_up"],
                    "camera_movements": ["static", "zoom", "bounce"],
                    "visual_style": "anime"
                }
            },
            AnimeSubtype.REALISTIC_ANIME: {
                "name_zh": "写实动漫",
                "name_en": "Realistic Anime",
                "description_zh": "细节丰富、真实比例、电影级光影",
                "description_en": "Detailed characters, realistic proportions, cinematic lighting",
                "style_keywords": ["detailed", "realistic proportions", "cinematic lighting", "high quality anime"],
                "recommended_settings": {
                    "shot_types": ["medium_shot", "close_up", "full_shot"],
                    "camera_movements": ["dolly", "tracking", "pan"],
                    "visual_style": "semi_realistic"
                }
            }
        }
    },
    VideoType.MOVIE: {
        "name_zh": "电影",
        "name_en": "Movie/Film",
        "description_zh": "电影级视频制作",
        "description_en": "Cinematic film production",
        "subtypes": {
            MovieSubtype.ACTION: {
                "name_zh": "动作片",
                "name_en": "Action",
                "description_zh": "快节奏、动态镜头、激烈场景、特技",
                "description_en": "Fast-paced, dynamic camera, intense scenes, stunts",
                "style_keywords": ["action-packed", "dynamic", "intense", "fast-paced", "cinematic"],
                "recommended_settings": {
                    "shot_types": ["long_shot", "full_shot", "medium_shot"],
                    "camera_movements": ["tracking", "dolly", "zoom", "pan"],
                    "visual_style": "realistic"
                }
            },
            MovieSubtype.DRAMA: {
                "name_zh": "剧情片",
                "name_en": "Drama",
                "description_zh": "角色为中心、情感深度、对话丰富",
                "description_en": "Character-focused, emotional depth, dialogue-heavy",
                "style_keywords": ["dramatic", "emotional", "character-driven", "cinematic lighting"],
                "recommended_settings": {
                    "shot_types": ["close_up", "medium_shot", "over_shoulder"],
                    "camera_movements": ["static", "dolly", "pan"],
                    "visual_style": "realistic"
                }
            },
            MovieSubtype.SCI_FI: {
                "name_zh": "科幻片",
                "name_en": "Sci-Fi",
                "description_zh": "未来场景、特效、科技主题",
                "description_en": "Futuristic settings, special effects, technology themes",
                "style_keywords": ["futuristic", "sci-fi", "high-tech", "special effects", "cinematic"],
                "recommended_settings": {
                    "shot_types": ["long_shot", "full_shot", "medium_shot"],
                    "camera_movements": ["dolly", "tracking", "zoom"],
                    "visual_style": "realistic"
                }
            },
            MovieSubtype.HORROR: {
                "name_zh": "恐怖片",
                "name_en": "Horror",
                "description_zh": "黑暗氛围、悬疑、诡异光影",
                "description_en": "Dark atmosphere, suspenseful, eerie lighting",
                "style_keywords": ["dark", "suspenseful", "eerie", "atmospheric", "horror"],
                "recommended_settings": {
                    "shot_types": ["close_up", "extreme_close_up", "long_shot"],
                    "camera_movements": ["static", "slow pan", "tracking"],
                    "visual_style": "realistic"
                }
            },
            MovieSubtype.ROMANCE: {
                "name_zh": "爱情片",
                "name_en": "Romance",
                "description_zh": "亲密时刻、柔和光影、情感连接",
                "description_en": "Intimate moments, soft lighting, emotional connection",
                "style_keywords": ["romantic", "intimate", "soft lighting", "emotional", "cinematic"],
                "recommended_settings": {
                    "shot_types": ["close_up", "medium_shot", "over_shoulder"],
                    "camera_movements": ["static", "dolly", "pan"],
                    "visual_style": "realistic"
                }
            }
        }
    },
    VideoType.SHORT_DRAMA: {
        "name_zh": "短剧",
        "name_en": "Short Drama",
        "description_zh": "短视频剧集",
        "description_en": "Short-form drama series",
        "subtypes": {
            ShortDramaSubtype.MODERN_DRAMA: {
                "name_zh": "现代剧",
                "name_en": "Modern Drama",
                "description_zh": "当代背景、贴近生活、都市题材",
                "description_en": "Contemporary settings, relatable stories, urban life",
                "style_keywords": ["contemporary", "urban", "realistic", "relatable", "modern"],
                "recommended_settings": {
                    "shot_types": ["medium_shot", "close_up", "full_shot"],
                    "camera_movements": ["static", "pan", "dolly"],
                    "visual_style": "realistic"
                }
            },
            ShortDramaSubtype.PERIOD_DRAMA: {
                "name_zh": "古装剧",
                "name_en": "Period Drama",
                "description_zh": "历史背景、古装服饰、传统美学",
                "description_en": "Historical settings, period costumes, traditional aesthetics",
                "style_keywords": ["historical", "period costume", "traditional", "classical", "elegant"],
                "recommended_settings": {
                    "shot_types": ["full_shot", "medium_shot", "long_shot"],
                    "camera_movements": ["static", "pan", "dolly"],
                    "visual_style": "realistic"
                }
            },
            ShortDramaSubtype.COMEDY_SKETCH: {
                "name_zh": "喜剧小品",
                "name_en": "Comedy Sketch",
                "description_zh": "幽默情境、夸张表情、轻松基调",
                "description_en": "Humorous situations, exaggerated expressions, light tone",
                "style_keywords": ["humorous", "comedy", "exaggerated", "lighthearted", "funny"],
                "recommended_settings": {
                    "shot_types": ["medium_shot", "full_shot", "close_up"],
                    "camera_movements": ["static", "zoom", "pan"],
                    "visual_style": "realistic"
                }
            },
            ShortDramaSubtype.ROMANTIC_SHORT: {
                "name_zh": "浪漫短剧",
                "name_en": "Romantic Short",
                "description_zh": "爱情故事、亲密时刻、情感聚焦",
                "description_en": "Love stories, intimate moments, emotional focus",
                "style_keywords": ["romantic", "emotional", "intimate", "heartfelt", "love story"],
                "recommended_settings": {
                    "shot_types": ["close_up", "medium_shot", "over_shoulder"],
                    "camera_movements": ["static", "dolly", "pan"],
                    "visual_style": "realistic"
                }
            }
        }
    }
}


def get_video_type_config(video_type: VideoType, subtype: str) -> VideoTypeConfig:
    """
    Create a VideoTypeConfig from type and subtype.

    Args:
        video_type: Main video type
        subtype: Specific subtype string

    Returns:
        VideoTypeConfig with populated metadata

    Raises:
        ValueError: If type/subtype combination is invalid
    """
    if video_type not in VIDEO_TYPE_DEFINITIONS:
        raise ValueError(f"Invalid video type: {video_type}")

    type_def = VIDEO_TYPE_DEFINITIONS[video_type]

    # Find matching subtype
    subtype_def = None
    for subtype_enum, subtype_data in type_def["subtypes"].items():
        if subtype_enum.value == subtype:
            subtype_def = subtype_data
            break

    if not subtype_def:
        raise ValueError(f"Invalid subtype '{subtype}' for video type '{video_type}'")

    return VideoTypeConfig(
        type=video_type,
        subtype=subtype,
        description=subtype_def["description_en"],
        style_keywords=subtype_def["style_keywords"],
        recommended_settings=subtype_def["recommended_settings"]
    )


def validate_video_type_combination(video_type: str, subtype: str) -> bool:
    """
    Validate if a video type and subtype combination is valid.

    Args:
        video_type: Video type string
        subtype: Subtype string

    Returns:
        True if valid, False otherwise
    """
    try:
        vt = VideoType(video_type)
        if vt not in VIDEO_TYPE_DEFINITIONS:
            return False

        type_def = VIDEO_TYPE_DEFINITIONS[vt]
        for subtype_enum in type_def["subtypes"].keys():
            if subtype_enum.value == subtype:
                return True

        return False
    except (ValueError, KeyError):
        return False
