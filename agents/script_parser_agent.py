"""剧本解析Agent - 将文本剧本转换为结构化数据"""

import re
from typing import List, Dict, Any, Optional
from models.script_models import (
    Script, Scene, Character, Dialogue,
    ShotType, CameraMovement
)
from agents.base_agent import BaseAgent, AgentState
import logging


class ScriptParserAgent(BaseAgent):
    """剧本解析Agent - 将文本剧本转换为结构化数据"""

    def __init__(self, agent_id: str = "script_parser", config: Dict[str, Any] = None):
        super().__init__(agent_id, config or {})
        self.logger = logging.getLogger(__name__)

    async def execute(self, input_data: str) -> Script:
        """
        执行剧本解析

        Args:
            input_data: 原始剧本文本

        Returns:
            结构化的Script对象

        Raises:
            ValueError: 剧本格式错误
        """
        if not await self.validate_input(input_data):
            raise ValueError("Invalid script format")

        try:
            self.state = AgentState.RUNNING

            # 解析剧本元数据
            title = self._extract_title(input_data)
            author = self._extract_author(input_data)
            description = self._extract_description(input_data)

            # 解析角色
            characters = self._parse_characters(input_data)

            # 解析场景
            scenes = self._parse_scenes(input_data)

            # 构建Script对象
            script = Script(
                title=title,
                author=author,
                description=description,
                characters=characters,
                scenes=scenes
            )

            # 验证剧本
            errors = script.validate_script()
            if errors:
                self.logger.warning(f"Script validation warnings: {errors}")

            await self.on_complete(script)
            return script

        except Exception as e:
            await self.on_error(e)
            raise

    async def validate_input(self, input_data: str) -> bool:
        """验证输入数据"""
        if not input_data or not isinstance(input_data, str):
            return False

        # 至少包含一个场景标记
        if not re.search(r'##\s*场景\d+', input_data):
            return False

        return True

    def _extract_title(self, text: str) -> str:
        """提取剧本标题"""
        match = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
        return match.group(1).strip() if match else "未命名剧本"

    def _extract_author(self, text: str) -> Optional[str]:
        """提取作者信息"""
        match = re.search(r'作者[:：]\s*(.+)$', text, re.MULTILINE)
        return match.group(1).strip() if match else None

    def _extract_description(self, text: str) -> Optional[str]:
        """提取剧本简介"""
        match = re.search(r'简介[:：]\s*(.+)$', text, re.MULTILINE)
        return match.group(1).strip() if match else None

    def _parse_characters(self, text: str) -> List[Character]:
        """
        解析角色列表

        格式: - 角色名: 描述
        """
        characters = []
        char_section = re.search(
            r'##\s*角色\s*\n(.*?)(?=##|\Z)',
            text,
            re.DOTALL
        )

        if not char_section:
            return characters

        char_lines = char_section.group(1).strip().split('\n')
        for line in char_lines:
            line = line.strip()
            if line.startswith('-'):
                # 格式: - 小明: 25岁的Python开发者，戴黑框眼镜
                match = re.match(r'-\s*([^:：]+)[:：]\s*(.+)', line)
                if match:
                    name = match.group(1).strip()
                    description = match.group(2).strip()

                    # 尝试提取年龄和性别
                    age = None
                    gender = None

                    age_match = re.search(r'(\d+)岁', description)
                    if age_match:
                        age = int(age_match.group(1))

                    if '男' in description or 'male' in description.lower():
                        gender = 'male'
                    elif '女' in description or 'female' in description.lower():
                        gender = 'female'

                    characters.append(Character(
                        name=name,
                        description=description,
                        age=age,
                        gender=gender
                    ))

        return characters

    def _parse_scenes(self, text: str) -> List[Scene]:
        """
        解析场景列表

        场景格式:
        ## 场景N：场景名称
        地点: XXX
        时间: XXX
        ...
        """
        scenes = []

        # 分割场景
        scene_pattern = r'##\s*场景(\d+)[：:]\s*(.+?)\n(.*?)(?=##\s*场景\d+|$)'
        matches = re.finditer(scene_pattern, text, re.DOTALL)

        for match in matches:
            scene_num = match.group(1)
            scene_name = match.group(2).strip()
            scene_content = match.group(3).strip()

            # 解析场景属性
            scene_data = self._parse_scene_content(
                scene_id=f"scene_{scene_num.zfill(3)}",
                scene_name=scene_name,
                content=scene_content
            )

            if scene_data:
                scenes.append(scene_data)

        return scenes

    def _parse_scene_content(self, scene_id: str, scene_name: str,
                            content: str) -> Optional[Scene]:
        """解析单个场景的内容"""
        try:
            # 提取场景属性
            location = self._extract_field(content, r'地点[:：]\s*(.+)')
            time = self._extract_field(content, r'时间[:：]\s*(.+)')
            weather = self._extract_field(content, r'天气[:：]\s*(.+)')
            atmosphere = self._extract_field(content, r'氛围[:：]\s*(.+)')
            description = self._extract_field(content, r'描述[:：]\s*(.+)')

            # 提取镜头参数
            duration_str = self._extract_field(content, r'时长[:：]\s*([\d.]+)')
            duration = float(duration_str) if duration_str else None

            shot_type_str = self._extract_field(content, r'镜头[:：]\s*(.+)')
            shot_type = self._parse_shot_type(shot_type_str)

            camera_movement_str = self._extract_field(content, r'运镜[:：]\s*(.+)')
            camera_movement = self._parse_camera_movement(camera_movement_str)

            visual_style = self._extract_field(content, r'风格[:：]\s*(.+)')
            color_tone = self._extract_field(content, r'色调[:：]\s*(.+)')

            # 提取对话
            dialogues = self._extract_dialogues(content)

            # 提取旁白
            narrations = self._extract_narrations(content)

            # 提取音效
            sound_effects = self._extract_sound_effects(content)

            # 提取动作
            action = self._extract_field(content, r'动作[:：]\s*(.+)')

            # 提取出现的角色
            characters = list(set([d.character for d in dialogues]))

            return Scene(
                scene_id=scene_id,
                location=location or scene_name,
                time=time or "白天",
                weather=weather,
                atmosphere=atmosphere,
                description=description or f"{location}, {time}",
                shot_type=shot_type,
                camera_movement=camera_movement,
                duration=duration,
                characters=characters,
                dialogues=dialogues,
                narrations=narrations,
                sound_effects=sound_effects,
                action=action,
                visual_style=visual_style,
                color_tone=color_tone
            )

        except Exception as e:
            self.logger.error(f"Failed to parse scene {scene_id}: {e}")
            return None

    def _extract_field(self, text: str, pattern: str) -> Optional[str]:
        """提取字段值"""
        match = re.search(pattern, text, re.MULTILINE)
        return match.group(1).strip() if match else None

    def _extract_dialogues(self, content: str) -> List[Dialogue]:
        """
        提取对话（增强版）

        支持格式:
        1. 基础格式: 角色名：对话内容
        2. 带情绪: 角色名（情绪）：对话内容
        3. 带情绪和语音风格: 角色名（情绪|语音风格）：对话内容
        4. 多行对话: 角色名（情绪）：对话1\n对话2
        """
        dialogues = []
        dialogue_pattern = r'([^（\(]+)(?:[（\(]([^）\)]+)[）\)])?[:：]\s*(.+)'

        for line in content.split('\n'):
            line = line.strip()

            # 跳过字段标记行
            if any(keyword in line for keyword in
                   ['地点', '时间', '天气', '氛围', '描述', '镜头', '时长', '运镜', '风格', '色调', '动作']):
                continue

            # 跳过旁白和音效行（支持带参数的格式）
            if line.startswith('[旁白') or line.startswith('[音效'):
                continue

            match = re.match(dialogue_pattern, line)
            if match:
                character = match.group(1).strip()
                emotion_voice = match.group(2).strip() if match.group(2) else None
                content_text = match.group(3).strip()

                # 解析 emotion 和 voice_style
                emotion = None
                voice_style = None
                if emotion_voice:
                    if '|' in emotion_voice:
                        # 支持 "情绪|语音风格" 格式
                        parts = emotion_voice.split('|')
                        emotion = parts[0].strip()
                        voice_style = parts[1].strip() if len(parts) > 1 else None
                    else:
                        # 仅有情绪
                        emotion = emotion_voice

                # 处理多行对话（\n 分隔）
                if '\\n' in content_text:
                    content_text = content_text.replace('\\n', '\n')

                dialogues.append(Dialogue(
                    character=character,
                    content=content_text,
                    emotion=emotion,
                    voice_style=voice_style
                ))

        return dialogues

    def _extract_narrations(self, content: str) -> List['Narration']:
        """
        提取旁白

        格式: [旁白]：内容
        或    [旁白|语音风格]：内容
        """
        from models.script_models import Narration

        narrations = []
        narration_pattern = r'\[旁白(?:\|([^\]]+))?\][:：]\s*(.+)'

        for line in content.split('\n'):
            match = re.match(narration_pattern, line.strip())
            if match:
                voice_style = match.group(1).strip() if match.group(1) else None
                narration_content = match.group(2).strip()

                narrations.append(Narration(
                    content=narration_content,
                    voice_style=voice_style
                ))

        return narrations

    def _extract_sound_effects(self, content: str) -> List['SoundEffect']:
        """
        提取音效标记

        格式: [音效：描述]
        或    [音效@时间点：描述]  # 例如 [音效@1.5：键盘声]
        """
        from models.script_models import SoundEffect

        effects = []
        effect_pattern = r'\[音效(?:@([\d.]+))?[:：]\s*([^\]]+)\]'

        for line in content.split('\n'):
            match = re.search(effect_pattern, line.strip())
            if match:
                timing_str = match.group(1)
                description = match.group(2).strip()

                timing = float(timing_str) if timing_str else None

                effects.append(SoundEffect(
                    description=description,
                    timing=timing
                ))

        return effects

    def _parse_shot_type(self, shot_str: Optional[str]) -> ShotType:
        """解析镜头类型"""
        if not shot_str:
            return ShotType.MEDIUM_SHOT

        shot_mapping = {
            '特写': ShotType.CLOSE_UP,
            '大特写': ShotType.EXTREME_CLOSE_UP,
            '中景': ShotType.MEDIUM_SHOT,
            '远景': ShotType.LONG_SHOT,
            '全景': ShotType.FULL_SHOT,
            '过肩': ShotType.OVER_SHOULDER,
        }

        for key, value in shot_mapping.items():
            if key in shot_str:
                return value

        return ShotType.MEDIUM_SHOT

    def _parse_camera_movement(self, movement_str: Optional[str]) -> CameraMovement:
        """解析摄像机运动"""
        if not movement_str:
            return CameraMovement.STATIC

        movement_mapping = {
            '静止': CameraMovement.STATIC,
            '摇镜': CameraMovement.PAN,
            '俯仰': CameraMovement.TILT,
            '推拉': CameraMovement.ZOOM,
            '移动': CameraMovement.DOLLY,
            '跟踪': CameraMovement.TRACKING,
        }

        for key, value in movement_mapping.items():
            if key in movement_str:
                return value

        return CameraMovement.STATIC
