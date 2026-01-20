"""Sora2 video generation API service client

This module provides a client for the Sora2 video generation API, which follows
the OpenAI format. It supports image-to-video generation with various styles,
resolutions, and durations.

Key Features:
- Image to video conversion (single or multiple images)
- Multiple style support (anime, comic, nostalgic, etc.)
- Character consistency via character_url parameter
- Storyboard mode for multi-shot videos
- Async task polling with progress tracking
- Comprehensive error handling and retry logic
"""
import httpx
import asyncio
import time
from typing import Dict, Any, Optional, Union, List
from pathlib import Path

from config.settings import settings
from utils.retry import async_retry
from backend.core.exceptions import ServiceException
import logging


class Sora2Service:
    """Sora2 API service wrapper for image-to-video conversion

    This service provides a high-level interface to the Sora2 video generation API,
    handling image uploads, task polling, error classification, and video downloads.

    Supported durations: 4, 8, 12 seconds (basic mode); 10, 15, 25 seconds (storyboard mode)
    Supported resolutions: 720x1280, 1280x720, 1024x1792, 1792x1024
    Supported styles: thanksgiving, comic, news, selfie, nostalgic, anime

    Example:
        ```python
        async with Sora2Service() as service:
            result = await service.image_to_video(
                image_path="scene.png",
                duration=8,
                size="1280x720",
                style="anime"
            )
            video_url = result['video_url']
            await service.download_video(video_url, Path("output.mp4"))
        ```
    """

    # Supported durations (in seconds)
    SUPPORTED_DURATIONS = [4, 8, 12]
    STORYBOARD_DURATIONS = [10, 15, 25]

    # Supported resolutions
    SUPPORTED_SIZES = [
        "720x1280",   # Portrait 9:16
        "1280x720",   # Landscape 16:9
        "1024x1792",  # Portrait 9:16 (high-res)
        "1792x1024"   # Landscape 16:9 (high-res)
    ]

    # Supported styles
    SUPPORTED_STYLES = [
        "thanksgiving",
        "comic",
        "news",
        "selfie",
        "nostalgic",
        "anime"
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        endpoint: Optional[str] = None,
        model: Optional[str] = None,
        default_size: Optional[str] = None,
        default_duration: Optional[int] = None,
        default_style: Optional[str] = None,
        watermark: bool = False,
        private: bool = False
    ):
        """Initialize Sora2 service

        Args:
            api_key: API key for authentication (defaults to settings)
            base_url: Base URL for API (defaults to settings)
            endpoint: API endpoint path (defaults to settings)
            model: Video generation model name (defaults to settings)
            default_size: Default video resolution (defaults to settings)
            default_duration: Default video duration in seconds (defaults to settings)
            default_style: Default video style (defaults to settings)
            watermark: Whether to add watermark to generated videos
            private: Whether videos should be private (no remix allowed)
        """
        # Load configuration from settings or use provided values
        self.api_key = api_key or settings.sora2_api_key
        self.base_url = base_url or settings.sora2_base_url
        self.endpoint = endpoint or settings.sora2_endpoint
        self.model = model or settings.sora2_model
        self.default_size = default_size or settings.sora2_default_size
        self.default_duration = default_duration or settings.sora2_default_duration
        self.default_style = default_style or settings.sora2_default_style
        self.watermark = watermark or settings.sora2_watermark
        self.private = private or settings.sora2_private

        self.logger = logging.getLogger(__name__)

        # Log service initialization
        self.logger.info(f"Sora2Service initialized with configuration:")
        self.logger.info(f"  - Base URL: {self.base_url}")
        self.logger.info(f"  - Endpoint: {self.endpoint}")
        self.logger.info(f"  - Model: {self.model}")
        self.logger.info(f"  - Default size: {self.default_size}")
        self.logger.info(f"  - Default duration: {self.default_duration}s")
        if self.default_style:
            self.logger.info(f"  - Default style: {self.default_style}")
        self.logger.debug(f"  - Watermark: {self.watermark}")
        self.logger.debug(f"  - Private: {self.private}")

        # Create HTTP client with Bearer token authentication
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}"
            },
            timeout=120.0  # Sora2 generation may take time
        )

    async def close(self):
        """Close HTTP client and cleanup resources"""
        await self.client.aclose()
        self.logger.info("Sora2Service HTTP client closed")

    @async_retry(
        max_attempts=3,
        backoff_factor=2.0,
        exceptions=(httpx.HTTPError, asyncio.TimeoutError)
    )
    async def image_to_video(
        self,
        image_path: Union[str, List[str]],
        duration: Optional[int] = None,
        size: Optional[str] = None,
        style: Optional[str] = None,
        prompt: str = "Generate video from this image",
        watermark: Optional[bool] = None,
        private: Optional[bool] = None,
        character_url: Optional[str] = None,
        character_timestamps: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Convert image(s) to video using Sora2 API

        This method uploads image(s) and creates a video generation task. It automatically
        polls the task status until completion or failure.

        Args:
            image_path: Path to image file (single) or list of paths (multiple)
            duration: Video duration in seconds (4, 8, or 12). Defaults to service default.
            size: Video resolution (e.g., "1280x720"). Defaults to service default.
            style: Video style (anime, comic, etc.). Optional.
            prompt: Text prompt describing the video to generate
            watermark: Whether to add watermark. Defaults to service default.
            private: Whether video should be private. Defaults to service default.
            character_url: URL to character reference video (for consistency)
            character_timestamps: Character appearance time range (format: "start,end")
            **kwargs: Additional API parameters

        Returns:
            Dict containing:
                - id: Task ID
                - status: "completed"
                - video_url: URL to download the generated video
                - progress: 100
                - enhanced_prompt: AI-enhanced prompt (if available)

        Raises:
            ServiceException: If API request fails or task fails
            TimeoutError: If task exceeds maximum wait time
            ValueError: If parameters are invalid
        """
        # Process single or multiple images
        image_paths = [image_path] if isinstance(image_path, str) else image_path

        # Use defaults if not specified
        duration = duration or self.default_duration
        size = size or self.default_size
        watermark = watermark if watermark is not None else self.watermark
        private = private if private is not None else self.private
        if style is None and self.default_style:
            style = self.default_style

        # Validate duration
        if duration not in self.SUPPORTED_DURATIONS and duration not in self.STORYBOARD_DURATIONS:
            # Find closest supported duration
            all_durations = self.SUPPORTED_DURATIONS + self.STORYBOARD_DURATIONS
            closest = min(all_durations, key=lambda x: abs(x - duration))
            self.logger.warning(
                f"Duration {duration}s is not supported. Adjusted to {closest}s "
                f"(Sora2 constraint: {self.SUPPORTED_DURATIONS} or {self.STORYBOARD_DURATIONS})"
            )
            duration = closest

        # Validate size
        if size not in self.SUPPORTED_SIZES:
            self.logger.warning(
                f"Size {size} may not be supported. Supported sizes: {self.SUPPORTED_SIZES}"
            )

        # Validate style
        if style and style not in self.SUPPORTED_STYLES:
            self.logger.warning(
                f"Style {style} may not be supported. Supported styles: {self.SUPPORTED_STYLES}"
            )

        # Log generation request
        if len(image_paths) == 1:
            self.logger.info(f"Generating video using single image from: {image_paths[0]}")
        else:
            self.logger.info(f"Generating video using {len(image_paths)} images")
            for idx, img_path in enumerate(image_paths, 1):
                self.logger.info(f"  - Image {idx}: {img_path}")

        self.logger.info(f"Video generation parameters:")
        self.logger.info(f"  - Duration: {duration}s")
        self.logger.info(f"  - Size: {size}")
        if style:
            self.logger.info(f"  - Style: {style}")
        if character_url:
            self.logger.info(f"  - Character URL: {character_url}")
            self.logger.info(f"  - Character timestamps: {character_timestamps}")
        self.logger.debug(f"  - Prompt: {prompt}")
        self.logger.debug(f"  - Watermark: {watermark}")
        self.logger.debug(f"  - Private: {private}")

        # Build form data
        files = {}
        file_handles = []

        try:
            # Open all image files
            for idx, img_path in enumerate(image_paths):
                file_handle = open(img_path, 'rb')
                file_handles.append(file_handle)

                if idx == 0:
                    # First image as main reference
                    files['input_reference'] = (Path(img_path).name, file_handle, 'image/png')
                else:
                    # Additional reference images (for scene continuity)
                    # Note: Sora2 may use these for character consistency
                    files[f'additional_reference_{idx}'] = (Path(img_path).name, file_handle, 'image/png')

            # Build form data fields
            data = {
                'model': self.model,
                'prompt': prompt,
                'seconds': str(duration),
                'size': size,
                'watermark': str(watermark).lower(),
                'private': str(private).lower()
            }

            # Add optional parameters
            if style:
                data['style'] = style

            if character_url:
                data['character_url'] = character_url
                if character_timestamps:
                    data['character_timestamps'] = character_timestamps

            self.logger.debug(f"Using model: {self.model}")
            self.logger.debug(f"Request data: {data}")

            try:
                # Send POST request with multipart/form-data
                response = await self.client.post(
                    self.endpoint,  # /v1/videos
                    data=data,
                    files=files,
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )

                self.logger.debug(f"Sora2 response status: {response.status_code}")
                self.logger.debug(f"Sora2 response headers: {dict(response.headers)}")

                response.raise_for_status()

                result = response.json()
                self.logger.debug(f"Sora2 response body: {str(result)[:500]}")

                # OpenAI format response: {"id": "video_xxx", "status": "queued", "progress": 0, ...}
                task_id = result.get('id')
                status = result.get('status')
                progress = result.get('progress', 0)

                self.logger.info(
                    f"Task {task_id} created, status: {status}, progress: {progress}%"
                )

                # Wait for completion if task is queued or processing
                if status in ['queued', 'processing', 'pending'] and task_id:
                    result = await self._wait_for_completion(task_id)

                return result

            except httpx.HTTPStatusError as e:
                error_response = None
                error_code = ""
                error_message = f"Sora2 API request failed with status {e.response.status_code}"

                # Try to parse error response
                try:
                    error_response = e.response.json()
                    if isinstance(error_response, dict):
                        # Extract error information (support multiple formats)
                        error_dict = error_response.get('error', error_response)
                        if isinstance(error_dict, dict):
                            error_code = error_dict.get('code', '')
                            error_msg = error_dict.get('message', '')
                        else:
                            error_code = error_response.get('code', '')
                            error_msg = error_response.get('message', '')

                        if error_msg:
                            error_message = error_msg
                except Exception:
                    # If JSON parsing fails, use raw text
                    error_response = {"raw_text": e.response.text}

                self.logger.error(f"Sora2 API request failed: {e.response.status_code}")
                self.logger.error(f"Error code: {error_code}")
                self.logger.error(f"Error message: {error_message}")
                self.logger.error(f"Response: {e.response.text[:500]}")

                # Throw enhanced ServiceException
                raise ServiceException(
                    message=error_message,
                    service_name="Sora2",
                    retryable=e.response.status_code >= 500,  # 5xx errors are retryable
                    original_error=e,
                    error_code=error_code,
                    error_type="video_generation_failed",
                    stage="video_generation",
                    api_response=error_response
                )

        finally:
            # Ensure all file handles are closed
            for file_handle in file_handles:
                try:
                    file_handle.close()
                except Exception as e:
                    self.logger.warning(f"Failed to close file handle: {e}")

    async def _wait_for_completion(
        self,
        task_id: str,
        poll_interval: float = 5.0,
        max_wait_time: float = 600.0
    ) -> Dict[str, Any]:
        """Wait for video generation task to complete

        This method polls the task status at regular intervals until the task
        completes, fails, or exceeds the maximum wait time.

        Args:
            task_id: Task ID to poll
            poll_interval: Polling interval in seconds
            max_wait_time: Maximum wait time in seconds

        Returns:
            Completed task result with video_url

        Raises:
            TimeoutError: If task exceeds maximum wait time
            ServiceException: If task fails
        """
        start_time = time.time()

        self.logger.info(
            f"Waiting for task {task_id} completion "
            f"(poll_interval={poll_interval}s, max_wait={max_wait_time}s)"
        )

        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait_time:
                self.logger.error(
                    f"Task {task_id} timeout after {max_wait_time}s "
                    f"(last elapsed: {elapsed:.1f}s)"
                )
                raise TimeoutError(
                    f"Video generation timeout after {max_wait_time}s"
                )

            # Query task status
            status = await self.check_task_status(task_id)
            state = status.get('status')  # OpenAI format uses 'status' field
            progress = status.get('progress', 0)

            self.logger.info(
                f"Task {task_id} status: {state}, progress: {progress}% "
                f"({elapsed:.1f}s elapsed)"
            )

            if state == 'completed':
                # Task completed, check for video_url
                video_url = status.get('video_url')
                if video_url:
                    self.logger.info(f"Task {task_id} completed with video URL: {video_url}")
                    return status
                else:
                    # If no video_url, try to fetch via content endpoint
                    self.logger.info(f"Task {task_id} completed, fetching video URL...")
                    video_url = await self._download_video_content(task_id)
                    status['video_url'] = video_url
                    return status

            elif state == 'failed':
                error_msg = status.get('error', 'Unknown error')
                error_code = ""

                # Parse error information
                if isinstance(error_msg, dict):
                    error_code = error_msg.get('code', '')
                    error_message = error_msg.get('message', str(error_msg))
                else:
                    error_message = str(error_msg)
                    # Try to extract error code from message
                    if 'code' in error_message.lower():
                        error_code = error_message

                self.logger.error(
                    f"Task {task_id} failed: code={error_code}, message={error_message}"
                )

                # Classify error type
                error_type = self._classify_error_type(error_code, error_message)

                # Check if error is retryable
                retryable = self._is_retryable_error(error_code, error_message)

                # Throw enhanced ServiceException
                raise ServiceException(
                    message=error_message,
                    service_name="Sora2",
                    retryable=retryable,
                    original_error=None,
                    error_code=error_code,
                    error_type=error_type,
                    stage="video_generation_polling",
                    api_response=status
                )

            # Sleep before next poll
            await asyncio.sleep(poll_interval)

    async def check_task_status(self, task_id: str) -> Dict[str, Any]:
        """Check video generation task status

        Args:
            task_id: Task ID to check

        Returns:
            Task status information containing:
                - id: Task ID
                - status: Current status (queued, processing, completed, failed)
                - progress: Progress percentage (0-100)
                - video_url: Video URL (if completed)
                - enhanced_prompt: AI-enhanced prompt (if available)
                - status_update_time: Last status update timestamp

        Raises:
            ServiceException: If API request fails
        """
        # OpenAI format task status query
        response = await self.client.get(f"{self.endpoint}/{task_id}")

        self.logger.debug(f"Task status response status: {response.status_code}")
        self.logger.debug(f"Task status response headers: {dict(response.headers)}")

        response.raise_for_status()

        # Verify JSON response
        content_type = response.headers.get('content-type', '')
        if 'application/json' not in content_type:
            self.logger.error(f"Unexpected content type: {content_type}")
            self.logger.error(f"Response body: {response.text[:1000]}")
            raise ValueError(f"API returned non-JSON response: {content_type}")

        result = response.json()
        self.logger.debug(f"Task status response body: {str(result)[:500]}")

        return result

    async def _download_video_content(self, task_id: str) -> str:
        """Get video download URL via OpenAI format content endpoint

        This method handles both redirect responses (302/307) and JSON responses
        that contain the video URL.

        Args:
            task_id: Task ID

        Returns:
            Video download URL

        Raises:
            ValueError: If video URL cannot be obtained
        """
        # OpenAI format: GET /v1/videos/{id}/content
        response = await self.client.get(
            f"{self.endpoint}/{task_id}/content",
            follow_redirects=False
        )

        self.logger.debug(f"Video content response status: {response.status_code}")
        self.logger.debug(f"Video content response headers: {dict(response.headers)}")

        # Handle redirect response (302/307/301)
        if response.status_code in (302, 307, 301):
            video_url = response.headers.get('Location')
            if video_url:
                self.logger.info(f"Got video URL from redirect: {video_url}")
                return video_url
            else:
                raise ValueError("Redirect response missing Location header")

        # Handle JSON response (200)
        response.raise_for_status()
        if 'application/json' in response.headers.get('content-type', ''):
            result = response.json()
            video_url = result.get('video_url') or result.get('url')
            if video_url:
                self.logger.info(f"Got video URL from JSON response: {video_url}")
                return video_url

        raise ValueError("Could not get video URL from content endpoint")

    async def download_video(
        self,
        video_url: str,
        save_path: Path
    ) -> Path:
        """Download generated video to local file

        Args:
            video_url: Video download URL
            save_path: Local path to save the video

        Returns:
            Actual saved file path

        Raises:
            Exception: If download fails
        """
        self.logger.info(f"Downloading video from {video_url}")
        self.logger.info(f"Save path: {save_path}")

        try:
            # Create new client for download (larger timeout)
            async with httpx.AsyncClient() as download_client:
                response = await download_client.get(
                    video_url,
                    timeout=300.0,  # Video files may be large
                    follow_redirects=True
                )
                response.raise_for_status()

                # Create parent directory if not exists
                save_path.parent.mkdir(parents=True, exist_ok=True)

                # Write video content to file
                with open(save_path, 'wb') as f:
                    f.write(response.content)

                file_size = len(response.content)
                self.logger.info(
                    f"Video saved to {save_path} "
                    f"(size: {file_size / 1024 / 1024:.2f} MB)"
                )
                return save_path

        except Exception as e:
            self.logger.error(f"Failed to download video: {e}")
            raise

    def _classify_error_type(self, error_code: str, error_message: str) -> str:
        """Classify error type based on error code and message

        Args:
            error_code: API error code
            error_message: Error message

        Returns:
            Error type string (audio_filtered, content_policy, copyright,
            invalid_prompt, or unknown)
        """
        error_upper = error_message.upper()
        error_code_upper = error_code.upper()

        # Audio filter error (usually dialog content issues)
        if 'AUDIO_FILTERED' in error_upper or 'AUDIO_FILTERED' in error_code_upper:
            return 'audio_filtered'

        # Content policy violation
        if 'CONTENT_POLICY' in error_upper or 'CONTENT_POLICY' in error_code_upper:
            return 'content_policy'

        # Copyright violation
        if 'COPYRIGHT' in error_upper or 'COPYRIGHT' in error_code_upper:
            return 'copyright'

        # Invalid prompt
        if 'INVALID_PROMPT' in error_upper or 'INVALID_PROMPT' in error_code_upper:
            return 'invalid_prompt'

        return 'unknown'

    def _is_retryable_error(self, error_code: str, error_message: str) -> bool:
        """Determine if error is retryable

        Args:
            error_code: API error code
            error_message: Error message

        Returns:
            True if error is retryable, False otherwise
        """
        # Non-retryable error codes (content moderation, violations, etc.)
        non_retryable_codes = [
            'PROMINENT_PEOPLE_FILTER_FAILED',  # Celebrity detection failed
            'CONTENT_POLICY_VIOLATION',  # Content policy violation
            'NSFW_CONTENT_DETECTED',  # NSFW content
            'COPYRIGHT_VIOLATION',  # Copyright violation
            'INVALID_INPUT',  # Invalid input
            'INVALID_PROMPT',  # Invalid prompt
        ]

        # Retryable error codes (temporary errors)
        retryable_codes = [
            'INTERNAL_ERROR',  # Internal error
            'SERVICE_UNAVAILABLE',  # Service unavailable
            'TIMEOUT',  # Timeout
            'RATE_LIMIT_EXCEEDED',  # Rate limit exceeded
            'INSUFFICIENT_QUOTA',  # Insufficient quota
        ]

        error_upper = error_message.upper()

        # Check for explicit non-retryable errors
        for code in non_retryable_codes:
            if code in error_code.upper() or code in error_upper:
                self.logger.warning(f"Non-retryable error detected: {code}")
                return False

        # Check for explicit retryable errors
        for code in retryable_codes:
            if code in error_code.upper() or code in error_upper:
                self.logger.info(f"Retryable error detected: {code}")
                return True

        # Default: treat unknown errors as retryable (conservative approach)
        self.logger.info(f"Unknown error type, treating as retryable: {error_message}")
        return True

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
