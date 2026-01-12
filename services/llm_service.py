"""LLM API service client - 用于提示词优化"""
import httpx
import asyncio
import re
from typing import Dict, Any, Optional, List, Literal
from config.settings import settings
from utils.retry import async_retry
import logging


def detect_language(text: str) -> Literal["zh", "en"]:
    """
    检测文本的主要语言

    Args:
        text: 要检测的文本

    Returns:
        "zh" 表示中文，"en" 表示英文
    """
    if not text or not text.strip():
        return "en"

    # 统计中文字符数量
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    # 统计英文单词数量
    english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))

    # 如果中文字符数量超过英文单词数量，判定为中文
    if chinese_chars > english_words:
        return "zh"
    else:
        return "en"


class LLMService:
    """LLM API服务封装 - 用于调用LLM进行提示词优化"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        初始化服务

        Args:
            api_key: API密钥
            api_url: API基础URL（OpenAI兼容接口）
            model: 模型名称
        """
        self.api_key = api_key or settings.fast_llm_api_key
        self.api_url = api_url or settings.fast_llm_api_url
        self.model = model or settings.fast_llm_model
        self.logger = logging.getLogger(__name__)

        # 构建 headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        # No timeout for LLM requests - they may take a long time for complex tasks
        self.client = httpx.AsyncClient(
            headers=headers,
            timeout=None
        )

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()

    @async_retry(
        max_attempts=3,
        backoff_factor=2.0,
        exceptions=(httpx.HTTPError, asyncio.TimeoutError)
    )
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> Dict[str, Any]:
        """
        调用LLM进行对话

        Args:
            messages: 对话消息列表，格式：[{"role": "user", "content": "..."}]
            temperature: 温度参数（0-2），控制随机性
            max_tokens: 最大生成token数
            **kwargs: 其他API参数

        Returns:
            API响应，包含生成的文本
        """
        # 构建请求 payload
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }

        self.logger.debug(f"Calling LLM with model: {self.model}")
        self.logger.debug(f"Messages: {messages}")

        try:
            # 使用完整URL拼接chat/completions端点
            url = f"{self.api_url}/chat/completions"

            self.logger.debug(f"Sending request to: {url}")
            response = await self.client.post(
                url,
                json=payload
            )

            self.logger.debug(f"Response status: {response.status_code}")
            response.raise_for_status()

            result = response.json()
            
            # Log response structure for debugging
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"].get("content", "")
                content_length = len(content) if content else 0
                self.logger.info(f"LLM response received | content_length={content_length} chars")
                self.logger.debug(f"Content preview: {content[:100]}..." if content else "Content is empty!")
            else:
                self.logger.warning(f"LLM response has no choices | response_keys={result.keys()}")

            return result

        except httpx.HTTPStatusError as e:
            self.logger.error(f"LLM API request failed: {e.response.status_code}")
            self.logger.error(f"Response: {e.response.text}")
            raise
        except Exception as e:
            self.logger.error(f"LLM API request error: {e}")
            raise

    async def optimize_prompt(
        self,
        original_prompt: str,
        optimization_context: str = "",
        temperature: float = 0.7
    ) -> str:
        """
        使用LLM优化提示词（通用方法，用于图片生成）

        Args:
            original_prompt: 原始提示词
            optimization_context: 优化上下文（如"用于图片生成"或"用于视频生成"）
            temperature: 温度参数

        Returns:
            优化后的提示词
        """
        # 检测原始提示词的语言
        language = detect_language(original_prompt)
        self.logger.info(f"Detected language: {language}")

        # 根据语言选择系统提示词和用户消息
        if language == "zh":
            system_prompt = """你是一位专业的提示词工程师，专门优化用于AI图片和视频生成的提示词。你的任务是增强提示词，使其更详细、更具体、更有效，以生成高质量的视觉内容。"""

            user_message = f"""请优化以下用于{optimization_context}的提示词。

原始提示词：{original_prompt}

要求：
1. 保持核心含义和意图
2. 添加更多视觉细节和具体性
3. 提高清晰度和结构
4. 确保风格和语气的一致性
5. 使其更适合AI视觉生成
6. 关键：添加明确的指令"画面中不要出现任何文字、字母、水印"，以确保生成的图像不包含任何文本元素
7. 只返回优化后的提示词，不要有任何解释或额外文本

优化后的提示词："""
        else:
            system_prompt = """You are an expert prompt engineer specializing in optimizing prompts for image and video generation AI models. Your task is to enhance prompts to be more detailed, specific, and effective for generating high-quality visual content."""

            user_message = f"""Please optimize the following prompt for {optimization_context}.

Original prompt: {original_prompt}

Requirements:
1. Keep the core meaning and intent
2. Add more visual details and specificity
3. Improve clarity and structure
4. Ensure consistency in style and tone
5. Make it more suitable for AI visual generation
6. CRITICAL: Add explicit instruction "no text, no words, no letters, no watermarks in the image" to ensure the generated image contains NO text elements whatsoever
7. Return ONLY the optimized prompt, without any explanations or additional text

Optimized prompt:"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        self.logger.info(f"Optimizing prompt for {optimization_context} in {language}")

        try:
            result = await self.chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=500
            )

            # 提取生成的文本
            if 'choices' in result and len(result['choices']) > 0:
                optimized_prompt = result['choices'][0]['message']['content'].strip()
                self.logger.info(f"Prompt optimized successfully")
                self.logger.debug(f"Original: {original_prompt[:100]}...")
                self.logger.debug(f"Optimized: {optimized_prompt[:100]}...")
                return optimized_prompt
            else:
                self.logger.warning("No choices in LLM response, using original prompt")
                return original_prompt

        except Exception as e:
            self.logger.error(f"Failed to optimize prompt: {e}")
            self.logger.warning("Falling back to original prompt")
            return original_prompt

    async def batch_optimize_prompts(
        self,
        prompts: List[str],
        optimization_context: str = "",
        temperature: float = 0.7
    ) -> List[str]:
        """
        批量优化提示词

        Args:
            prompts: 原始提示词列表
            optimization_context: 优化上下文
            temperature: 温度参数

        Returns:
            优化后的提示词列表
        """
        self.logger.info(f"Batch optimizing {len(prompts)} prompts")

        tasks = [
            self.optimize_prompt(prompt, optimization_context, temperature)
            for prompt in prompts
        ]

        optimized_prompts = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常情况，如果某个优化失败则使用原始提示词
        results = []
        for i, result in enumerate(optimized_prompts):
            if isinstance(result, Exception):
                self.logger.error(f"Failed to optimize prompt {i}: {result}")
                results.append(prompts[i])
            else:
                results.append(result)

        return results

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
