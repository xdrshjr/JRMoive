"""
Scene Continuity Judge Service

使用LLM判断相邻场景是否属于同一场景，从而决定是否使用前一视频的尾帧作为参考。
"""

import httpx
import json
import logging
from typing import Optional, Dict, Any
from config.settings import settings
from models.script_models import Scene


class SceneContinuityJudgeService:
    """场景连续性判断服务"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_key = settings.judge_llm_api_key
        self.api_url = settings.judge_llm_api_url
        self.model = settings.judge_llm_model
        self.temperature = 0.2  # 使用较低温度以获得更稳定的判断

        if not self.api_key:
            self.logger.warning("Judge LLM API key not configured")

    async def should_use_continuity(
        self,
        previous_scene: Scene,
        current_scene: Scene,
        character_dict: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        判断当前场景是否应该使用前一场景的尾帧作为参考

        Args:
            previous_scene: 前一个场景
            current_scene: 当前场景
            character_dict: 角色字典（可选）

        Returns:
            判断结果字典，包含：
            - should_use: bool - 是否应该使用连续性
            - confidence: float - 判断置信度 (0.0-1.0)
            - reason: str - 判断理由
            - scene_type: str - 场景类型 (same_scene/continuous_scene/different_scene)
        """
        if not self.api_key:
            self.logger.warning("Judge LLM not configured, defaulting to use continuity")
            return {
                "should_use": True,
                "confidence": 0.5,
                "reason": "LLM未配置，默认使用连续性",
                "scene_type": "unknown"
            }

        try:
            # 构建判断提示词
            prompt = self._build_judge_prompt(previous_scene, current_scene, character_dict)

            # 调用LLM
            response = await self._call_llm(prompt)

            # 解析响应
            result = self._parse_response(response)

            self.logger.info(
                f"Scene continuity judgment: {previous_scene.scene_id} -> {current_scene.scene_id}: "
                f"should_use={result['should_use']}, type={result['scene_type']}, "
                f"confidence={result['confidence']:.2f}"
            )

            return result

        except Exception as e:
            self.logger.error(f"Failed to judge scene continuity: {e}", exc_info=True)
            # 出错时默认使用连续性（保守策略）
            return {
                "should_use": True,
                "confidence": 0.5,
                "reason": f"判断失败，默认使用连续性: {str(e)}",
                "scene_type": "error"
            }

    def _build_judge_prompt(
        self,
        previous_scene: Scene,
        current_scene: Scene,
        character_dict: Optional[Dict[str, Any]] = None
    ) -> str:
        """构建LLM判断提示词"""

        # 提取场景信息
        prev_info = self._extract_scene_info(previous_scene, character_dict)
        curr_info = self._extract_scene_info(current_scene, character_dict)

        prompt = f"""你是一个专业的影视剧本分析专家。请分析以下两个相邻场景，判断它们是否属于同一场景或连续场景，从而决定在视频生成时是否应该使用前一场景的最后一帧作为参考，以保持视觉连贯性。

## 场景1（前一场景）
场景ID: {previous_scene.scene_id}
地点: {prev_info['location']}
时间: {prev_info['time']}
天气: {prev_info['weather']}
氛围: {prev_info['atmosphere']}
角色: {prev_info['characters']}
动作描述: {prev_info['action']}
镜头类型: {prev_info['shot_type']}
摄像机运动: {prev_info['camera_movement']}
对话: {prev_info['dialogues']}

## 场景2（当前场景）
场景ID: {current_scene.scene_id}
地点: {curr_info['location']}
时间: {curr_info['time']}
天气: {curr_info['weather']}
氛围: {curr_info['atmosphere']}
角色: {curr_info['characters']}
动作描述: {curr_info['action']}
镜头类型: {curr_info['shot_type']}
摄像机运动: {curr_info['camera_movement']}
对话: {curr_info['dialogues']}

## 判断标准

请根据以下标准判断是否应该使用视觉连续性：

1. **同一场景** (应该使用连续性)
   - 地点完全相同
   - 时间连续（无明显时间跳跃）
   - 角色连续出现
   - 动作连贯（如：坐下→站起来→走向门口）

2. **连续场景** (应该使用连续性)
   - 地点相邻或相关（如：客厅→厨房，室内→室外同一建筑）
   - 时间连续
   - 角色连续
   - 剧情连贯

3. **不同场景** (不应该使用连续性)
   - 地点完全不同（如：办公室→家里）
   - 时间跳跃（如：白天→夜晚，今天→明天）
   - 角色完全不同
   - 剧情不连贯（如：闪回、插叙）

## 输出格式

请以JSON格式输出判断结果，必须严格遵循以下格式：

```json
{{
  "should_use": true/false,
  "confidence": 0.0-1.0,
  "scene_type": "same_scene/continuous_scene/different_scene",
  "reason": "详细的判断理由，说明为什么做出这个判断"
}}
```

**重要提示**：
- should_use: true表示应该使用前一场景的尾帧，false表示不应该使用
- confidence: 判断的置信度，1.0表示非常确定，0.5表示不确定
- scene_type: 场景类型分类
- reason: 必须提供清晰的判断理由

请直接输出JSON，不要包含任何其他文字。"""

        return prompt

    def _extract_scene_info(
        self,
        scene: Scene,
        character_dict: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """提取场景信息用于判断"""

        # 提取角色信息
        characters = []
        if scene.characters:
            for char_name in scene.characters:
                if character_dict and char_name in character_dict:
                    char = character_dict[char_name]
                    characters.append(f"{char_name}（{char.get('appearance', '未描述')}）")
                else:
                    characters.append(char_name)

        # 提取对话信息
        dialogues = []
        if scene.dialogues:
            for dialogue in scene.dialogues[:3]:  # 只取前3条对话
                dialogues.append(f"{dialogue.character}: \"{dialogue.content}\"")

        return {
            "location": scene.location or "未指定",
            "time": scene.time or "未指定",
            "weather": scene.weather or "未指定",
            "atmosphere": scene.atmosphere or "未指定",
            "characters": ", ".join(characters) if characters else "无",
            "action": scene.action or "未描述",
            "shot_type": scene.shot_type.value if scene.shot_type else "未指定",
            "camera_movement": scene.camera_movement.value if scene.camera_movement else "未指定",
            "dialogues": " | ".join(dialogues) if dialogues else "无对话"
        }

    async def _call_llm(self, prompt: str) -> str:
        """调用LLM API"""

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.api_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一个专业的影视剧本分析专家，擅长分析场景连续性。"
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": self.temperature,
                    "max_tokens": 500
                }
            )

            response.raise_for_status()
            result = response.json()

            # 提取LLM响应
            content = result["choices"][0]["message"]["content"]
            return content

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析LLM响应"""

        try:
            # 尝试提取JSON
            # 移除可能的markdown代码块标记
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            # 解析JSON
            result = json.loads(response)

            # 验证必需字段
            if "should_use" not in result:
                raise ValueError("Missing 'should_use' field")
            if "confidence" not in result:
                result["confidence"] = 0.7  # 默认置信度
            if "scene_type" not in result:
                result["scene_type"] = "unknown"
            if "reason" not in result:
                result["reason"] = "未提供理由"

            # 确保类型正确
            result["should_use"] = bool(result["should_use"])
            result["confidence"] = float(result["confidence"])
            result["scene_type"] = str(result["scene_type"])
            result["reason"] = str(result["reason"])

            return result

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            self.logger.error(f"Failed to parse LLM response: {e}")
            self.logger.debug(f"Raw response: {response}")

            # 尝试基于关键词的简单解析
            response_lower = response.lower()
            if "should_use" in response_lower:
                if "true" in response_lower or "是" in response_lower or "应该" in response_lower:
                    return {
                        "should_use": True,
                        "confidence": 0.6,
                        "scene_type": "unknown",
                        "reason": "基于关键词解析"
                    }
                elif "false" in response_lower or "否" in response_lower or "不应该" in response_lower:
                    return {
                        "should_use": False,
                        "confidence": 0.6,
                        "scene_type": "unknown",
                        "reason": "基于关键词解析"
                    }

            # 默认返回使用连续性
            return {
                "should_use": True,
                "confidence": 0.5,
                "scene_type": "unknown",
                "reason": "解析失败，默认使用连续性"
            }
