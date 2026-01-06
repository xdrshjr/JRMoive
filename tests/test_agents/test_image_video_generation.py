"""Tests for image and video generation modules"""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Import modules to test
from agents.image_generator_agent import ImageGenerationAgent
from agents.video_generator_agent import VideoGenerationAgent
from models.script_models import Scene, ShotType, CameraMovement


@pytest.fixture
def sample_scenes():
    """创建示例场景数据"""
    scenes = [
        Scene(
            scene_id="scene_001",
            location="办公室",
            time="清晨",
            description="程序员正在写代码",
            duration=3.0,
            shot_type=ShotType.MEDIUM_SHOT,
            camera_movement=CameraMovement.STATIC,
            visual_style="现代办公",
            color_tone="明亮"
        ),
        Scene(
            scene_id="scene_002",
            location="咖啡厅",
            time="下午",
            description="程序员在喝咖啡",
            duration=2.5,
            shot_type=ShotType.CLOSE_UP,
            camera_movement=CameraMovement.PAN,
            visual_style="温馨",
            color_tone="温暖"
        )
    ]
    return scenes


@pytest.fixture
def sample_image_results():
    """创建示例图片结果"""
    return [
        {
            'scene_id': 'scene_001',
            'image_path': './output/images/scene_001_test.png',
            'prompt': 'A programmer coding in an office',
            'config': {'width': 1920, 'height': 1080}
        },
        {
            'scene_id': 'scene_002',
            'image_path': './output/images/scene_002_test.png',
            'prompt': 'A programmer drinking coffee in a cafe',
            'config': {'width': 1920, 'height': 1080}
        }
    ]


class TestImageGenerationAgent:
    """测试ImageGenerationAgent"""

    @pytest.mark.asyncio
    async def test_validate_input_valid(self, sample_scenes):
        """测试有效输入验证"""
        agent = ImageGenerationAgent()

        result = await agent.validate_input(sample_scenes)

        assert result is True

    @pytest.mark.asyncio
    async def test_validate_input_empty(self):
        """测试空输入验证"""
        agent = ImageGenerationAgent()

        result = await agent.validate_input([])

        assert result is False

    @pytest.mark.asyncio
    async def test_generate_image_for_scene(self, sample_scenes):
        """测试单个场景图片生成"""
        agent = ImageGenerationAgent()

        # Mock the service
        mock_result = {
            'image_path': './output/images/test.png',
            'prompt': 'test prompt',
            'api_response': {'status': 'success'}
        }

        with patch.object(agent.service, 'generate_and_save',
                         new_callable=AsyncMock, return_value=mock_result):

            result = await agent._generate_image_for_scene(sample_scenes[0])

            assert result['scene_id'] == 'scene_001'
            assert 'image_path' in result
            assert 'prompt' in result

    @pytest.mark.asyncio
    async def test_concurrent_generation(self, sample_scenes):
        """测试并发图片生成"""
        agent = ImageGenerationAgent(config={'max_concurrent': 2})

        # Mock the service
        mock_result = {
            'image_path': './output/images/test.png',
            'prompt': 'test prompt',
            'api_response': {'status': 'success'}
        }

        with patch.object(agent.service, 'generate_and_save',
                         new_callable=AsyncMock, return_value=mock_result):

            results = await agent.execute_concurrent(sample_scenes)

            assert len(results) == len(sample_scenes)
            assert all('scene_id' in r for r in results)


class TestVideoGenerationAgent:
    """测试VideoGenerationAgent"""

    @pytest.mark.asyncio
    async def test_validate_input_valid(self, sample_image_results, sample_scenes):
        """测试有效输入验证"""
        agent = VideoGenerationAgent()

        result = await agent.validate_input((sample_image_results, sample_scenes))

        assert result is True

    @pytest.mark.asyncio
    async def test_validate_input_mismatch(self, sample_image_results, sample_scenes):
        """测试输入数量不匹配"""
        agent = VideoGenerationAgent()

        result = await agent.validate_input((sample_image_results, sample_scenes[:1]))

        assert result is False

    def test_map_camera_motion(self):
        """测试摄像机运动映射"""
        agent = VideoGenerationAgent()

        assert agent._map_camera_motion(CameraMovement.STATIC) == 'static'
        assert agent._map_camera_motion(CameraMovement.PAN) == 'pan'
        assert agent._map_camera_motion(CameraMovement.ZOOM) == 'zoom'

    @pytest.mark.asyncio
    async def test_generate_video_clip(self, sample_image_results, sample_scenes):
        """测试单个视频片段生成"""
        agent = VideoGenerationAgent()

        # Mock the service methods
        mock_api_result = {
            'video_url': 'http://example.com/video.mp4',
            'status': 'completed'
        }

        mock_video_path = Path('./output/videos/test.mp4')

        with patch.object(agent.service, 'image_to_video',
                         new_callable=AsyncMock, return_value=mock_api_result):
            with patch.object(agent.service, 'download_video',
                            new_callable=AsyncMock, return_value=mock_video_path):

                task_data = {
                    'image_result': sample_image_results[0],
                    'scene': sample_scenes[0]
                }

                result = await agent._generate_video_clip(task_data)

                assert result['scene_id'] == 'scene_001'
                assert 'video_path' in result
                assert result['duration'] == 3.0


class TestConcurrencyUtilities:
    """测试并发工具"""

    @pytest.mark.asyncio
    async def test_concurrency_limiter(self):
        """测试并发限制器"""
        from utils.concurrency import ConcurrencyLimiter

        limiter = ConcurrencyLimiter(max_concurrent=2)

        async def mock_task(x):
            await asyncio.sleep(0.1)
            return x * 2

        items = [1, 2, 3, 4, 5]
        results = await limiter.run_batch(mock_task, items)

        assert results == [2, 4, 6, 8, 10]

    @pytest.mark.asyncio
    async def test_rate_limiter(self):
        """测试速率限制器"""
        from utils.concurrency import RateLimiter
        import time

        limiter = RateLimiter(max_requests=2, time_window=1.0)

        start_time = time.time()

        # 快速发出3个请求
        for _ in range(3):
            await limiter.acquire()

        elapsed = time.time() - start_time

        # 第3个请求应该被延迟，所以总耗时应该大于1秒
        assert elapsed >= 1.0


class TestRetryDecorator:
    """测试重试装饰器"""

    @pytest.mark.asyncio
    async def test_retry_success(self):
        """测试成功的重试"""
        from utils.retry import async_retry

        @async_retry(max_attempts=3)
        async def mock_func():
            return "success"

        result = await mock_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_with_failure(self):
        """测试失败后重试"""
        from utils.retry import async_retry

        call_count = 0

        @async_retry(max_attempts=3, backoff_factor=0.1)
        async def mock_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not ready yet")
            return "success"

        result = await mock_func()

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_max_attempts_exceeded(self):
        """测试超过最大重试次数"""
        from utils.retry import async_retry

        @async_retry(max_attempts=2, backoff_factor=0.1)
        async def mock_func():
            raise ValueError("Always fails")

        with pytest.raises(ValueError):
            await mock_func()


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
