"""
Performance benchmarks for AI Drama Generation System
"""

import pytest
import asyncio
import time
from typing import List, Dict, Any
from pathlib import Path
import statistics

from agents.image_generator_agent import ImageGenerationAgent
from agents.video_generator_agent import VideoGenerationAgent
from agents.orchestrator_agent import DramaGenerationOrchestrator
from models.script_models import Scene
from unittest.mock import patch, AsyncMock


class BenchmarkResult:
    """Benchmark result data class"""

    def __init__(self, name: str):
        self.name = name
        self.timings = []
        self.success_count = 0
        self.failure_count = 0

    def add_timing(self, duration: float, success: bool = True):
        """Add a timing measurement"""
        self.timings.append(duration)
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get statistical summary"""
        if not self.timings:
            return {}

        return {
            'name': self.name,
            'count': len(self.timings),
            'total_time': sum(self.timings),
            'mean': statistics.mean(self.timings),
            'median': statistics.median(self.timings),
            'min': min(self.timings),
            'max': max(self.timings),
            'stdev': statistics.stdev(self.timings) if len(self.timings) > 1 else 0,
            'success_rate': self.success_count / len(self.timings) * 100 if self.timings else 0
        }

    def print_stats(self):
        """Print benchmark statistics"""
        stats = self.get_stats()
        print(f"\n{'='*60}")
        print(f"Benchmark: {stats['name']}")
        print(f"{'='*60}")
        print(f"  Executions: {stats['count']}")
        print(f"  Total Time: {stats['total_time']:.2f}s")
        print(f"  Mean Time: {stats['mean']:.3f}s")
        print(f"  Median Time: {stats['median']:.3f}s")
        print(f"  Min Time: {stats['min']:.3f}s")
        print(f"  Max Time: {stats['max']:.3f}s")
        print(f"  Std Dev: {stats['stdev']:.3f}s")
        print(f"  Success Rate: {stats['success_rate']:.1f}%")
        print(f"{'='*60}")


@pytest.fixture
def mock_scenes() -> List[Scene]:
    """Create mock scenes for testing"""
    return [
        Scene(
            scene_id=f"bench_{i}",
            location=f"location_{i}",
            time="day",
            description=f"Benchmark scene {i}",
            duration=3.0
        )
        for i in range(10)
    ]


class TestScriptParserBenchmarks:
    """Benchmarks for script parser"""

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_parser_performance(self):
        """Benchmark script parsing performance"""
        from agents.script_parser_agent import ScriptParserAgent

        script_text = """
# 性能测试剧本

## 角色
- 角色1: 描述1
- 角色2: 描述2
- 角色3: 描述3

## 场景1：测试场景1
地点: 地点1
时间: 白天
描述: 测试描述1
时长: 3.0

角色1：对话内容1

## 场景2：测试场景2
地点: 地点2
时间: 晚上
描述: 测试描述2
时长: 3.5

角色2：对话内容2
角色3：对话内容3
        """

        parser = ScriptParserAgent()
        result = BenchmarkResult("Script Parser")

        # Run multiple iterations
        for _ in range(10):
            start = time.time()
            try:
                await parser.execute(script_text)
                elapsed = time.time() - start
                result.add_timing(elapsed, success=True)
            except Exception as e:
                elapsed = time.time() - start
                result.add_timing(elapsed, success=False)
                print(f"Error: {e}")

        result.print_stats()

        # Performance assertion
        stats = result.get_stats()
        assert stats['mean'] < 1.0, "Parsing should complete in under 1 second"
        assert stats['success_rate'] == 100.0


class TestConcurrencyBenchmarks:
    """Benchmarks for concurrent processing"""

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_concurrent_vs_sequential(self, mock_scenes):
        """Compare concurrent vs sequential processing"""

        async def mock_process_scene(scene: Scene):
            """Mock scene processing with delay"""
            await asyncio.sleep(0.2)  # Simulate API call
            return {'scene_id': scene.scene_id, 'status': 'completed'}

        # Sequential processing
        seq_result = BenchmarkResult("Sequential Processing")
        start = time.time()
        for scene in mock_scenes:
            await mock_process_scene(scene)
        seq_time = time.time() - start
        seq_result.add_timing(seq_time)

        # Concurrent processing
        conc_result = BenchmarkResult("Concurrent Processing (max=5)")
        start = time.time()
        from utils.concurrency import ConcurrencyLimiter
        limiter = ConcurrencyLimiter(max_concurrent=5)
        await limiter.run_batch(mock_process_scene, mock_scenes)
        conc_time = time.time() - start
        conc_result.add_timing(conc_time)

        # Print results
        seq_result.print_stats()
        conc_result.print_stats()

        # Concurrent should be significantly faster
        speedup = seq_time / conc_time
        print(f"\nSpeedup: {speedup:.2f}x")
        assert speedup > 2.0, "Concurrent processing should be at least 2x faster"


class TestMemoryBenchmarks:
    """Benchmarks for memory usage"""

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_memory_usage_during_generation(self, mock_scenes):
        """Monitor memory usage during processing"""
        import psutil
        import os

        process = psutil.Process(os.getpid())

        # Get initial memory
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Simulate heavy processing
        async def mock_heavy_process(scene: Scene):
            # Simulate some memory allocation
            data = [0] * 100000  # Allocate some memory
            await asyncio.sleep(0.1)
            return {'scene_id': scene.scene_id, 'data': len(data)}

        from utils.concurrency import ConcurrencyLimiter
        limiter = ConcurrencyLimiter(max_concurrent=3)

        results = await limiter.run_batch(mock_heavy_process, mock_scenes)

        # Get final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        print(f"\nMemory Usage:")
        print(f"  Initial: {initial_memory:.2f} MB")
        print(f"  Final: {final_memory:.2f} MB")
        print(f"  Increase: {memory_increase:.2f} MB")

        # Memory increase should be reasonable
        assert memory_increase < 500, "Memory increase should be less than 500MB"


class TestThroughputBenchmarks:
    """Benchmarks for throughput metrics"""

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_scene_processing_throughput(self):
        """Measure scenes processed per second"""

        async def mock_generate_image(scene: Scene):
            await asyncio.sleep(0.3)
            return {'scene_id': scene.scene_id, 'image_path': f'/test/{scene.scene_id}.png'}

        # Create many scenes
        scenes = [
            Scene(
                scene_id=f"throughput_test_{i}",
                location="test",
                time="day",
                description="test",
                duration=3.0
            )
            for i in range(20)
        ]

        result = BenchmarkResult("Throughput Test")

        from utils.concurrency import ConcurrencyLimiter
        limiter = ConcurrencyLimiter(max_concurrent=5)

        start = time.time()
        await limiter.run_batch(mock_generate_image, scenes)
        elapsed = time.time() - start

        result.add_timing(elapsed)

        throughput = len(scenes) / elapsed

        print(f"\nThroughput Metrics:")
        print(f"  Total Scenes: {len(scenes)}")
        print(f"  Total Time: {elapsed:.2f}s")
        print(f"  Throughput: {throughput:.2f} scenes/second")

        # Should process at least 2 scenes per second with concurrency=5
        assert throughput > 2.0


class TestEndToEndBenchmark:
    """End-to-end workflow benchmarks"""

    @pytest.mark.benchmark
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_complete_workflow_performance(self):
        """Benchmark complete workflow with mocked services"""

        script = """
# 性能测试完整流程

## 角色
- 测试角色: 用于性能测试

## 场景1：场景1
地点: 测试地点1
时间: 白天
描述: 性能测试场景
时长: 3.0

## 场景2：场景2
地点: 测试地点2
时间: 晚上
描述: 性能测试场景
时长: 3.0

## 场景3：场景3
地点: 测试地点3
时间: 下午
描述: 性能测试场景
时长: 3.0
        """

        # Mock all services to avoid real API calls
        with patch('services.nano_banana_service.NanoBananaService.generate_image') as mock_image:
            with patch('services.veo3_service.Veo3Service.image_to_video') as mock_video:
                with patch('agents.video_composer_agent.VideoComposerAgent.execute') as mock_composer:

                    # Setup mocks
                    async def mock_gen_image(*args, **kwargs):
                        await asyncio.sleep(0.2)
                        return {'image_url': 'http://test.com/image.png'}

                    async def mock_gen_video(*args, **kwargs):
                        await asyncio.sleep(0.3)
                        return {'video_url': 'http://test.com/video.mp4'}

                    mock_image.side_effect = mock_gen_image
                    mock_video.side_effect = mock_gen_video
                    mock_composer.return_value = "/test/final.mp4"

                    # Run benchmark
                    result = BenchmarkResult("Complete Workflow")

                    config = {
                        'image': {'max_concurrent': 3},
                        'video': {'max_concurrent': 2}
                    }

                    orchestrator = DramaGenerationOrchestrator(config=config)

                    start = time.time()
                    try:
                        video_path = await orchestrator.execute(
                            script_text=script,
                            output_filename="benchmark.mp4"
                        )
                        elapsed = time.time() - start
                        result.add_timing(elapsed, success=True)
                    except Exception as e:
                        elapsed = time.time() - start
                        result.add_timing(elapsed, success=False)
                        print(f"Error: {e}")
                    finally:
                        await orchestrator.close()

                    result.print_stats()

                    # Workflow should complete in reasonable time
                    stats = result.get_stats()
                    assert stats['mean'] < 5.0, "Complete workflow should finish in under 5 seconds (mocked)"


# Utility function to run all benchmarks
def run_all_benchmarks():
    """Run all benchmark tests"""
    pytest.main([
        __file__,
        '-v',
        '-s',
        '-m', 'benchmark',
        '--tb=short'
    ])


if __name__ == "__main__":
    run_all_benchmarks()
