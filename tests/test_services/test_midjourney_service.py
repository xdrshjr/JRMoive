"""Tests for Midjourney service"""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from services.midjourney_service import MidjourneyService


@pytest.fixture
def mock_submit_response():
    """Mock successful submit response"""
    return {
        "code": 1,
        "description": "Submit success",
        "result": "1730621718151844",
        "properties": {
            "discordChannelId": "1300842676874379336",
            "discordInstanceId": "1572398367386955776"
        }
    }


@pytest.fixture
def mock_task_response_in_progress():
    """Mock task response in progress"""
    return {
        "id": "1730621826053455",
        "action": "IMAGINE",
        "customId": "",
        "botType": "MID_JOURNEY",
        "prompt": "cat --v 6.1",
        "promptEn": "cat --v 6.1",
        "description": "Processing",
        "state": "",
        "submitTime": 1730621826053,
        "startTime": 1730621828024,
        "finishTime": 0,
        "imageUrl": "",
        "status": "IN_PROGRESS",
        "progress": "50%",
        "failReason": "",
        "buttons": [],
        "maskBase64": "",
        "properties": {
            "finalPrompt": "cat --v 6.1",
            "finalZhPrompt": ""
        }
    }


@pytest.fixture
def mock_task_response_success():
    """Mock task response success"""
    return {
        "id": "1730621826053455",
        "action": "IMAGINE",
        "customId": "",
        "botType": "MID_JOURNEY",
        "prompt": "cat --v 6.1",
        "promptEn": "cat --v 6.1",
        "description": "Submit success",
        "state": "",
        "submitTime": 1730621826053,
        "startTime": 1730621828024,
        "finishTime": 1730621855817,
        "imageUrl": "https://example.com/cat.png",
        "status": "SUCCESS",
        "progress": "100%",
        "failReason": "",
        "buttons": [
            {
                "customId": "MJ::JOB::upsample::1::abc123",
                "emoji": "",
                "label": "U1",
                "type": 2,
                "style": 2
            }
        ],
        "maskBase64": "",
        "properties": {
            "finalPrompt": "cat --v 6.1",
            "finalZhPrompt": ""
        }
    }


class TestMidjourneyService:
    """测试MidjourneyService"""

    @pytest.mark.asyncio
    async def test_submit_imagine_success(self, mock_submit_response):
        """测试成功提交imagine任务"""
        service = MidjourneyService(
            api_key="test_key",
            base_url="https://api.example.com"
        )

        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_submit_response

        with patch.object(service.client, 'post',
                         new_callable=AsyncMock, return_value=mock_response):

            task_id = await service.submit_imagine(prompt="cat")

            assert task_id == "1730621718151844"
            service.client.post.assert_called_once()

        await service.close()

    @pytest.mark.asyncio
    async def test_submit_imagine_with_base64(self, mock_submit_response):
        """测试带垫图的提交"""
        service = MidjourneyService(
            api_key="test_key",
            base_url="https://api.example.com"
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_submit_response

        with patch.object(service.client, 'post',
                         new_callable=AsyncMock, return_value=mock_response):

            base64_array = ["iVBORw0KGgoAAAANS..."]
            task_id = await service.submit_imagine(
                prompt="cat",
                base64_array=base64_array
            )

            assert task_id == "1730621718151844"

            # Verify the payload includes base64Array
            call_args = service.client.post.call_args
            payload = call_args.kwargs.get('json')
            assert 'base64Array' in payload
            assert payload['base64Array'] == base64_array

        await service.close()

    @pytest.mark.asyncio
    async def test_fetch_task_success(self, mock_task_response_success):
        """测试获取任务状态成功"""
        service = MidjourneyService(
            api_key="test_key",
            base_url="https://api.example.com"
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_task_response_success

        with patch.object(service.client, 'get',
                         new_callable=AsyncMock, return_value=mock_response):

            result = await service.fetch_task("1730621826053455")

            assert result['status'] == 'SUCCESS'
            assert result['progress'] == '100%'
            assert result['imageUrl'] == 'https://example.com/cat.png'

        await service.close()

    @pytest.mark.asyncio
    async def test_wait_for_completion_success(
        self,
        mock_task_response_in_progress,
        mock_task_response_success
    ):
        """测试等待任务完成"""
        service = MidjourneyService(
            api_key="test_key",
            base_url="https://api.example.com",
            poll_interval=0.1,
            max_poll_attempts=10
        )

        # First call returns in progress, second call returns success
        mock_response_1 = MagicMock()
        mock_response_1.status_code = 200
        mock_response_1.json.return_value = mock_task_response_in_progress

        mock_response_2 = MagicMock()
        mock_response_2.status_code = 200
        mock_response_2.json.return_value = mock_task_response_success

        with patch.object(service.client, 'get',
                         new_callable=AsyncMock,
                         side_effect=[mock_response_1, mock_response_2]):

            result = await service.wait_for_completion("1730621826053455")

            assert result['status'] == 'SUCCESS'
            assert result['imageUrl'] == 'https://example.com/cat.png'

        await service.close()

    @pytest.mark.asyncio
    async def test_wait_for_completion_timeout(
        self,
        mock_task_response_in_progress
    ):
        """测试等待超时"""
        service = MidjourneyService(
            api_key="test_key",
            base_url="https://api.example.com",
            poll_interval=0.05,
            max_poll_attempts=3
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_task_response_in_progress

        with patch.object(service.client, 'get',
                         new_callable=AsyncMock, return_value=mock_response):

            with pytest.raises(TimeoutError):
                await service.wait_for_completion("1730621826053455")

        await service.close()

    @pytest.mark.asyncio
    async def test_wait_for_completion_failure(self):
        """测试任务失败"""
        service = MidjourneyService(
            api_key="test_key",
            base_url="https://api.example.com"
        )

        mock_failed_response = {
            "id": "12345",
            "status": "FAILURE",
            "failReason": "Invalid prompt",
            "progress": "0%"
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_failed_response

        with patch.object(service.client, 'get',
                         new_callable=AsyncMock, return_value=mock_response):

            with pytest.raises(ValueError) as excinfo:
                await service.wait_for_completion("12345")

            assert "Invalid prompt" in str(excinfo.value)

        await service.close()

    @pytest.mark.asyncio
    async def test_generate_image_success(
        self,
        mock_submit_response,
        mock_task_response_success
    ):
        """测试完整的图片生成流程"""
        service = MidjourneyService(
            api_key="test_key",
            base_url="https://api.example.com",
            poll_interval=0.1
        )

        # Mock submit_imagine
        with patch.object(service, 'submit_imagine',
                         new_callable=AsyncMock,
                         return_value="1730621826053455"):
            # Mock wait_for_completion
            with patch.object(service, 'wait_for_completion',
                            new_callable=AsyncMock,
                            return_value=mock_task_response_success):

                result = await service.generate_image(prompt="cat")

                assert result['task_id'] == "1730621826053455"
                assert result['image_url'] == 'https://example.com/cat.png'
                assert result['status'] == 'SUCCESS'

        await service.close()

    @pytest.mark.asyncio
    async def test_download_image(self, tmp_path):
        """测试下载图片"""
        service = MidjourneyService(
            api_key="test_key",
            base_url="https://api.example.com"
        )

        mock_image_data = b"fake image data"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = mock_image_data

        save_path = tmp_path / "test_image.png"

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result_path = await service.download_image(
                "https://example.com/cat.png",
                save_path
            )

            assert result_path.exists()
            assert result_path.read_bytes() == mock_image_data

        await service.close()

    @pytest.mark.asyncio
    async def test_generate_and_save(
        self,
        mock_task_response_success,
        tmp_path
    ):
        """测试生成并保存图片"""
        service = MidjourneyService(
            api_key="test_key",
            base_url="https://api.example.com"
        )

        save_path = tmp_path / "cat.png"
        mock_image_data = b"fake image data"

        # Mock generate_image
        with patch.object(service, 'generate_image',
                         new_callable=AsyncMock,
                         return_value={
                             'task_id': '12345',
                             'image_url': 'https://example.com/cat.png',
                             'status': 'SUCCESS'
                         }):
            # Mock download_image
            with patch.object(service, 'download_image',
                            new_callable=AsyncMock,
                            return_value=save_path):

                # Create a fake file for testing
                save_path.parent.mkdir(parents=True, exist_ok=True)
                save_path.write_bytes(mock_image_data)

                result = await service.generate_and_save(
                    prompt="cat",
                    save_path=save_path
                )

                assert result['image_path'] == str(save_path)
                assert result['prompt'] == 'cat'
                assert result['task_id'] == '12345'

        await service.close()

    @pytest.mark.asyncio
    async def test_bot_type_configuration(self):
        """测试bot类型配置"""
        service = MidjourneyService(
            api_key="test_key",
            base_url="https://api.example.com",
            bot_type="NIJI_JOURNEY"
        )

        assert service.bot_type == "NIJI_JOURNEY"

        await service.close()

    @pytest.mark.asyncio
    async def test_progress_callback(self, mock_task_response_success):
        """测试进度回调"""
        service = MidjourneyService(
            api_key="test_key",
            base_url="https://api.example.com",
            poll_interval=0.1
        )

        progress_updates = []

        def progress_callback(progress: str, status: str):
            progress_updates.append((progress, status))

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_task_response_success

        with patch.object(service.client, 'get',
                         new_callable=AsyncMock, return_value=mock_response):

            await service.wait_for_completion(
                "1730621826053455",
                progress_callback=progress_callback
            )

            assert len(progress_updates) > 0
            assert progress_updates[-1] == ("100%", "SUCCESS")

        await service.close()


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
