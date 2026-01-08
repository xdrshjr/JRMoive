"""LLM Judge Service for character consistency scoring"""
import httpx
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from config.settings import settings
from utils.image_comparison import ImageComparator


class LLMJudgeService:
    """LLM评分服务 - 用于评估场景图片与角色参考图的一致性"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3
    ):
        """
        初始化LLM评分服务

        Args:
            api_key: API密钥（默认从settings读取）
            api_url: API URL（默认从settings读取）
            model: 模型名称（默认从settings读取）
            temperature: 温度参数（越低越稳定）
        """
        self.api_key = api_key or settings.judge_llm_api_key
        self.api_url = api_url or settings.judge_llm_api_url
        self.model = model or settings.judge_llm_model
        self.temperature = temperature

        self.logger = logging.getLogger(__name__)
        self.image_comparator = ImageComparator()

        if not self.api_key:
            raise ValueError("Judge LLM API key is required. Set JUDGE_LLM_API_KEY in .env")

    async def judge_character_consistency(
        self,
        reference_image_path: Path,
        scene_image_path: Path,
        scene_prompt: str,
        character_name: str
    ) -> Dict[str, Any]:
        """
        评估场景图片与角色参考图的一致性

        Args:
            reference_image_path: 角色参考图路径
            scene_image_path: 场景图片路径
            scene_prompt: 场景提示词
            character_name: 角色名称

        Returns:
            评分结果字典，包含：
            - score: 分数（0-100）
            - reasoning: 评分理由
            - consistency_aspects: 各方面一致性评分
        """
        try:
            # 拼接图片并转换为base64
            self.logger.info(f"Preparing comparison image for character: {character_name}")
            stitched_base64 = self.image_comparator.prepare_for_llm_judge(
                reference_image_path,
                scene_image_path,
                layout="horizontal"
            )

            # 构建评分提示词
            judge_prompt = self._build_judge_prompt(scene_prompt, character_name)

            # 调用LLM API
            response = await self._call_llm_api(stitched_base64, judge_prompt)

            # 解析响应
            result = self._parse_judge_response(response)

            self.logger.info(
                f"Character consistency score for {character_name}: {result['score']}/100"
            )

            return result

        except Exception as e:
            self.logger.error(f"Failed to judge character consistency: {e}")
            # 返回默认低分
            return {
                'score': 0,
                'reasoning': f"Error during judging: {str(e)}",
                'consistency_aspects': {},
                'error': str(e)
            }

    def _build_judge_prompt(self, scene_prompt: str, character_name: str) -> str:
        """
        构建评分提示词

        Args:
            scene_prompt: 场景提示词
            character_name: 角色名称

        Returns:
            评分提示词
        """
        prompt = f"""你是一个专业的角色一致性评估专家。请仔细观察这两张图片：
- 左侧是角色"{character_name}"的参考图
- 右侧是基于以下场景描述生成的图片：

场景描述：{scene_prompt}

请从以下几个方面评估右侧场景图中的角色与左侧参考图的一致性：

1. **面部特征一致性** (30分)：五官、脸型、表情等是否与参考图一致
2. **发型和发色一致性** (20分)：发型、发色、发长等是否与参考图一致
3. **服装风格一致性** (20分)：服装款式、颜色、配饰等是否与参考图一致
4. **整体气质一致性** (15分)：角色的整体气质、姿态是否与参考图一致
5. **场景融合度** (15分)：角色是否自然地融入场景，没有违和感

请按照以下JSON格式输出评分结果：

```json
{{
  "score": 总分(0-100),
  "reasoning": "详细的评分理由，说明各方面的表现",
  "consistency_aspects": {{
    "facial_features": 面部特征得分(0-30),
    "hairstyle": 发型得分(0-20),
    "clothing": 服装得分(0-20),
    "overall_temperament": 整体气质得分(0-15),
    "scene_integration": 场景融合度得分(0-15)
  }}
}}
```

请严格按照JSON格式输出，不要添加其他内容。"""

        return prompt

    async def _call_llm_api(self, image_base64: str, prompt: str) -> Dict[str, Any]:
        """
        调用LLM API进行评分

        Args:
            image_base64: base64编码的拼接图片
            prompt: 评分提示词

        Returns:
            API响应
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 构建请求体（兼容火山引擎方舟API格式）
        payload = {
            "model": self.model,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_image",
                            "image_url": f"data:image/png;base64,{image_base64}"
                        },
                        {
                            "type": "input_text",
                            "text": prompt
                        }
                    ]
                }
            ],
            "temperature": self.temperature
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.api_url}/responses",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()

    def _parse_judge_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析LLM评分响应

        Args:
            response: API响应

        Returns:
            解析后的评分结果
        """
        try:
            # 提取响应内容
            # 火山引擎方舟API的响应格式: response['output'] 是一个列表
            if 'output' in response and isinstance(response['output'], list):
                output_list = response['output']

                # 查找message类型的输出
                text_content = ""
                for item in output_list:
                    if item.get('type') == 'message':
                        # 从message的content中提取文本
                        content_items = item.get('content', [])
                        for content_item in content_items:
                            if content_item.get('type') == 'output_text':
                                text_content = content_item.get('text', '')
                                break
                        if text_content:
                            break

                if not text_content:
                    raise ValueError("No text content in response")

                # 提取JSON部分
                import json
                import re

                # 尝试提取JSON代码块
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', text_content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # 尝试直接解析整个文本
                    json_str = text_content

                # 解析JSON
                result = json.loads(json_str)

                # 验证必需字段
                if 'score' not in result:
                    raise ValueError("Missing 'score' field in response")

                return result

            else:
                raise ValueError("Invalid response format")

        except Exception as e:
            self.logger.error(f"Failed to parse judge response: {e}")
            self.logger.debug(f"Response: {response}")

            # 返回默认低分
            return {
                'score': 0,
                'reasoning': f"Failed to parse response: {str(e)}",
                'consistency_aspects': {},
                'parse_error': str(e)
            }

    async def batch_judge(
        self,
        reference_image_path: Path,
        candidate_images: List[Path],
        scene_prompt: str,
        character_name: str
    ) -> List[Dict[str, Any]]:
        """
        批量评估多个候选图片

        Args:
            reference_image_path: 角色参考图路径
            candidate_images: 候选场景图片路径列表
            scene_prompt: 场景提示词
            character_name: 角色名称

        Returns:
            评分结果列表
        """
        results = []

        for i, scene_image_path in enumerate(candidate_images):
            self.logger.info(f"Judging candidate {i+1}/{len(candidate_images)}")

            result = await self.judge_character_consistency(
                reference_image_path,
                scene_image_path,
                scene_prompt,
                character_name
            )

            result['candidate_index'] = i
            result['image_path'] = str(scene_image_path)
            results.append(result)

        return results

    def select_best_candidate(
        self,
        judge_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        从评分结果中选择最佳候选图片

        Args:
            judge_results: 评分结果列表

        Returns:
            最佳候选图片的评分结果
        """
        if not judge_results:
            raise ValueError("No judge results provided")

        # 按分数排序
        sorted_results = sorted(
            judge_results,
            key=lambda x: x.get('score', 0),
            reverse=True
        )

        best_result = sorted_results[0]

        self.logger.info(
            f"Best candidate: index={best_result.get('candidate_index')}, "
            f"score={best_result.get('score')}/100"
        )

        return best_result

    async def close(self):
        """关闭资源"""
        pass
