"""剧本数据模型定义"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum
from datetime import timedelta
import yaml
import logging

logger = logging.getLogger(__name__)


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

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """验证角色名称"""
        if not v or not v.strip():
            raise ValueError("Character name cannot be empty")
        if len(v) > 50:
            raise ValueError("Character name must be less than 50 characters")
        return v.strip()
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        """验证角色描述"""
        if not v or not v.strip():
            raise ValueError("Character description cannot be empty")
        return v.strip()

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

    @field_validator('character')
    @classmethod
    def validate_character(cls, v):
        """验证角色名称"""
        if not v or not v.strip():
            raise ValueError("Dialogue character name cannot be empty")
        return v.strip()
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        """验证对话内容"""
        if not v or not v.strip():
            raise ValueError("Dialogue content cannot be empty")
        return v.strip()

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


class Narration(BaseModel):
    """旁白模型"""
    content: str = Field(..., description="旁白内容")
    voice_style: Optional[str] = Field(None, description="旁白语音风格（用于未来TTS扩展）")

    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        """验证旁白内容"""
        if not v or not v.strip():
            raise ValueError("Narration content cannot be empty")
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "example": {
                "content": "时间来到了深夜，办公室里只剩下小明一个人。",
                "voice_style": "calm"
            }
        }
    }


class SoundEffect(BaseModel):
    """音效模型"""
    description: str = Field(..., description="音效描述")
    timing: Optional[float] = Field(None, description="在场景中的时间点（秒）")

    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        """验证音效描述"""
        if not v or not v.strip():
            raise ValueError("Sound effect description cannot be empty")
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "example": {
                "description": "键盘敲击声",
                "timing": 1.5
            }
        }
    }


class SubScene(BaseModel):
    """子场景模型"""
    sub_scene_id: str = Field(..., description="子场景唯一标识符")
    description: str = Field(..., description="子场景详细描述")
    action: Optional[str] = Field(None, description="动作描述")
    
    # 分镜参数
    shot_type: Optional[ShotType] = Field(None, description="镜头类型（可继承父场景）")
    camera_movement: Optional[CameraMovement] = Field(None, description="摄像机运动（可继承父场景）")
    duration: Optional[float] = Field(default=3.0, description="时长（秒）")
    
    # 内容
    dialogues: List[Dialogue] = Field(default_factory=list, description="对话列表")
    narrations: List[Narration] = Field(default_factory=list, description="旁白列表")
    sound_effects: List[SoundEffect] = Field(default_factory=list, description="音效列表")
    
    # 视觉风格（可继承或覆盖父场景）
    visual_style: Optional[str] = Field(None, description="视觉风格（cinematic, anime等）")
    color_tone: Optional[str] = Field(None, description="色调（warm, cool, vibrant等）")
    
    # 自定义基础图片
    base_image_filename: Optional[str] = Field(None, description="自定义场景基础图文件名（从项目scenes文件夹加载）")
    
    @field_validator('duration')
    @classmethod
    def validate_duration(cls, v):
        """验证时长合法性"""
        if v is not None and (v < 1.0 or v > 10.0):
            raise ValueError("SubScene duration must be between 1 and 10 seconds")
        return v
    
    def to_video_prompt(
        self, 
        parent_scene: 'Scene',
        character_dict: Optional[Dict[str, 'Character']] = None
    ) -> str:
        """
        将子场景转换为视频生成提示词（继承父场景的基础信息）
        
        Args:
            parent_scene: 父场景对象
            character_dict: 可选的角色字典
            
        Returns:
            适合Veo3视频生成的提示词
        """
        prompt_parts = []
        
        # 1. 继承父场景的基础描述
        prompt_parts.append(f"{parent_scene.location}, {parent_scene.time}")
        
        # 2. 继承天气和氛围
        if parent_scene.weather:
            prompt_parts.append(f"{parent_scene.weather} weather")
        if parent_scene.atmosphere:
            prompt_parts.append(f"{parent_scene.atmosphere} atmosphere")
        
        # 3. 继承角色信息
        if parent_scene.characters and character_dict:
            char_descriptions = []
            for char_name in parent_scene.characters:
                if char_name in character_dict:
                    char = character_dict[char_name]
                    desc_parts = [char_name]
                    
                    if char.appearance:
                        desc_parts.append(f"({char.appearance})")
                    elif char.description:
                        desc_parts.append(f"({char.description})")
                    
                    char_descriptions.append(" ".join(desc_parts))
            
            if char_descriptions:
                prompt_parts.append(", ".join(char_descriptions))
        elif parent_scene.characters:
            prompt_parts.append(", ".join(parent_scene.characters))
        
        # 4. 动作描述
        if self.action:
            prompt_parts.append(self.action)
        
        # 5. 子场景对话
        if self.dialogues:
            dialogue_descriptions = []
            for dialogue in self.dialogues:
                emotion_desc = f" with {dialogue.emotion} expression" if dialogue.emotion else ""
                voice_style_desc = f" in {dialogue.voice_style} voice" if dialogue.voice_style else ""
                
                dialogue_desc = f"{dialogue.character} speaking{emotion_desc}{voice_style_desc}: \"{dialogue.content}\""
                dialogue_descriptions.append(dialogue_desc)
            
            prompt_parts.append("; ".join(dialogue_descriptions))
        
        # 6. 子场景详细描述
        prompt_parts.append(self.description)
        
        # 7. 镜头类型和运镜（使用子场景的或继承父场景的）
        shot_type = self.shot_type if self.shot_type else parent_scene.shot_type
        camera_movement = self.camera_movement if self.camera_movement else parent_scene.camera_movement
        
        prompt_parts.append(f"{shot_type.value} shot")
        prompt_parts.append(f"{camera_movement.value} camera movement")
        
        # 8. 视觉风格（优先使用子场景的，否则继承父场景的）
        visual_style = self.visual_style if self.visual_style else parent_scene.visual_style
        color_tone = self.color_tone if self.color_tone else parent_scene.color_tone
        
        if visual_style:
            prompt_parts.append(f"{visual_style} style")
        if color_tone:
            prompt_parts.append(f"{color_tone} color tone")
        
        return ", ".join(prompt_parts)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "sub_scene_id": "scene_001_sub_001",
                "description": "Close-up of steaming coffee cup",
                "shot_type": "close_up",
                "duration": 3.0
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
    duration: Optional[float] = Field(default=None, description="时长（秒，可选，由视频生成模型决定）")

    # 内容
    characters: List[str] = Field(default_factory=list, description="出现的角色")
    dialogues: List[Dialogue] = Field(default_factory=list, description="对话列表")
    narrations: List[Narration] = Field(default_factory=list, description="旁白列表")
    sound_effects: List[SoundEffect] = Field(default_factory=list, description="音效列表")
    action: Optional[str] = Field(None, description="动作描述")

    # 视觉风格
    visual_style: Optional[str] = Field(None, description="视觉风格（cinematic, anime等）")
    color_tone: Optional[str] = Field(None, description="色调（warm, cool, vibrant等）")
    
    # 子场景支持
    sub_scenes: List[SubScene] = Field(default_factory=list, description="子场景列表")
    extract_frame_index: Optional[int] = Field(default=5, description="从基础视频提取帧的位置（负数表示从末尾倒数）")
    
    # 自定义基础图片
    base_image_filename: Optional[str] = Field(None, description="自定义场景基础图文件名（从项目scenes文件夹加载）")

    @field_validator('duration')
    @classmethod
    def validate_duration(cls, v):
        """验证时长合法性（如果提供）"""
        if v is not None and (v < 1.0 or v > 10.0):
            raise ValueError("Scene duration must be between 1 and 10 seconds")
        return v
    
    @field_validator('scene_id')
    @classmethod
    def validate_scene_id(cls, v):
        """验证场景ID"""
        if not v or not v.strip():
            raise ValueError("Scene ID cannot be empty")
        return v.strip()
    
    @field_validator('location')
    @classmethod
    def validate_location(cls, v):
        """验证地点"""
        if not v or not v.strip():
            raise ValueError("Scene location cannot be empty")
        return v.strip()
    
    @field_validator('time')
    @classmethod
    def validate_time(cls, v):
        """验证时间"""
        if not v or not v.strip():
            raise ValueError("Scene time cannot be empty")
        return v.strip()
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        """验证描述"""
        if not v or not v.strip():
            raise ValueError("Scene description cannot be empty")
        return v.strip()

    def to_image_prompt(self, character_dict: Optional[Dict[str, 'Character']] = None) -> str:
        """
        将场景转换为图片生成提示词

        Args:
            character_dict: 可选的角色字典，用于添加详细外貌描述

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

        # 角色和动作 - 增强版本
        if self.characters:
            if character_dict:
                # 有角色字典：使用详细描述
                char_descriptions = []
                for char_name in self.characters:
                    if char_name in character_dict:
                        char = character_dict[char_name]
                        desc_parts = [char_name]

                        # 优先使用 appearance，其次 description
                        if char.appearance:
                            desc_parts.append(f"({char.appearance})")
                        elif char.description:
                            desc_parts.append(f"({char.description})")

                        # 添加年龄和性别
                        if char.age and char.gender:
                            desc_parts.append(f"{char.age} years old {char.gender}")

                        char_descriptions.append(" ".join(desc_parts))

                if char_descriptions:
                    prompt_parts.append("Characters: " + ", ".join(char_descriptions))
            else:
                # 无角色字典：仅使用名称（保持向后兼容）
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

    def to_video_prompt(self, character_dict: Optional[Dict[str, 'Character']] = None) -> str:
        """
        将场景转换为视频生成提示词（包含对话和情感）

        Args:
            character_dict: 可选的角色字典，用于添加详细角色信息

        Returns:
            适合Veo3视频生成的提示词
        """
        prompt_parts = []

        # 1. 基础场景描述
        prompt_parts.append(f"{self.location}, {self.time}")

        # 2. 天气和氛围
        if self.weather:
            prompt_parts.append(f"{self.weather} weather")
        if self.atmosphere:
            prompt_parts.append(f"{self.atmosphere} atmosphere")

        # 3. 角色信息
        if self.characters and character_dict:
            char_descriptions = []
            for char_name in self.characters:
                if char_name in character_dict:
                    char = character_dict[char_name]
                    desc_parts = [char_name]

                    # 优先使用 appearance，其次 description
                    if char.appearance:
                        desc_parts.append(f"({char.appearance})")
                    elif char.description:
                        desc_parts.append(f"({char.description})")

                    char_descriptions.append(" ".join(desc_parts))

            if char_descriptions:
                prompt_parts.append(", ".join(char_descriptions))
        elif self.characters:
            # 无角色字典：仅使用名称（向后兼容）
            prompt_parts.append(", ".join(self.characters))

        # 4. 动作描述
        if self.action:
            prompt_parts.append(self.action)

        # 5. 对话和情感（核心新增）
        if self.dialogues:
            dialogue_descriptions = []
            for dialogue in self.dialogues:
                emotion_desc = f" with {dialogue.emotion} expression" if dialogue.emotion else ""
                voice_style_desc = f" in {dialogue.voice_style} voice" if dialogue.voice_style else ""

                dialogue_desc = f"{dialogue.character} speaking{emotion_desc}{voice_style_desc}: \"{dialogue.content}\""
                dialogue_descriptions.append(dialogue_desc)

            prompt_parts.append("; ".join(dialogue_descriptions))

        # 6. 场景详细描述
        prompt_parts.append(self.description)

        # 7. 镜头类型和运镜
        prompt_parts.append(f"{self.shot_type.value} shot")
        prompt_parts.append(f"{self.camera_movement.value} camera movement")

        # 8. 视觉风格
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

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        """验证标题"""
        if not v or not v.strip():
            raise ValueError("Script title cannot be empty")
        return v.strip()
    
    @field_validator('scenes')
    @classmethod
    def validate_scenes(cls, v):
        """验证场景列表"""
        if not v:
            raise ValueError("Script must have at least one scene")
        return v

    @property
    def total_duration(self) -> Optional[float]:
        """计算总时长（秒）- 如果所有场景都有duration则返回总和，否则返回None"""
        durations = [scene.duration for scene in self.scenes if scene.duration is not None]
        if len(durations) == len(self.scenes):
            return sum(durations)
        return None

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

        # 只在所有场景都有duration时才检查总时长
        total_dur = self.total_duration
        if total_dur is not None and total_dur > 600:  # 限制最长10分钟
            errors.append(f"Total duration {total_dur}s exceeds 600s limit")

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
    
    def to_yaml(self) -> str:
        """
        将剧本导出为YAML格式
        
        Returns:
            YAML格式的剧本字符串
        """
        logger.debug("Converting Script to YAML format")
        
        # Convert to dictionary
        script_dict = {
            'title': self.title,
            'author': self.author,
            'description': self.description,
            'characters': [
                {
                    'name': char.name,
                    'description': char.description,
                    'age': char.age,
                    'gender': char.gender,
                    'appearance': char.appearance,
                }
                for char in self.characters
            ],
            'scenes': []
        }
        
        # Convert scenes
        for scene in self.scenes:
            scene_dict = {
                'scene_id': scene.scene_id,
                'location': scene.location,
                'time': scene.time,
                'weather': scene.weather,
                'atmosphere': scene.atmosphere,
                'description': scene.description,
                'shot_type': scene.shot_type.value,
                'camera_movement': scene.camera_movement.value,
                'duration': scene.duration,
                'visual_style': scene.visual_style,
                'color_tone': scene.color_tone,
                'action': scene.action,
                'extract_frame_index': scene.extract_frame_index,
                'base_image_filename': scene.base_image_filename,
                'characters': scene.characters,
                'dialogues': [
                    {
                        'character': d.character,
                        'content': d.content,
                        'emotion': d.emotion,
                        'voice_style': d.voice_style,
                    }
                    for d in scene.dialogues
                ],
                'narrations': [
                    {
                        'content': n.content,
                        'voice_style': n.voice_style,
                    }
                    for n in scene.narrations
                ],
                'sound_effects': [
                    {
                        'description': se.description,
                        'timing': se.timing,
                    }
                    for se in scene.sound_effects
                ],
                'sub_scenes': []
            }
            
            # Convert sub-scenes
            for sub_scene in scene.sub_scenes:
                sub_scene_dict = {
                    'sub_scene_id': sub_scene.sub_scene_id,
                    'description': sub_scene.description,
                    'action': sub_scene.action,
                    'shot_type': sub_scene.shot_type.value if sub_scene.shot_type else None,
                    'camera_movement': sub_scene.camera_movement.value if sub_scene.camera_movement else None,
                    'duration': sub_scene.duration,
                    'visual_style': sub_scene.visual_style,
                    'color_tone': sub_scene.color_tone,
                    'base_image_filename': sub_scene.base_image_filename,
                    'dialogues': [
                        {
                            'character': d.character,
                            'content': d.content,
                            'emotion': d.emotion,
                            'voice_style': d.voice_style,
                        }
                        for d in sub_scene.dialogues
                    ],
                    'narrations': [
                        {
                            'content': n.content,
                            'voice_style': n.voice_style,
                        }
                        for n in sub_scene.narrations
                    ],
                    'sound_effects': [
                        {
                            'description': se.description,
                            'timing': se.timing,
                        }
                        for se in sub_scene.sound_effects
                    ],
                }
                scene_dict['sub_scenes'].append(sub_scene_dict)
            
            script_dict['scenes'].append(scene_dict)
        
        # Add metadata if present
        if self.metadata:
            script_dict['metadata'] = self.metadata
        
        # Convert to YAML with proper formatting
        yaml_str = yaml.dump(
            script_dict,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            indent=2,
            width=120
        )
        
        logger.info(f"Script exported to YAML: {len(self.scenes)} scenes, {len(self.characters)} characters")
        return yaml_str

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
