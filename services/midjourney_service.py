"""Midjourney API service client"""
import httpx
import asyncio
import base64
from typing import Dict, Any, Optional, List
from pathlib import Path
from config.settings import settings
from utils.retry import async_retry
import logging


class MidjourneyService:
    """Midjourney API服务封装 - 图片生成"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        bot_type: Optional[str] = None,
        poll_interval: float = 3.0,
        max_poll_attempts: int = 100,
        auto_upscale: Optional[bool] = None,
        upscale_index: Optional[int] = None
    ):
        """
        初始化服务

        Args:
            api_key: API密钥
            base_url: API基础URL
            bot_type: Bot类型 (MID_JOURNEY 或 NIJI_JOURNEY)
            poll_interval: 轮询间隔（秒）
            max_poll_attempts: 最大轮询次数
            auto_upscale: 是否自动upscale获取单张图（默认从配置读取）
            upscale_index: 选择upscale哪一张1-4（默认从配置读取）
        """
        self.api_key = api_key or settings.midjourney_api_key
        self.base_url = base_url or settings.midjourney_base_url
        self.bot_type = bot_type or settings.midjourney_bot_type
        self.poll_interval = poll_interval
        self.max_poll_attempts = max_poll_attempts
        self.auto_upscale = auto_upscale if auto_upscale is not None else settings.midjourney_auto_upscale
        self.upscale_index = upscale_index if upscale_index is not None else settings.midjourney_upscale_index
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

    @async_retry(
        max_attempts=3,
        backoff_factor=2.0,
        exceptions=(httpx.HTTPError, asyncio.TimeoutError)
    )
    async def submit_imagine(
        self,
        prompt: str,
        base64_array: Optional[List[str]] = None,
        notify_hook: Optional[str] = None,
        state: Optional[str] = None
    ) -> str:
        """
        提交Imagine任务

        Args:
            prompt: 提示词
            base64_array: 垫图base64数组（可选）
            notify_hook: 回调地址（可选）
            state: 自定义参数（可选）

        Returns:
            任务ID
        """
        payload = {
            "botType": self.bot_type,
            "prompt": prompt,
        }

        if base64_array:
            payload["base64Array"] = base64_array

        if notify_hook:
            payload["notifyHook"] = notify_hook

        if state:
            payload["state"] = state

        self.logger.info(f"Submitting Midjourney imagine task with prompt: {prompt[:50]}...")
        self.logger.debug(f"Using bot type: {self.bot_type}")
        self.logger.debug(f"Base URL: {self.base_url}")

        try:
            endpoint = "/mj/submit/imagine"
            self.logger.debug(f"POST endpoint: {endpoint}")

            response = await self.client.post(
                endpoint,
                json=payload
            )

            self.logger.debug(f"Response status: {response.status_code}")
            response.raise_for_status()

            # 检查响应内容
            response_text = response.text
            self.logger.debug(f"Raw response: {response_text[:200] if response_text else '(empty)'}")

            if not response_text or not response_text.strip():
                raise ValueError(f"Empty response from API. Status: {response.status_code}")

            try:
                result = response.json()
            except Exception as json_err:
                self.logger.error(f"Failed to parse JSON response. Raw text: {response_text[:500]}")
                raise ValueError(f"Invalid JSON response: {json_err}") from json_err

            self.logger.debug(f"Submit response: {result}")

            if result.get("code") != 1:
                raise ValueError(f"Submit failed: {result.get('description', 'Unknown error')}")

            task_id = result.get("result")
            if not task_id:
                raise ValueError("No task ID in response")

            self.logger.info(f"Task submitted successfully, task_id: {task_id}")
            return task_id

        except httpx.HTTPStatusError as e:
            self.logger.error(f"API request failed: {e.response.status_code}")
            self.logger.error(f"Response: {e.response.text}")
            raise

    @async_retry(
        max_attempts=3,
        backoff_factor=2.0,
        exceptions=(httpx.HTTPError, asyncio.TimeoutError)
    )
    async def submit_action(
        self,
        task_id: str,
        custom_id: str
    ) -> str:
        """
        提交动作任务（如Upscale、Variation等）

        Args:
            task_id: 原始任务ID
            custom_id: 按钮的customId（从buttons中获取）

        Returns:
            新任务ID
        """
        # 尝试多种可能的payload格式
        payload = {
            "customId": custom_id
        }

        self.logger.info(f"Submitting action for task {task_id}")
        self.logger.debug(f"Custom ID: {custom_id}")
        self.logger.debug(f"Payload: {payload}")

        try:
            response = await self.client.post(
                "/mj/submit/action",
                json=payload
            )

            self.logger.debug(f"Response status: {response.status_code}")

            # 先检查响应内容
            response_text = response.text
            self.logger.debug(f"Raw response: {response_text[:500] if response_text else '(empty)'}")

            response.raise_for_status()

            if not response_text or not response_text.strip():
                raise ValueError(f"Empty response from API. Status: {response.status_code}")

            try:
                result = response.json()
            except Exception as json_err:
                self.logger.error(f"Failed to parse JSON response. Raw text: {response_text[:500]}")
                raise ValueError(f"Invalid JSON response: {json_err}") from json_err

            self.logger.debug(f"Action submit response: {result}")

            if result.get("code") != 1:
                raise ValueError(f"Action submit failed: {result.get('description', 'Unknown error')}")

            new_task_id = result.get("result")
            if not new_task_id:
                raise ValueError("No task ID in action response")

            self.logger.info(f"Action submitted successfully, new task_id: {new_task_id}")
            return new_task_id

        except httpx.HTTPStatusError as e:
            self.logger.error(f"API request failed: {e.response.status_code}")
            self.logger.error(f"Response: {e.response.text}")
            raise

    @async_retry(
        max_attempts=3,
        backoff_factor=2.0,
        exceptions=(httpx.HTTPError, asyncio.TimeoutError)
    )
    async def fetch_task(self, task_id: str) -> Dict[str, Any]:
        """
        查询任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态信息
        """
        self.logger.debug(f"Fetching task status: {task_id}")

        try:
            response = await self.client.get(f"/mj/task/{task_id}/fetch")
            response.raise_for_status()

            result = response.json()
            self.logger.debug(f"Task status: {result.get('status')}, progress: {result.get('progress')}")

            return result

        except httpx.HTTPStatusError as e:
            self.logger.error(f"Failed to fetch task: {e.response.status_code}")
            self.logger.error(f"Response: {e.response.text}")
            raise

    async def wait_for_completion(
        self,
        task_id: str,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        等待任务完成

        Args:
            task_id: 任务ID
            progress_callback: 进度回调函数 (progress: str, status: str) -> None

        Returns:
            完成的任务信息

        Raises:
            TimeoutError: 超过最大轮询次数
            ValueError: 任务失败
        """
        self.logger.info(f"Waiting for task completion: {task_id}")

        for attempt in range(self.max_poll_attempts):
            task_info = await self.fetch_task(task_id)

            status = task_info.get("status")
            progress = task_info.get("progress", "0%")

            # 调用进度回调
            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback(progress, status)
                else:
                    progress_callback(progress, status)

            # 检查状态
            if status == "SUCCESS":
                self.logger.info(f"Task completed successfully: {task_id}")
                return task_info

            if status == "FAILURE" or status == "FAILED":
                fail_reason = task_info.get("failReason", "Unknown error")
                self.logger.error(f"Task failed: {fail_reason}")
                raise ValueError(f"Task failed: {fail_reason}")

            # 继续等待
            self.logger.debug(f"Task in progress ({attempt + 1}/{self.max_poll_attempts}): {progress}")
            await asyncio.sleep(self.poll_interval)

        raise TimeoutError(f"Task {task_id} did not complete within {self.max_poll_attempts * self.poll_interval}s")

    async def generate_image(
        self,
        prompt: str,
        base64_array: Optional[List[str]] = None,
        progress_callback: Optional[callable] = None,
        auto_upscale: Optional[bool] = None,
        upscale_index: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        生成图片（提交任务并等待完成，自动upscale获取单张高清图）

        Args:
            prompt: 图片描述提示词
            base64_array: 垫图base64数组（可选）
            progress_callback: 进度回调函数
            auto_upscale: 是否自动upscale（默认使用配置值）
            upscale_index: 选择upscale哪一张（1-4，默认使用配置值）
            **kwargs: 其他参数（notify_hook, state等）

        Returns:
            包含图片URL的响应数据
        """
        # 使用配置的默认值
        _auto_upscale = auto_upscale if auto_upscale is not None else self.auto_upscale
        _upscale_index = upscale_index if upscale_index is not None else self.upscale_index

        # 步骤1: 提交imagine任务（生成四宫格）
        self.logger.info(f"Step 1: Submitting imagine task...")
        task_id = await self.submit_imagine(
            prompt=prompt,
            base64_array=base64_array,
            notify_hook=kwargs.get("notify_hook"),
            state=kwargs.get("state")
        )

        # 步骤2: 等待imagine完成
        self.logger.info(f"Step 2: Waiting for imagine completion...")
        result = await self.wait_for_completion(task_id, progress_callback)

        # 如果不需要自动upscale，直接返回四宫格
        if not _auto_upscale:
            self.logger.info(f"Auto-upscale disabled, returning grid image")
            return {
                "task_id": task_id,
                "image_url": result.get("imageUrl"),
                "status": result.get("status"),
                "progress": result.get("progress"),
                "prompt": result.get("prompt"),
                "is_upscaled": False,
                "raw_response": result
            }

        # 步骤3: 自动upscale获取单张图
        self.logger.info(f"Step 3: Auto-upscaling image (U{_upscale_index})...")

        # 从buttons中找到对应的upscale按钮
        buttons = result.get("buttons", [])
        upscale_button = None

        for button in buttons:
            label = button.get("label", "")
            if label == f"U{_upscale_index}":
                upscale_button = button
                break

        if not upscale_button:
            self.logger.warning(f"Upscale button U{_upscale_index} not found, returning grid image")
            return {
                "task_id": task_id,
                "image_url": result.get("imageUrl"),
                "status": result.get("status"),
                "progress": result.get("progress"),
                "prompt": result.get("prompt"),
                "is_upscaled": False,
                "raw_response": result
            }

        # 提交upscale任务
        custom_id = upscale_button.get("customId")
        self.logger.info(f"Submitting upscale action with customId: {custom_id}")

        try:
            upscale_task_id = await self.submit_action(task_id, custom_id)

            # 等待upscale完成
            self.logger.info(f"Step 4: Waiting for upscale completion...")
            upscale_result = await self.wait_for_completion(upscale_task_id, progress_callback)

            # 返回upscale后的单张图片
            self.logger.info(f"Upscale completed! Got single high-quality image")
            return {
                "task_id": upscale_task_id,
                "original_task_id": task_id,
                "image_url": upscale_result.get("imageUrl"),
                "status": upscale_result.get("status"),
                "progress": upscale_result.get("progress"),
                "prompt": result.get("prompt"),
                "is_upscaled": True,
                "upscale_index": _upscale_index,
                "raw_response": upscale_result
            }

        except Exception as e:
            # Upscale失败，降级返回四宫格
            self.logger.warning(f"Upscale failed ({e}), falling back to grid image")
            return {
                "task_id": task_id,
                "image_url": result.get("imageUrl"),
                "status": result.get("status"),
                "progress": result.get("progress"),
                "prompt": result.get("prompt"),
                "is_upscaled": False,
                "upscale_error": str(e),
                "raw_response": result
            }

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

    async def generate_and_save(
        self,
        prompt: str,
        save_path: Path,
        base64_array: Optional[List[str]] = None,
        progress_callback: Optional[callable] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        生成图片并保存到本地（一步到位）

        Args:
            prompt: 图片描述提示词
            save_path: 保存路径
            base64_array: 垫图base64数组（可选）
            progress_callback: 进度回调函数
            **kwargs: 其他生成参数

        Returns:
            包含图片路径和API响应的字典
        """
        # 生成图片
        result = await self.generate_image(
            prompt=prompt,
            base64_array=base64_array,
            progress_callback=progress_callback,
            **kwargs
        )

        # 下载图片
        image_url = result.get('image_url')
        if not image_url:
            raise ValueError("No image URL in response")

        actual_path = await self.download_image(image_url, save_path)

        return {
            'image_path': str(actual_path),
            'prompt': prompt,
            'task_id': result.get('task_id'),
            'api_response': result
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
