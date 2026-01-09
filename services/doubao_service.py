"""Doubao (豆包) API service client - 支持文生图和图生图"""
import httpx
import asyncio
import base64
from typing import Dict, Any, Optional
from pathlib import Path
from config.settings import settings
from utils.retry import async_retry
import logging


class DoubaoService:
    """豆包 API服务封装 - 图片生成（文生图 + 图生图）"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        endpoint: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        初始化服务

        Args:
            api_key: API密钥
            base_url: API基础URL
            endpoint: API端点路径
            model: 图像生成模型名称
        """
        self.api_key = api_key or settings.doubao_api_key
        self.base_url = base_url or settings.doubao_base_url
        self.endpoint = endpoint or settings.doubao_endpoint
        self.model = model or settings.doubao_model
        self.logger = logging.getLogger(__name__)

        # 构建 headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=60.0
        )

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()

    def _normalize_image_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化豆包 API 的响应格式

        豆包响应格式: {"data": [{"url": "..."}]}

        Returns:
            统一格式: {"image_url": "...", "raw_response": {...}}
        """
        normalized = {"raw_response": response}

        # 豆包格式
        if "data" in response and isinstance(response["data"], list) and len(response["data"]) > 0:
            first_image = response["data"][0]
            if "url" in first_image:
                normalized["image_url"] = first_image["url"]
            if "b64_json" in first_image:
                normalized["image_base64"] = first_image["b64_json"]
            return normalized

        # 直接格式
        if "url" in response:
            normalized["image_url"] = response["url"]

        return normalized

    async def _image_url_to_base64(self, image_url: str) -> str:
        """
        将图片URL转换为base64编码（用于图生图）

        Args:
            image_url: 图片URL

        Returns:
            base64编码的图片数据
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url, timeout=30.0, follow_redirects=True)
                response.raise_for_status()

                # 转换为base64
                image_data = response.content
                base64_data = base64.b64encode(image_data).decode('utf-8')

                return base64_data
        except Exception as e:
            self.logger.error(f"Failed to convert image URL to base64: {e}")
            raise

    async def _read_image_as_base64(self, image_path: Path) -> str:
        """
        读取本地图片并转换为base64编码

        Args:
            image_path: 本地图片路径

        Returns:
            base64编码的图片数据
        """
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()

            base64_data = base64.b64encode(image_data).decode('utf-8')
            return base64_data
        except Exception as e:
            self.logger.error(f"Failed to read image as base64: {e}")
            raise

    @async_retry(
        max_attempts=3,
        backoff_factor=2.0,
        exceptions=(httpx.HTTPError, asyncio.TimeoutError)
    )
    async def generate_image(
        self,
        prompt: str,
        width: int = 1920,
        height: int = 1080,
        quality: str = "high",
        style: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        seed: Optional[int] = None,
        cfg_scale: Optional[float] = None,
        steps: Optional[int] = None,
        reference_image: Optional[str] = None,  # 参考图URL或base64或本地路径
        reference_image_weight: float = 0.7,  # 参考图权重 (0.0-1.0)
        **kwargs
    ) -> Dict[str, Any]:
        """
        生成图片（文生图或图生图）

        Args:
            prompt: 图片描述提示词
            width: 图片宽度
            height: 图片高度
            quality: 质量（high/medium/low）
            style: 风格（可选）
            negative_prompt: 负面提示词
            seed: 随机种子
            cfg_scale: CFG引导强度
            steps: 推理步数
            reference_image: 参考图（URL/base64/本地路径），提供时为图生图
            reference_image_weight: 参考图权重，控制对参考图的遵循程度
            **kwargs: 其他API参数

        Returns:
            API响应，包含图片URL或Base64数据
        """
        # 处理参考图
        image_data = None
        if reference_image:
            # 判断是URL、base64还是本地路径
            if reference_image.startswith('http://') or reference_image.startswith('https://'):
                # URL - 转换为base64
                self.logger.info(f"Converting reference image URL to base64")
                image_data = await self._image_url_to_base64(reference_image)
            elif Path(reference_image).exists():
                # 本地路径 - 读取并转换为base64
                self.logger.info(f"Reading local reference image: {reference_image}")
                image_data = await self._read_image_as_base64(Path(reference_image))
            else:
                # 假设已经是base64
                image_data = reference_image
                self.logger.info(f"Using provided base64 reference image")

        # 豆包API不支持seed、cfg_scale、steps参数，从kwargs中移除这些参数
        unsupported_params = ['seed', 'cfg_scale', 'steps']
        filtered_kwargs = {k: v for k, v in kwargs.items() if k not in unsupported_params}

        if any(param in kwargs for param in unsupported_params):
            removed = [p for p in unsupported_params if p in kwargs]
            self.logger.debug(f"Removed unsupported Doubao API parameters: {removed}")

        # 构建请求 payload
        payload = {
            "model": self.model,
            "prompt": prompt,
            "size": f"{width}x{height}" if width == height else "2K",  # 豆包支持方形或2K
            "response_format": "url",  # 返回URL
            "stream": False,
            "watermark": filtered_kwargs.get('watermark', settings.doubao_watermark)  # 使用配置的水印设置，默认false
        }

        # 图生图参数
        if image_data:
            # 豆包图生图使用 "image" 字段
            payload["image"] = f"data:image/png;base64,{image_data}" if not image_data.startswith('data:') else image_data
            payload["sequential_image_generation"] = "disabled"  # 禁用连续生成
            self.logger.info(f"Image-to-image mode enabled with reference weight {reference_image_weight}")

        # 可选参数 - 只添加豆包API实际支持的参数
        if style:
            payload["style"] = style

        if negative_prompt:
            self.logger.debug(f"Note: negative_prompt may not be supported by Doubao API")
            # payload["negative_prompt"] = negative_prompt  # 暂时注释，可能不支持

        # Note: seed, cfg_scale, steps are NOT supported by Doubao API
        if seed is not None:
            self.logger.debug(f"Ignoring seed parameter (not supported by Doubao API): {seed}")

        if cfg_scale is not None:
            self.logger.debug(f"Ignoring cfg_scale parameter (not supported by Doubao API): {cfg_scale}")

        if steps is not None:
            self.logger.debug(f"Ignoring steps parameter (not supported by Doubao API): {steps}")

        mode = "image-to-image" if image_data else "text-to-image"
        self.logger.info(f"Generating image ({mode}) with prompt: {prompt[:50]}...")
        self.logger.debug(f"Using model: {self.model}")
        self.logger.debug(f"Request payload keys: {list(payload.keys())}")

        try:
            response = await self.client.post(
                self.endpoint,
                json=payload
            )

            self.logger.debug(f"Response status: {response.status_code}")
            self.logger.debug(f"Response headers: {dict(response.headers)}")

            response.raise_for_status()

            response_text = response.text
            self.logger.debug(f"Raw response: {response_text[:200]}")

            if not response_text or not response_text.strip():
                raise ValueError(f"Empty response from API. Status: {response.status_code}")

            try:
                result = response.json()
            except Exception as json_err:
                self.logger.error(f"Failed to parse JSON response. Raw text: {response_text[:500]}")
                raise ValueError(f"Invalid JSON response: {json_err}") from json_err

            self.logger.info(f"Image generated successfully ({mode})")
            self.logger.debug(f"API response structure: {list(result.keys()) if isinstance(result, dict) else type(result)}")

            # 转换为统一格式
            normalized_result = self._normalize_image_response(result)

            return normalized_result

        except httpx.HTTPStatusError as e:
            self.logger.error(f"API request failed: {e.response.status_code}")
            self.logger.error(f"Response: {e.response.text}")
            raise

    async def download_image(
        self,
        image_url: str,
        save_path: Path
    ) -> Path:
        """
        下载图片到本地

        Args:
            image_url: 图片URL
            save_path: 保存路径

        Returns:
            实际保存的文件路径
        """
        self.logger.info(f"Downloading image from {image_url}")

        try:
            async with httpx.AsyncClient() as download_client:
                response = await download_client.get(
                    image_url,
                    timeout=120.0,
                    follow_redirects=True
                )
                response.raise_for_status()

                # 确保目录存在
                save_path.parent.mkdir(parents=True, exist_ok=True)

                # 保存图片
                with open(save_path, 'wb') as f:
                    f.write(response.content)

                self.logger.info(f"Image saved to {save_path}")
                return save_path

        except Exception as e:
            self.logger.error(f"Failed to download image: {e}")
            raise

    async def save_base64_image(
        self,
        base64_data: str,
        save_path: Path
    ) -> Path:
        """
        保存Base64编码的图片

        Args:
            base64_data: Base64编码的图片数据
            save_path: 保存路径

        Returns:
            实际保存的文件路径
        """
        self.logger.info(f"Saving base64 image to {save_path}")

        try:
            # 移除data URL前缀（如果存在）
            if ',' in base64_data:
                base64_data = base64_data.split(',')[1]

            # 解码Base64数据
            image_data = base64.b64decode(base64_data)

            # 确保目录存在
            save_path.parent.mkdir(parents=True, exist_ok=True)

            # 保存图片
            with open(save_path, 'wb') as f:
                f.write(image_data)

            self.logger.info(f"Base64 image saved to {save_path}")
            return save_path

        except Exception as e:
            self.logger.error(f"Failed to save base64 image: {e}")
            raise

    async def generate_and_save(
        self,
        prompt: str,
        save_path: Path,
        reference_image: Optional[str] = None,
        reference_image_weight: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """
        生成图片并保存到本地（一步到位）

        Args:
            prompt: 图片描述提示词
            save_path: 保存路径
            reference_image: 参考图（URL/base64/本地路径）
            reference_image_weight: 参考图权重
            **kwargs: 其他生成参数

        Returns:
            包含图片路径和API响应的字典
        """
        # 生成图片
        result = await self.generate_image(
            prompt,
            reference_image=reference_image,
            reference_image_weight=reference_image_weight,
            **kwargs
        )

        # 保存图片
        if 'image_url' in result:
            # 从URL下载
            actual_path = await self.download_image(result['image_url'], save_path)
        elif 'image_base64' in result:
            # 从Base64保存
            actual_path = await self.save_base64_image(result['image_base64'], save_path)
        else:
            raise ValueError("API response doesn't contain image_url or image_base64")

        return {
            'image_path': str(actual_path),
            'prompt': prompt,
            'reference_image': reference_image,
            'api_response': result
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
