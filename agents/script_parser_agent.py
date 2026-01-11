"""剧本解析Agent - 将YAML剧本转换为结构化数据"""

import re
import yaml
from typing import List, Dict, Any, Optional
from models.script_models import (
    Script, Scene, SubScene, Character, Dialogue,
    ShotType, CameraMovement, Narration, SoundEffect
)
from agents.base_agent import BaseAgent, AgentState
from utils.duration_calculator import DurationCalculator
from config.settings import settings
import logging


class ScriptParserAgent(BaseAgent):
    """剧本解析Agent - 将YAML剧本转换为结构化数据"""

    def __init__(self, agent_id: str = "script_parser", config: Dict[str, Any] = None):
        super().__init__(agent_id, config or {})
        self.logger = logging.getLogger(__name__)

    async def execute(self, input_data: str) -> Script:
        """
        执行剧本解析

        Args:
            input_data: YAML格式的剧本文本

        Returns:
            结构化的Script对象

        Raises:
            ValueError: 剧本格式错误
        """
        if not await self.validate_input(input_data):
            raise ValueError("Invalid script format: must be valid YAML with required fields")

        try:
            self.state = AgentState.RUNNING
            self.logger.info("ScriptParserAgent | Starting script parsing | format=YAML")

            # Parse YAML script
            script = self._parse_yaml_script(input_data)

            # 应用智能时长计算（如果启用）
            if settings.enable_smart_duration:
                DurationCalculator.apply_to_script(script, override=False)
                scenes_with_duration = sum(1 for s in script.scenes if s.duration is not None)
                self.logger.info(
                    f"ScriptParserAgent | Applied smart duration calculation | "
                    f"scenes_with_duration={scenes_with_duration}/{len(script.scenes)}"
                )

            # 验证剧本
            errors = script.validate_script()
            if errors:
                self.logger.warning(f"ScriptParserAgent | Script validation warnings | warnings={errors}")

            self.logger.info(
                f"ScriptParserAgent | Script parsing completed | "
                f"title={script.title} | "
                f"scenes={len(script.scenes)} | "
                f"characters={len(script.characters)}"
            )

            await self.on_complete(script)
            return script

        except yaml.YAMLError as e:
            self.logger.error(f"ScriptParserAgent | YAML parsing error | error={e}")
            await self.on_error(e)
            raise ValueError(f"Invalid YAML format: {str(e)}")
        except Exception as e:
            self.logger.error(f"ScriptParserAgent | Script parsing failed | error={e}")
            await self.on_error(e)
            raise

    async def validate_input(self, input_data: str) -> bool:
        """验证输入数据"""
        if not input_data or not isinstance(input_data, str):
            self.logger.error("ScriptParserAgent | Validation failed | reason=empty_or_invalid_type")
            return False

        try:
            # Try to parse as YAML
            data = yaml.safe_load(input_data)
            
            if not isinstance(data, dict):
                self.logger.error("ScriptParserAgent | Validation failed | reason=yaml_not_dict")
                return False
            
            # Check for required top-level fields
            if 'title' not in data:
                self.logger.error("ScriptParserAgent | Validation failed | reason=missing_title")
                return False
            
            if 'scenes' not in data or not isinstance(data['scenes'], list):
                self.logger.error("ScriptParserAgent | Validation failed | reason=missing_or_invalid_scenes")
                return False
            
            if not data['scenes']:
                self.logger.error("ScriptParserAgent | Validation failed | reason=empty_scenes")
                return False
            
            self.logger.debug("ScriptParserAgent | Validation passed | scenes_count={len(data['scenes'])}")
            return True
            
        except yaml.YAMLError as e:
            self.logger.error(f"ScriptParserAgent | Validation failed | reason=yaml_error | error={e}")
            return False

    def _parse_yaml_script(self, text: str) -> Script:
        """
        解析YAML格式的剧本
        
        Args:
            text: YAML格式的剧本文本
            
        Returns:
            Script对象
        """
        self.logger.debug("ScriptParserAgent | Parsing YAML script")
        
        try:
            data = yaml.safe_load(text)
            
            # Parse metadata
            title = data.get('title', 'Untitled Script')
            author = data.get('author')
            description = data.get('description')
            metadata = data.get('metadata', {})
            
            self.logger.debug(
                f"ScriptParserAgent | Parsed metadata | "
                f"title={title} | author={author} | has_description={bool(description)}"
            )
            
            # Parse characters
            characters = []
            characters_data = data.get('characters', [])
            
            if not isinstance(characters_data, list):
                self.logger.error("ScriptParserAgent | Characters must be a list")
                raise ValueError("Characters must be a list")
            
            for idx, char_data in enumerate(characters_data):
                if not isinstance(char_data, dict):
                    self.logger.warning(f"ScriptParserAgent | Skipping invalid character at index {idx}")
                    continue
                
                try:
                    character = Character(
                        name=char_data.get('name', ''),
                        description=char_data.get('description', ''),
                        age=char_data.get('age'),
                        gender=char_data.get('gender'),
                        appearance=char_data.get('appearance')
                    )
                    characters.append(character)
                    self.logger.debug(f"ScriptParserAgent | Parsed character | name={character.name}")
                except Exception as e:
                    self.logger.error(f"ScriptParserAgent | Failed to parse character {idx} | error={e}")
                    raise ValueError(f"Invalid character at index {idx}: {str(e)}")
            
            self.logger.info(f"ScriptParserAgent | Parsed {len(characters)} characters")
            
            # Parse scenes
            scenes = []
            scenes_data = data.get('scenes', [])
            
            if not isinstance(scenes_data, list):
                self.logger.error("ScriptParserAgent | Scenes must be a list")
                raise ValueError("Scenes must be a list")
            
            for idx, scene_data in enumerate(scenes_data):
                if not isinstance(scene_data, dict):
                    self.logger.warning(f"ScriptParserAgent | Skipping invalid scene at index {idx}")
                    continue
                
                try:
                    scene = self._parse_scene_from_dict(scene_data, idx)
                    scenes.append(scene)
                    self.logger.debug(
                        f"ScriptParserAgent | Parsed scene | "
                        f"scene_id={scene.scene_id} | location={scene.location}"
                    )
                except Exception as e:
                    self.logger.error(f"ScriptParserAgent | Failed to parse scene {idx} | error={e}")
                    raise ValueError(f"Invalid scene at index {idx}: {str(e)}")
            
            self.logger.info(f"ScriptParserAgent | Parsed {len(scenes)} scenes")
            
            # Create Script object
            script = Script(
                title=title,
                author=author,
                description=description,
                characters=characters,
                scenes=scenes,
                metadata=metadata
            )
            
            return script
            
        except yaml.YAMLError as e:
            self.logger.error(f"ScriptParserAgent | YAML parsing error | error={e}")
            raise ValueError(f"Invalid YAML format: {str(e)}")
        except Exception as e:
            self.logger.error(f"ScriptParserAgent | Failed to parse YAML script | error={e}")
            raise

    def _parse_scene_from_dict(self, scene_data: Dict[str, Any], index: int) -> Scene:
        """
        从字典解析场景
        
        Args:
            scene_data: 场景数据字典
            index: 场景索引
            
        Returns:
            Scene对象
        """
        # Required fields
        scene_id = scene_data.get('scene_id', f"scene_{str(index + 1).zfill(3)}")
        location = scene_data.get('location', '')
        time = scene_data.get('time', '')
        description = scene_data.get('description', '')
        
        # Optional fields
        weather = scene_data.get('weather')
        atmosphere = scene_data.get('atmosphere')
        action = scene_data.get('action')
        visual_style = scene_data.get('visual_style')
        color_tone = scene_data.get('color_tone')
        duration = scene_data.get('duration')
        extract_frame_index = scene_data.get('extract_frame_index', -5)
        base_image_filename = scene_data.get('base_image_filename')
        
        # Parse shot type
        shot_type_str = scene_data.get('shot_type', 'medium_shot')
        shot_type = self._parse_shot_type_from_string(shot_type_str)
        
        # Parse camera movement
        camera_movement_str = scene_data.get('camera_movement', 'static')
        camera_movement = self._parse_camera_movement_from_string(camera_movement_str)
        
        # Parse characters
        characters = scene_data.get('characters', [])
        if not isinstance(characters, list):
            characters = []
        
        # Parse dialogues
        dialogues = []
        dialogues_data = scene_data.get('dialogues', [])
        if isinstance(dialogues_data, list):
            for dialogue_data in dialogues_data:
                if isinstance(dialogue_data, dict):
                    try:
                        dialogue = Dialogue(
                            character=dialogue_data.get('character', ''),
                            content=dialogue_data.get('content', ''),
                            emotion=dialogue_data.get('emotion'),
                            voice_style=dialogue_data.get('voice_style')
                        )
                        dialogues.append(dialogue)
                    except Exception as e:
                        self.logger.warning(
                            f"ScriptParserAgent | Failed to parse dialogue in scene {scene_id} | error={e}"
                        )
        
        # Parse narrations
        narrations = []
        narrations_data = scene_data.get('narrations', [])
        if isinstance(narrations_data, list):
            for narration_data in narrations_data:
                if isinstance(narration_data, dict):
                    try:
                        narration = Narration(
                            content=narration_data.get('content', ''),
                            voice_style=narration_data.get('voice_style')
                        )
                        narrations.append(narration)
                    except Exception as e:
                        self.logger.warning(
                            f"ScriptParserAgent | Failed to parse narration in scene {scene_id} | error={e}"
                        )
        
        # Parse sound effects
        sound_effects = []
        sound_effects_data = scene_data.get('sound_effects', [])
        if isinstance(sound_effects_data, list):
            for se_data in sound_effects_data:
                if isinstance(se_data, dict):
                    try:
                        sound_effect = SoundEffect(
                            description=se_data.get('description', ''),
                            timing=se_data.get('timing')
                        )
                        sound_effects.append(sound_effect)
                    except Exception as e:
                        self.logger.warning(
                            f"ScriptParserAgent | Failed to parse sound effect in scene {scene_id} | error={e}"
                        )
        
        # Parse sub-scenes
        sub_scenes = []
        sub_scenes_data = scene_data.get('sub_scenes', [])
        if isinstance(sub_scenes_data, list):
            for sub_idx, sub_scene_data in enumerate(sub_scenes_data):
                if isinstance(sub_scene_data, dict):
                    try:
                        sub_scene = self._parse_sub_scene_from_dict(sub_scene_data, scene_id, sub_idx)
                        sub_scenes.append(sub_scene)
                    except Exception as e:
                        self.logger.warning(
                            f"ScriptParserAgent | Failed to parse sub-scene {sub_idx} in scene {scene_id} | error={e}"
                        )
        
        # Create Scene object
        scene = Scene(
            scene_id=scene_id,
            location=location,
            time=time,
            weather=weather,
            atmosphere=atmosphere,
            description=description,
            shot_type=shot_type,
            camera_movement=camera_movement,
            duration=duration,
            visual_style=visual_style,
            color_tone=color_tone,
            action=action,
            extract_frame_index=extract_frame_index,
            base_image_filename=base_image_filename,
            characters=characters,
            dialogues=dialogues,
            narrations=narrations,
            sound_effects=sound_effects,
            sub_scenes=sub_scenes
        )
        
        return scene

    def _parse_sub_scene_from_dict(self, sub_scene_data: Dict[str, Any], parent_scene_id: str, index: int) -> SubScene:
        """
        从字典解析子场景
        
        Args:
            sub_scene_data: 子场景数据字典
            parent_scene_id: 父场景ID
            index: 子场景索引
            
        Returns:
            SubScene对象
        """
        # Required fields
        sub_scene_id = sub_scene_data.get('sub_scene_id', f"{parent_scene_id}_sub_{str(index + 1).zfill(3)}")
        description = sub_scene_data.get('description', '')
        
        # Optional fields
        action = sub_scene_data.get('action')
        duration = sub_scene_data.get('duration', 3.0)
        visual_style = sub_scene_data.get('visual_style')
        color_tone = sub_scene_data.get('color_tone')
        base_image_filename = sub_scene_data.get('base_image_filename')
        
        # Parse shot type (optional, can inherit from parent)
        shot_type = None
        shot_type_str = sub_scene_data.get('shot_type')
        if shot_type_str:
            shot_type = self._parse_shot_type_from_string(shot_type_str)
        
        # Parse camera movement (optional, can inherit from parent)
        camera_movement = None
        camera_movement_str = sub_scene_data.get('camera_movement')
        if camera_movement_str:
            camera_movement = self._parse_camera_movement_from_string(camera_movement_str)
        
        # Parse dialogues
        dialogues = []
        dialogues_data = sub_scene_data.get('dialogues', [])
        if isinstance(dialogues_data, list):
            for dialogue_data in dialogues_data:
                if isinstance(dialogue_data, dict):
                    try:
                        dialogue = Dialogue(
                            character=dialogue_data.get('character', ''),
                            content=dialogue_data.get('content', ''),
                            emotion=dialogue_data.get('emotion'),
                            voice_style=dialogue_data.get('voice_style')
                        )
                        dialogues.append(dialogue)
                    except Exception as e:
                        self.logger.warning(
                            f"ScriptParserAgent | Failed to parse dialogue in sub-scene {sub_scene_id} | error={e}"
                        )
        
        # Parse narrations
        narrations = []
        narrations_data = sub_scene_data.get('narrations', [])
        if isinstance(narrations_data, list):
            for narration_data in narrations_data:
                if isinstance(narration_data, dict):
                    try:
                        narration = Narration(
                            content=narration_data.get('content', ''),
                            voice_style=narration_data.get('voice_style')
                        )
                        narrations.append(narration)
                    except Exception as e:
                        self.logger.warning(
                            f"ScriptParserAgent | Failed to parse narration in sub-scene {sub_scene_id} | error={e}"
                        )
        
        # Parse sound effects
        sound_effects = []
        sound_effects_data = sub_scene_data.get('sound_effects', [])
        if isinstance(sound_effects_data, list):
            for se_data in sound_effects_data:
                if isinstance(se_data, dict):
                    try:
                        sound_effect = SoundEffect(
                            description=se_data.get('description', ''),
                            timing=se_data.get('timing')
                        )
                        sound_effects.append(sound_effect)
                    except Exception as e:
                        self.logger.warning(
                            f"ScriptParserAgent | Failed to parse sound effect in sub-scene {sub_scene_id} | error={e}"
                        )
        
        # Create SubScene object
        sub_scene = SubScene(
            sub_scene_id=sub_scene_id,
            description=description,
            action=action,
            shot_type=shot_type,
            camera_movement=camera_movement,
            duration=duration,
            visual_style=visual_style,
            color_tone=color_tone,
            base_image_filename=base_image_filename,
            dialogues=dialogues,
            narrations=narrations,
            sound_effects=sound_effects
        )
        
        return sub_scene

    def _parse_shot_type_from_string(self, shot_str: Optional[str]) -> ShotType:
        """解析镜头类型"""
        if not shot_str:
            return ShotType.MEDIUM_SHOT

        shot_mapping = {
            'close_up': ShotType.CLOSE_UP,
            'extreme_close_up': ShotType.EXTREME_CLOSE_UP,
            'medium_shot': ShotType.MEDIUM_SHOT,
            'long_shot': ShotType.LONG_SHOT,
            'full_shot': ShotType.FULL_SHOT,
            'over_shoulder': ShotType.OVER_SHOULDER,
            # Chinese aliases
            '特写': ShotType.CLOSE_UP,
            '大特写': ShotType.EXTREME_CLOSE_UP,
            '中景': ShotType.MEDIUM_SHOT,
            '远景': ShotType.LONG_SHOT,
            '全景': ShotType.FULL_SHOT,
            '过肩': ShotType.OVER_SHOULDER,
        }

        shot_str_lower = shot_str.lower().strip()
        for key, value in shot_mapping.items():
            if key in shot_str_lower or shot_str_lower in key:
                return value

        self.logger.warning(f"ScriptParserAgent | Unknown shot type: {shot_str}, defaulting to MEDIUM_SHOT")
        return ShotType.MEDIUM_SHOT

    def _parse_camera_movement_from_string(self, movement_str: Optional[str]) -> CameraMovement:
        """解析摄像机运动"""
        if not movement_str:
            return CameraMovement.STATIC

        movement_mapping = {
            'static': CameraMovement.STATIC,
            'pan': CameraMovement.PAN,
            'tilt': CameraMovement.TILT,
            'zoom': CameraMovement.ZOOM,
            'dolly': CameraMovement.DOLLY,
            'tracking': CameraMovement.TRACKING,
            # Chinese aliases
            '静止': CameraMovement.STATIC,
            '摇镜': CameraMovement.PAN,
            '俯仰': CameraMovement.TILT,
            '推拉': CameraMovement.ZOOM,
            '移动': CameraMovement.DOLLY,
            '跟踪': CameraMovement.TRACKING,
        }

        movement_str_lower = movement_str.lower().strip()
        for key, value in movement_mapping.items():
            if key in movement_str_lower or movement_str_lower in key:
                return value

        self.logger.warning(f"ScriptParserAgent | Unknown camera movement: {movement_str}, defaulting to STATIC")
        return CameraMovement.STATIC
