"""LLM API service client - 用于提示词优化"""
import httpx
import asyncio
from typing import Dict, Any, Optional, List
from config.settings import settings
from utils.retry import async_retry
import logging


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

        self.client = httpx.AsyncClient(
            headers=headers,
            timeout=60.0
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

            response = await self.client.post(
                url,
                json=payload
            )

            self.logger.debug(f"Response status: {response.status_code}")
            response.raise_for_status()

            result = response.json()
            self.logger.debug(f"LLM response received")

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
        # 构建优化指令
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

        self.logger.info(f"Optimizing prompt for {optimization_context}")

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
