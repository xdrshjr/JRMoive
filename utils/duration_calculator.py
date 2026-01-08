"""
Smart duration calculator for scenes based on dialogue and action content.

根据对话和动作内容智能计算场景时长。
"""
from typing import List, Optional
import re


class DurationCalculator:
    """智能场景时长计算器"""

    @staticmethod
    def calculate_scene_duration(scene, override: bool = False) -> float:
        """
        根据场景内容计算最优时长。

        Args:
            scene: Scene 对象
            override: 如果为 True，即使已设置时长也重新计算

        Returns:
            计算出的时长（秒），限制在 1-10 秒范围内
        """
        # 导入放在这里避免循环依赖
        from config.settings import settings

        # 尊重明确设置的时长（除非要求覆盖）
        if not override and scene.duration is not None:
            return scene.duration

        total_time = 0.0

        # 1. 基础时长（场景建立）
        total_time += settings.duration_base_time

        # 2. 对话时长
        if scene.dialogues:
            dialogue_time = DurationCalculator._calculate_dialogue_time(scene.dialogues)
            total_time += dialogue_time

        # 3. 旁白时长
        if scene.narrations:
            narration_time = DurationCalculator._calculate_narration_time(scene.narrations)
            total_time += narration_time

        # 4. 动作时长
        if scene.action:
            action_time = DurationCalculator._calculate_action_time(scene.action)
            total_time += action_time

        # 5. 应用缓冲系数（10% 余量保证自然节奏）
        total_time *= settings.duration_buffer_multiplier

        # 6. 确保最小时长
        total_time = max(total_time, settings.duration_min_guaranteed)

        # 7. 限制在 API 约束范围内 [1.0, 10.0]
        return max(1.0, min(10.0, total_time))

    @staticmethod
    def _calculate_dialogue_time(dialogues: List) -> float:
        """
        计算所有对话所需时间。

        Args:
            dialogues: Dialogue 对象列表

        Returns:
            对话总时长（秒）
        """
        from config.settings import settings

        total = 0.0

        for dialogue in dialogues:
            content = dialogue.content

            # 检测并计算中文字符
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))

            # 检测并计算英文单词
            english_words = len(re.findall(r'\b[a-zA-Z]+\b', content))

            # 计算基础朗读时间
            base_time = 0.0
            if chinese_chars > 0:
                base_time += chinese_chars / settings.duration_chinese_chars_per_sec
            if english_words > 0:
                base_time += english_words / settings.duration_english_words_per_sec

            # 添加情绪停顿时间
            emotion_padding = DurationCalculator._get_emotion_padding(dialogue.emotion)

            total += base_time + emotion_padding

        return total

    @staticmethod
    def _calculate_narration_time(narrations: List) -> float:
        """
        计算旁白所需时间（比对话稍慢，更清晰）。

        Args:
            narrations: Narration 对象列表

        Returns:
            旁白总时长（秒）
        """
        from config.settings import settings

        total = 0.0

        for narration in narrations:
            content = narration.content

            # 检测并计算中文字符
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))

            # 检测并计算英文单词
            english_words = len(re.findall(r'\b[a-zA-Z]+\b', content))

            # 计算基础朗读时间
            base_time = 0.0
            if chinese_chars > 0:
                base_time += chinese_chars / settings.duration_chinese_chars_per_sec
            if english_words > 0:
                base_time += english_words / settings.duration_english_words_per_sec

            # 旁白比对话慢 10%，更清晰
            base_time *= 1.1

            # 旁白添加固定停顿
            total += base_time + 0.2

        return total

    @staticmethod
    def _calculate_action_time(action: str) -> float:
        """
        根据动作描述估算所需时间。

        Args:
            action: 动作描述字符串

        Returns:
            动作时长（秒）
        """
        from config.settings import settings

        action_lower = action.lower()

        # 复杂动作关键词（需要更多时间）
        complex_keywords = ['打斗', '战斗', '对决', '拥抱', '亲吻', 'fight', 'battle', 'hug', 'kiss']

        # 移动动作关键词
        movement_keywords = ['走', '跑', '移动', '追', '逃', '跳', '飞', '游',
                            'walk', 'run', 'move', 'chase', 'jump', 'fly', 'swim']

        # 静态动作关键词
        static_keywords = ['坐', '站', '看', '想', '说', '听', '笑', '哭',
                          'sit', 'stand', 'look', 'think', 'say', 'listen', 'smile', 'cry']

        # 检测动作类型并返回相应时长
        if any(kw in action_lower for kw in complex_keywords):
            return 2.5
        elif any(kw in action_lower for kw in movement_keywords):
            return 2.0
        elif any(kw in action_lower for kw in static_keywords):
            return 1.0
        else:
            # 默认动作时长
            return settings.duration_action_base

    @staticmethod
    def _get_emotion_padding(emotion: Optional[str]) -> float:
        """
        根据情绪类型获取停顿填充时间。

        Args:
            emotion: 情绪描述（可选）

        Returns:
            情绪停顿时长（秒）
        """
        from config.settings import settings

        if not emotion:
            return settings.duration_emotion_padding

        emotion_lower = emotion.lower()

        # 快速情绪（较少停顿）
        fast_emotions = ['兴奋', '激动', '急切', '愤怒',
                        'excited', 'eager', 'urgent', 'angry']

        # 慢速情绪（较多停顿）
        slow_emotions = ['悲伤', '沉思', '疲惫', '忧郁', '思考',
                        'sad', 'thoughtful', 'tired', 'melancholy', 'pensive']

        # 根据情绪类型返回不同的停顿时间
        if any(e in emotion_lower for e in fast_emotions):
            return 0.2
        elif any(e in emotion_lower for e in slow_emotions):
            return 0.5
        else:
            # 默认情绪停顿
            return settings.duration_emotion_padding

    @staticmethod
    def apply_to_script(script, override: bool = False):
        """
        将智能时长计算应用到脚本的所有场景。

        Args:
            script: Script 对象
            override: 如果为 True，重新计算所有场景的时长（包括已设置的）
        """
        for scene in script.scenes:
            calculated_duration = DurationCalculator.calculate_scene_duration(scene, override)

            # 只在时长为 None 或 override 为 True 时设置
            if scene.duration is None or override:
                scene.duration = calculated_duration
