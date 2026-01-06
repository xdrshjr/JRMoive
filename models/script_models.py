"""剧本数据模型定义"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from enum import Enum
from datetime import timedelta


class ShotType(Enum):
    """镜头类型"""
    CLOSE_UP = "close_up"              # 特写
    MEDIUM_SHOT = "medium_shot"        # 中景
    LONG_SHOT = "long_shot"            # 远景
    EXTREME_CLOSE_UP = "extreme_close_up"  # 大特写
    FULL_SHOT = "full_shot"            # 全景
    OVER_SHOULDER = "over_shoulder"    # 过肩镜头


class CameraMovement(Enum):
    """摄像机运动"""
    STATIC = "static"                  # 静止
    PAN = "pan"                        # 摇镜
    TILT = "tilt"                      # 俯仰
    ZOOM = "zoom"                      # 推拉
    DOLLY = "dolly"                    # 移动
    TRACKING = "tracking"              # 跟踪


class Character(BaseModel):
    """角色模型"""
    name: str = Field(..., description="角色名称")
    description: str = Field(..., description="角色描述（外貌、性格等）")
    age: Optional[int] = Field(None, description="年龄")
    gender: Optional[str] = Field(None, description="性别")
    appearance: Optional[str] = Field(None, description="外貌特征")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "小明",
                "description": "25岁的年轻程序员，戴眼镜，清秀",
                "age": 25,
                "gender": "male",
                "appearance": "黑框眼镜，短发，白色T恤"
            }
        }
    }


class Dialogue(BaseModel):
    """对话模型"""
    character: str = Field(..., description="说话的角色")
    content: str = Field(..., description="对话内容")
    emotion: Optional[str] = Field(None, description="情绪（高兴、悲伤、愤怒等）")
    voice_style: Optional[str] = Field(None, description="语音风格（用于TTS）")

    model_config = {
        "json_schema_extra": {
            "example": {
                "character": "小明",
                "content": "今天的代码终于跑通了！",
                "emotion": "excited",
                "voice_style": "energetic"
            }
        }
    }


class Scene(BaseModel):
    """场景模型"""
    scene_id: str = Field(..., description="场景唯一标识符")
    location: str = Field(..., description="地点（如：咖啡馆、办公室）")
    time: str = Field(..., description="时间（如：清晨、黄昏）")
    weather: Optional[str] = Field(None, description="天气（晴天、雨天等）")
    atmosphere: Optional[str] = Field(None, description="氛围（温馨、紧张等）")
    description: str = Field(..., description="场景详细描述")

    # 分镜参数
    shot_type: ShotType = Field(default=ShotType.MEDIUM_SHOT, description="镜头类型")
    camera_movement: CameraMovement = Field(default=CameraMovement.STATIC, description="摄像机运动")
    duration: float = Field(default=3.0, ge=1.0, le=10.0, description="时长（秒）")

    # 内容
    characters: List[str] = Field(default_factory=list, description="出现的角色")
    dialogues: List[Dialogue] = Field(default_factory=list, description="对话列表")
    action: Optional[str] = Field(None, description="动作描述")

    # 视觉风格
    visual_style: Optional[str] = Field(None, description="视觉风格（cinematic, anime等）")
    color_tone: Optional[str] = Field(None, description="色调（warm, cool, vibrant等）")

    @field_validator('duration')
    @classmethod
    def validate_duration(cls, v):
        """验证时长合法性"""
        if v < 1.0 or v > 10.0:
            raise ValueError("Scene duration must be between 1 and 10 seconds")
        return v

    def to_image_prompt(self) -> str:
        """
        将场景转换为图片生成提示词

        Returns:
            适合AI图片生成的提示词
        """
        prompt_parts = []

        # 基础场景描述
        prompt_parts.append(f"{self.location}, {self.time}")

        # 天气和氛围
        if self.weather:
            prompt_parts.append(f"{self.weather} weather")
        if self.atmosphere:
            prompt_parts.append(f"{self.atmosphere} atmosphere")

        # 角色和动作
        if self.characters:
            char_desc = ", ".join(self.characters)
            prompt_parts.append(f"characters: {char_desc}")
        if self.action:
            prompt_parts.append(self.action)

        # 详细描述
        prompt_parts.append(self.description)

        # 镜头类型
        prompt_parts.append(f"{self.shot_type.value} shot")

        # 视觉风格
        if self.visual_style:
            prompt_parts.append(f"{self.visual_style} style")
        if self.color_tone:
            prompt_parts.append(f"{self.color_tone} color tone")

        return ", ".join(prompt_parts)

    model_config = {
        "json_schema_extra": {
            "example": {
                "scene_id": "scene_001",
                "location": "cozy coffee shop",
                "time": "morning",
                "weather": "sunny",
                "atmosphere": "warm and peaceful",
                "description": "Sunlight streams through large windows",
                "shot_type": "medium_shot",
                "camera_movement": "static",
                "duration": 3.5,
                "characters": ["Xiao Ming"],
                "action": "sitting by the window, holding a coffee cup"
            }
        }
    }


class Script(BaseModel):
    """完整剧本模型"""
    title: str = Field(..., description="剧本标题")
    author: Optional[str] = Field(None, description="作者")
    description: Optional[str] = Field(None, description="剧本简介")
    characters: List[Character] = Field(default_factory=list, description="角色列表")
    scenes: List[Scene] = Field(..., description="场景列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

    @property
    def total_duration(self) -> float:
        """计算总时长（秒）"""
        return sum(scene.duration for scene in self.scenes)

    @property
    def total_scenes(self) -> int:
        """场景总数"""
        return len(self.scenes)

    def validate_script(self) -> List[str]:
        """
        验证剧本完整性

        Returns:
            错误信息列表（空列表表示无错误）
        """
        errors = []

        if not self.scenes:
            errors.append("Script must have at least one scene")

        if self.total_duration > 600:  # 限制最长10分钟
            errors.append(f"Total duration {self.total_duration}s exceeds 600s limit")

        # 验证角色一致性
        declared_chars = {char.name for char in self.characters}
        used_chars = set()
        for scene in self.scenes:
            used_chars.update(scene.characters)
            for dialogue in scene.dialogues:
                used_chars.add(dialogue.character)

        undeclared = used_chars - declared_chars
        if undeclared:
            errors.append(f"Undeclared characters: {undeclared}")

        return errors

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "程序员的一天",
                "author": "AI编剧",
                "description": "讲述一个程序员日常工作的温馨故事",
                "characters": [
                    {
                        "name": "小明",
                        "description": "年轻的Python开发者",
                        "age": 25,
                        "gender": "male"
                    }
                ],
                "scenes": []
            }
        }
    }
