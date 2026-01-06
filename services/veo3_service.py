"""Veo3 video generation API service client"""
import httpx
import asyncio
import time
from typing import Dict, Any, Optional
from pathlib import Path

from config.settings import settings
from utils.retry import async_retry
import logging


class Veo3Service:
    """Veo3 API服务封装 - 图片到视频转换"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        endpoint: Optional[str] = None,
        model: Optional[str] = None,
        upload_endpoint: Optional[str] = None,
        skip_upload: Optional[bool] = None
    ):
        """
        初始化服务

        Args:
            api_key: API密钥
            base_url: API基础URL
            endpoint: API端点路径
            model: 视频生成模型名称
            upload_endpoint: 图片上传端点（如果需要上传）
            skip_upload: 是否跳过上传，直接使用 base64
        """
        self.api_key = api_key or settings.veo3_api_key
        self.base_url = base_url or settings.veo3_base_url
        self.endpoint = endpoint or settings.veo3_endpoint
        self.model = model or settings.veo3_model
        self.upload_endpoint = upload_endpoint or settings.veo3_upload_endpoint
        self.skip_upload = skip_upload if skip_upload is not None else settings.veo3_skip_upload
        self.logger = logging.getLogger(__name__)

        # 使用 Bearer token 认证
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=120.0  # Veo3生成视频可能较慢
        )

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()

    @async_retry(
        max_attempts=3,
        backoff_factor=2.0,
        exceptions=(httpx.HTTPError, asyncio.TimeoutError)
    )
    async def image_to_video(
        self,
        image_path: str,
        duration: float = 3.0,
        fps: int = 30,
        resolution: str = "1920x1080",
        motion_strength: float = 0.5,
        camera_motion: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        将图片转换为视频

        Args:
            image_path: 图片文件路径
            duration: 视频时长（秒）
            fps: 帧率
            resolution: 分辨率
            motion_strength: 运动强度（0.0-1.0）
            camera_motion: 摄像机运动类型（pan/tilt/zoom/static）
            **kwargs: 其他API参数

        Returns:
            API响应，包含任务ID或视频URL
        """
        # veo OpenAI 格式：使用 multipart/form-data 直接上传图片
        self.logger.info(f"Generating video using OpenAI format (multipart) from: {image_path}")

        # 构建 form data
        with open(image_path, 'rb') as image_file:
            files = {
                'input_reference': (Path(image_path).name, image_file, 'image/png')
            }

            # 构建其他字段
            # 注意：虽然使用 multipart/form-data，但某些 API 可能期望特定格式的字符串
            data = {
                'model': self.model,
                'prompt': kwargs.get('prompt', 'Generate video from this image'),
                'seconds': str(int(duration)),  # 必须是整数字符串
                'size': kwargs.get('size', '1920x1080'),  # 使用实际分辨率而不是宽高比
                'watermark': 'false'  # 字符串格式的布尔值
            }

            self.logger.debug(f"Using model: {self.model}")
            self.logger.debug(f"Form data: {data}")

            try:
                # 使用 multipart/form-data，需要临时移除 Content-Type header
                response = await self.client.post(
                    self.endpoint,  # /v1/videos
                    data=data,
                    files=files,
                    headers={"Authorization": f"Bearer {self.api_key}"}  # 只保留 Authorization
                )

                self.logger.debug(f"Veo response status: {response.status_code}")
                self.logger.debug(f"Veo response headers: {dict(response.headers)}")

                response.raise_for_status()

                result = response.json()
                self.logger.debug(f"Veo response: {result}")

                # OpenAI 格式返回：{"id": "video_xxx", "status": "queued", "progress": 0, ...}
                video_id = result.get('id')
                status = result.get('status')
                progress = result.get('progress', 0)

                self.logger.info(f"Video generation task created: {video_id}, status: {status}, progress: {progress}%")

                # 如果是异步任务（status=queued），等待完成
                if status in ['queued', 'processing'] and video_id:
                    result = await self._wait_for_completion(video_id)

                return result

            except httpx.HTTPStatusError as e:
                self.logger.error(f"Veo3 API request failed: {e.response.status_code}")
                self.logger.error(f"Response: {e.response.text}")
                raise

    async def _upload_image(self, image_path: str) -> str:
        """
        上传图片到Veo3服务器

        Args:
            image_path: 本地图片路径

        Returns:
            上传后的图片URL
        """
        with open(image_path, 'rb') as f:
            files = {'file': (Path(image_path).name, f, 'image/png')}

            # 注意：上传图片时需要移除 Content-Type header
            headers = {"Authorization": f"Bearer {self.api_key}"}

            # 使用配置的上传端点
            upload_endpoint = self.upload_endpoint or "/upload-image"

            async with httpx.AsyncClient(base_url=self.base_url) as upload_client:
                response = await upload_client.post(
                    upload_endpoint,
                    files=files,
                    headers=headers,
                    timeout=60.0
                )

                self.logger.debug(f"Upload response status: {response.status_code}")
                self.logger.debug(f"Upload response headers: {dict(response.headers)}")

                response.raise_for_status()

                # 检查响应内容
                response_text = response.text
                self.logger.debug(f"Upload raw response: {response_text[:500]}")

                if not response_text or not response_text.strip():
                    raise ValueError(f"Empty response from upload API. Status: {response.status_code}")

                try:
                    result = response.json()
                except Exception as json_err:
                    self.logger.error(f"Failed to parse upload response. Raw text: {response_text[:500]}")
                    raise ValueError(f"Invalid JSON response from upload: {json_err}") from json_err

                image_url = result.get('url')
                if not image_url:
                    self.logger.error(f"No 'url' in response: {result}")
                    raise ValueError(f"Upload response missing 'url' field: {result}")

                self.logger.info(f"Image uploaded: {image_url}")
                return image_url

    async def _wait_for_completion(
        self,
        task_id: str,
        poll_interval: float = 5.0,
        max_wait_time: float = 600.0
    ) -> Dict[str, Any]:
        """
        等待视频生成任务完成

        Args:
            task_id: 任务ID
            poll_interval: 轮询间隔（秒）
            max_wait_time: 最大等待时间（秒）

        Returns:
            完成后的任务结果

        Raises:
            TimeoutError: 超过最大等待时间
        """
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait_time:
                raise TimeoutError(
                    f"Video generation timeout after {max_wait_time}s"
                )

            # 查询任务状态
            status = await self.check_task_status(task_id)
            state = status.get('state')

            self.logger.info(
                f"Task {task_id} status: {state} "
                f"({elapsed:.1f}s elapsed)"
            )

            if state == 'completed':
                return status
            elif state == 'failed':
                error_msg = status.get('error', 'Unknown error')
                raise RuntimeError(f"Video generation failed: {error_msg}")

            await asyncio.sleep(poll_interval)

    async def check_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        检查任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态信息
        """
        response = await self.client.get(f"/task/{task_id}")
        response.raise_for_status()
        return response.json()

    async def download_video(
        self,
        video_url: str,
        save_path: Path
    ) -> Path:
        """
        下载生成的视频

        Args:
            video_url: 视频URL
            save_path: 保存路径

        Returns:
            实际保存的文件路径
        """
        self.logger.info(f"Downloading video from {video_url}")

        try:
            async with httpx.AsyncClient() as download_client:
                response = await download_client.get(
                    video_url,
                    timeout=300.0,  # 视频文件可能较大
                    follow_redirects=True
                )
                response.raise_for_status()

                save_path.parent.mkdir(parents=True, exist_ok=True)

                with open(save_path, 'wb') as f:
                    f.write(response.content)

                self.logger.info(f"Video saved to {save_path}")
                return save_path

        except Exception as e:
            self.logger.error(f"Failed to download video: {e}")
            raise

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
