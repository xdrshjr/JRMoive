"""提示词优化工具 - 使用LLM优化图片和视频生成的提示词"""
from typing import Optional
from services.llm_service import LLMService
from config.settings import settings
import logging


class PromptOptimizer:
    """提示词优化器 - 使用LLM优化提示词以提高生成质量"""

    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        enabled: Optional[bool] = None
    ):
        """
        初始化优化器

        Args:
            llm_service: LLM服务实例（可选，默认创建新实例）
            enabled: 是否启用优化（可选，默认从settings读取）
        """
        self.llm_service = llm_service or LLMService()
        self.enabled = enabled if enabled is not None else settings.enable_prompt_optimization
        self.logger = logging.getLogger(__name__)

        if not self.enabled:
            self.logger.info("Prompt optimization is disabled")
        else:
            self.logger.info("Prompt optimization is enabled")

    async def optimize_image_prompt(
        self,
        original_prompt: str,
        temperature: float = 0.7
    ) -> str:
        """
        优化图片生成提示词

        Args:
            original_prompt: 原始提示词
            temperature: 温度参数

        Returns:
            优化后的提示词（如果优化失败或未启用，返回原始提示词）
        """
        if not self.enabled:
            return original_prompt

        if not original_prompt or not original_prompt.strip():
            self.logger.warning("Empty prompt provided, skipping optimization")
            return original_prompt

        try:
            optimized = await self.llm_service.optimize_prompt(
                original_prompt=original_prompt,
                optimization_context="image generation",
                temperature=temperature
            )
            return optimized
        except Exception as e:
            self.logger.error(f"Image prompt optimization failed: {e}")
            return original_prompt

    async def optimize_video_prompt(
        self,
        original_prompt: str,
        temperature: float = 0.7
    ) -> str:
        """
        优化视频生成提示词

        Args:
            original_prompt: 原始提示词
            temperature: 温度参数

        Returns:
            优化后的提示词（如果优化失败或未启用，返回原始提示词）
        """
        if not self.enabled:
            return original_prompt

        if not original_prompt or not original_prompt.strip():
            self.logger.warning("Empty prompt provided, skipping optimization")
            return original_prompt

        try:
            optimized = await self.llm_service.optimize_prompt(
                original_prompt=original_prompt,
                optimization_context="video generation with motion and dialogue",
                temperature=temperature
            )
            return optimized
        except Exception as e:
            self.logger.error(f"Video prompt optimization failed: {e}")
            return original_prompt

    async def close(self):
        """关闭资源"""
        await self.llm_service.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
