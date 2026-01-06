"""
Integration tests for the complete AI Drama Generation workflow
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import shutil

from agents.orchestrator_agent import DramaGenerationOrchestrator, SimpleDramaGenerator
from agents.script_parser_agent import ScriptParserAgent
from models.script_models import Script


# Test fixtures
@pytest.fixture
def test_script():
    """Sample test script"""
    return """
# 测试短剧

## 角色
- 小明: 程序员
- 小红: 设计师

## 场景1：办公室
地点: 办公室
时间: 白天
描述: 小明在写代码
时长: 3.0

小明（专注）：这个bug终于修好了！

## 场景2：咖啡馆
地点: 咖啡馆
时间: 下午
描述: 小明和小红在讨论项目
时长: 3.5

小红（微笑）：你的代码写得真好！
小明（谦虚）：还有很多可以改进的地方。
    """


@pytest.fixture
def test_config():
    """Test configuration with low quality settings"""
    return {
        'image': {
            'max_concurrent': 2,
            'width': 512,
            'height': 288,
            'quality': 'low'
        },
        'video': {
            'max_concurrent': 1,
            'fps': 24,
            'resolution': '1280x720'
        },
        'composer': {
            'add_transitions': False,
            'fps': 24,
            'preset': 'ultrafast',
            'threads': 2
        }
    }


@pytest.fixture
def temp_output_dir():
    """Temporary output directory"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


class TestScriptParserIntegration:
    """Integration tests for script parser"""

    @pytest.mark.asyncio
    async def test_parse_complete_script(self, test_script):
        """Test parsing a complete script"""
        parser = ScriptParserAgent()
        script = await parser.execute(test_script)

        assert isinstance(script, Script)
        assert script.title == "测试短剧"
        assert len(script.characters) == 2
        assert len(script.scenes) == 2
        assert script.total_scenes == 2
        assert script.total_duration > 0

    @pytest.mark.asyncio
    async def test_scene_details(self, test_script):
        """Test scene details are correctly parsed"""
        parser = ScriptParserAgent()
        script = await parser.execute(test_script)

        scene1 = script.scenes[0]
        assert scene1.location == "办公室"
        assert scene1.time == "白天"
        assert scene1.duration == 3.0
        assert len(scene1.dialogues) >= 1

        scene2 = script.scenes[1]
        assert scene2.location == "咖啡馆"
        assert len(scene2.dialogues) >= 2

    @pytest.mark.asyncio
    async def test_prompt_generation(self, test_script):
        """Test that scenes can generate image prompts"""
        parser = ScriptParserAgent()
        script = await parser.execute(test_script)

        for scene in script.scenes:
            prompt = scene.to_image_prompt()
            assert isinstance(prompt, str)
            assert len(prompt) > 0
            assert scene.location in prompt or scene.description in prompt


class TestWorkflowIntegration:
    """Integration tests for the complete workflow"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.skipif(
        not Path('.env').exists(),
        reason="Requires API keys in .env file"
    )
    async def test_minimal_workflow(self, test_script, test_config, temp_output_dir):
        """Test minimal complete workflow (requires real API keys)"""
        # This test requires actual API keys and will make real API calls
        # Skip in CI/CD unless API keys are provided

        orchestrator = DramaGenerationOrchestrator(config=test_config)

        try:
            output_file = temp_output_dir / "test_output.mp4"

            video_path = await orchestrator.execute(
                script_text=test_script,
                output_filename=str(output_file)
            )

            # Verify output
            assert Path(video_path).exists()
            assert Path(video_path).stat().st_size > 0

        finally:
            await orchestrator.close()

    @pytest.mark.asyncio
    async def test_simple_generator_interface(self, test_script, temp_output_dir):
        """Test SimpleDramaGenerator interface"""
        # This is a lighter test that doesn't require API keys
        # It tests the interface but with mocked services

        with patch('agents.orchestrator_agent.DramaGenerationOrchestrator.execute') as mock_execute:
            mock_execute.return_value = str(temp_output_dir / "test.mp4")

            generator = SimpleDramaGenerator()
            video_path = await generator.generate(
                script_text=test_script,
                output_file="test.mp4"
            )

            assert mock_execute.called
            assert isinstance(video_path, str)

            await generator.close()


class TestCheckpointIntegration:
    """Integration tests for checkpoint functionality"""

    @pytest.mark.asyncio
    async def test_checkpoint_save_and_load(self, temp_output_dir):
        """Test checkpoint save and load"""
        from utils.checkpoint import CheckpointManager

        checkpoint_dir = temp_output_dir / "checkpoints"
        manager = CheckpointManager(checkpoint_dir)

        task_id = "test_task"
        stage = "parsing"
        data = {
            "test_data": "value",
            "scenes": 5,
            "duration": 30.0
        }

        # Save checkpoint
        checkpoint_file = manager.save_checkpoint(task_id, stage, data)
        assert checkpoint_file.exists()

        # Load checkpoint
        loaded = manager.load_checkpoint(task_id, stage)
        assert loaded is not None
        assert loaded['task_id'] == task_id
        assert loaded['stage'] == stage
        assert loaded['data'] == data

    @pytest.mark.asyncio
    async def test_checkpoint_resume_logic(self, temp_output_dir):
        """Test checkpoint resume stage logic"""
        from utils.checkpoint import CheckpointManager

        checkpoint_dir = temp_output_dir / "checkpoints"
        manager = CheckpointManager(checkpoint_dir)

        task_id = "resume_test"

        # Simulate workflow stages
        manager.save_checkpoint(task_id, "parsing", {"data": 1})
        assert manager.get_resume_stage(task_id) == "image_generation"

        manager.save_checkpoint(task_id, "image_generation", {"data": 2})
        assert manager.get_resume_stage(task_id) == "video_generation"

        manager.save_checkpoint(task_id, "video_generation", {"data": 3})
        assert manager.get_resume_stage(task_id) == "composition"


class TestProgressMonitoringIntegration:
    """Integration tests for progress monitoring"""

    @pytest.mark.asyncio
    async def test_progress_callback_integration(self, test_script, test_config):
        """Test progress callback integration"""
        progress_updates = []

        async def test_callback(percent, message):
            progress_updates.append({'percent': percent, 'message': message})

        with patch('agents.script_parser_agent.ScriptParserAgent.execute') as mock_parser:
            with patch('agents.image_generator_agent.ImageGenerationAgent.execute_concurrent') as mock_image:
                with patch('agents.video_generator_agent.VideoGenerationAgent.execute') as mock_video:
                    with patch('agents.video_composer_agent.VideoComposerAgent.execute') as mock_composer:
                        # Mock returns
                        from models.script_models import Script, Scene
                        mock_script = Script(
                            title="Test",
                            scenes=[Scene(scene_id="1", location="test", time="day", description="test", duration=3.0)]
                        )
                        mock_parser.return_value = mock_script
                        mock_image.return_value = [{'scene_id': '1', 'image_path': '/test/path.png'}]
                        mock_video.return_value = [{'scene_id': '1', 'video_path': '/test/video.mp4'}]
                        mock_composer.return_value = "/test/final.mp4"

                        orchestrator = DramaGenerationOrchestrator(config=test_config)

                        try:
                            await orchestrator.execute(
                                script_text=test_script,
                                output_filename="test.mp4",
                                progress_callback=test_callback
                            )

                            # Verify progress updates were made
                            assert len(progress_updates) > 0
                            # First update should be 0%
                            assert progress_updates[0]['percent'] == 0
                            # Last update should be 100%
                            assert progress_updates[-1]['percent'] == 100

                        finally:
                            await orchestrator.close()


class TestErrorHandlingIntegration:
    """Integration tests for error handling"""

    @pytest.mark.asyncio
    async def test_invalid_script_handling(self):
        """Test handling of invalid script"""
        parser = ScriptParserAgent()

        with pytest.raises(ValueError):
            await parser.execute("")

        with pytest.raises(ValueError):
            await parser.execute("invalid script format")

    @pytest.mark.asyncio
    async def test_api_error_propagation(self, test_script, test_config):
        """Test that API errors are properly propagated"""
        with patch('services.nano_banana_service.NanoBananaService.generate_image') as mock_api:
            mock_api.side_effect = Exception("API Error")

            orchestrator = DramaGenerationOrchestrator(config=test_config)

            try:
                with pytest.raises(Exception):
                    await orchestrator.execute(
                        script_text=test_script,
                        output_filename="test.mp4"
                    )
            finally:
                await orchestrator.close()


class TestResourceCleanup:
    """Integration tests for resource cleanup"""

    @pytest.mark.asyncio
    async def test_orchestrator_cleanup(self, test_config):
        """Test that orchestrator properly cleans up resources"""
        orchestrator = DramaGenerationOrchestrator(config=test_config)

        # Verify agents are initialized
        assert orchestrator.script_parser is not None
        assert orchestrator.image_generator is not None
        assert orchestrator.video_generator is not None
        assert orchestrator.video_composer is not None

        # Close should not raise errors
        await orchestrator.close()

    @pytest.mark.asyncio
    async def test_context_manager_usage(self):
        """Test using agents as context managers"""
        from services.nano_banana_service import NanoBananaService

        # This should work even without real API key for testing cleanup
        with patch.dict('os.environ', {'NANO_BANANA_API_KEY': 'test_key'}):
            async with NanoBananaService() as service:
                assert service is not None

            # Service should be closed after context exit


# Performance and load tests
class TestPerformanceIntegration:
    """Integration tests for performance characteristics"""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_scene_processing(self):
        """Test that concurrent processing actually improves performance"""
        from agents.image_generator_agent import ImageGenerationAgent
        from models.script_models import Scene
        import time

        # Create test scenes
        scenes = [
            Scene(
                scene_id=f"perf_test_{i}",
                location="test",
                time="day",
                description=f"Test scene {i}",
                duration=3.0
            )
            for i in range(5)
        ]

        # Mock the service to simulate processing time
        async def mock_generate(*args, **kwargs):
            await asyncio.sleep(0.5)  # Simulate API call
            return {'image_url': 'http://test.com/image.png'}

        with patch('services.nano_banana_service.NanoBananaService.generate_image', side_effect=mock_generate):
            agent = ImageGenerationAgent(config={'max_concurrent': 3})

            start_time = time.time()
            results = await agent.execute_concurrent(scenes)
            concurrent_time = time.time() - start_time

            # With 5 scenes, 0.5s each, and max_concurrent=3:
            # Sequential would take ~2.5s
            # Concurrent should take ~1.0s (2 batches: 3 + 2)
            assert concurrent_time < 2.0  # Should be faster than sequential
            assert len(results) == 5


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
