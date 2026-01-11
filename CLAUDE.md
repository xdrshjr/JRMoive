# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI短剧自动化生成系统 (AI Drama Automation System) - A multi-agent architecture system that generates complete short drama videos from text scripts. The system integrates Nano Banana Pro (image generation) and Veo3 (video generation) APIs to automate the entire drama production pipeline.

## Core Commands

### Development Setup
```bash
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env to add API keys
```

### Testing
```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_agents/test_image_video_generation.py

# Run with verbose output and short traceback
python -m pytest tests/test_agents/test_image_video_generation.py -v --tb=short

# Run specific test class
python -m pytest tests/test_agents/test_image_video_generation.py::TestConcurrencyUtilities -v --tb=short

# Run async tests
python -m pytest tests/test_agents/test_script_parser.py -v
```

### Project Initialization
```bash
# Initialize project structure
python init_project.py

# Run example workflow
python examples/complete_workflow_example.py
```

### CLI Commands
```bash
# Create new project
python cli.py init my_drama

# Generate complete drama video
python cli.py generate projects/my_drama

# Validate project configuration
python cli.py validate projects/my_drama

# List all projects
python cli.py list

# Advanced options
python cli.py generate projects/my_drama --log-level DEBUG
python cli.py generate projects/my_drama --override video.fps=60
```

**generate-sence Command**:
- Generates multiple candidate images per scene (configured in `config.yaml`)
- Saves to `projects/<project>/scenes/all/` directory
- Simple naming: `scene_001_candidate_1.png`, `scene_001_candidate_2.png`
- Supports sub-scenes: `scene_001_sub_001_candidate_1.png`
- No LLM judging - all candidates saved for manual selection
- Use case: Explore visual styles, preview before full generation, reduce costs

### Code Quality
```bash
# Format code
black .

# Lint code
flake8

# Type check
mypy .
```

## System Architecture

### Multi-Agent Workflow

The system uses a **multi-agent orchestration architecture** where specialized agents collaborate to transform text scripts into video:

1. **DramaGenerationOrchestrator** (`agents/orchestrator_agent.py`) - Main coordinator that orchestrates the entire workflow
2. **ScriptParserAgent** (`agents/script_parser_agent.py`) - Parses text scripts into structured Scene objects
3. **ImageGenerationAgent** (`agents/image_generator_agent.py`) - Generates storyboard images using Nano Banana Pro API
4. **VideoGenerationAgent** (`agents/video_generator_agent.py`) - Converts images to video clips using Veo3 API
5. **VideoComposerAgent** (`agents/video_composer_agent.py`) - Composes final video with transitions, BGM, and effects

### Key Design Patterns

**BaseAgent Pattern** (`agents/base_agent.py`):
- All agents inherit from `BaseAgent` abstract class
- Required methods: `execute()`, `validate_input()`
- Built-in lifecycle hooks: `on_error()`, `on_complete()`
- State management via `AgentState` enum (IDLE, RUNNING, WAITING, COMPLETED, ERROR)

**Message Bus Communication** (`agents/base_agent.py:108-154`):
- Agents communicate via async message queue
- Message format: `AgentMessage` with sender_id, receiver_id, message_type, payload, correlation_id
- Subscribe/publish pattern for decoupled communication

**Workflow State Management** (`agents/base_agent.py:156-216`):
- State machine with valid transitions: INITIALIZED → PARSING_SCRIPT → GENERATING_IMAGES → GENERATING_VIDEOS → COMPOSING_VIDEO → POST_PROCESSING → COMPLETED
- Checkpoint support for resume capability
- Prevent invalid state transitions

**Error Handling Strategy** (`agents/base_agent.py:218-263`):
- Centralized `ErrorHandler` with registered exception handlers
- Retry configuration with exponential backoff
- Context-aware error logging

### Data Models

**Core Models** (`models/script_models.py`):
- `Script` - Top-level model containing characters and scenes
- `Scene` - Individual scene with location, time, shot_type, camera_movement, duration (1-10s)
- `Character` - Character definition with appearance details
- `Dialogue` - Dialog with character, content, emotion, voice_style

**Scene to Prompt Conversion** (`models/script_models.py:100-137`):
- `Scene.to_image_prompt()` generates AI-ready image prompts
- Combines location, time, weather, atmosphere, characters, action, shot_type, visual_style

**Shot Types & Camera Movements** (`models/script_models.py:9-27`):
- ShotType: CLOSE_UP, MEDIUM_SHOT, LONG_SHOT, EXTREME_CLOSE_UP, FULL_SHOT, OVER_SHOULDER
- CameraMovement: STATIC, PAN, TILT, ZOOM, DOLLY, TRACKING

### Service Layer

**Nano Banana Pro Service** (`services/nano_banana_service.py`):
- Async image generation API client
- Supports Base64 and file-based image storage
- Retry logic via `@async_retry` decorator

**Veo3 Service** (`services/veo3_service.py`):
- Async video generation API client
- Image upload and async task polling
- Maps camera movements to motion strength parameters

**Configuration** (`config/settings.py`):
- Uses `pydantic-settings` for environment-based config
- Auto-loads from `.env` file
- Key settings: API keys, output_dir, temp_dir, max_concurrent_requests

### Utility Infrastructure

**Async Retry** (`utils/retry.py`):
- `@async_retry` decorator for automatic retry with exponential backoff
- Configurable max_attempts, backoff_factor, exception types
- Example: `@async_retry(max_attempts=3, backoff_factor=2.0)`

**Concurrency Control** (`utils/concurrency.py`):
- `ConcurrencyLimiter` - Semaphore-based concurrent task limiting
- `RateLimiter` - Token bucket rate limiting
- `ResultCache` - In-memory result caching

**Checkpoint Management** (`utils/checkpoint.py`):
- Save/load workflow state at each stage
- Resume from last successful checkpoint on failure
- Checkpoint stages: parsing, image_generation, video_generation, composition

**Progress Monitoring** (`utils/progress_monitor.py`):
- `ProgressMonitor` - Track completion percentage and ETA
- `ConsoleProgressMonitor` - Visual progress bar display
- Callbacks for real-time progress updates

**Task Queue** (`utils/task_queue.py`):
- Async task queue with worker pool
- Task submission, result retrieval, statistics tracking
- Supports timeout and graceful shutdown

**Video Processing** (`utils/video_utils.py`):
- FFmpeg wrapper for video operations
- Video concatenation, audio mixing, format conversion
- Transition effects (fade, crossfade)

## Important Implementation Details

### Orchestrator Progress Mapping
The orchestrator divides progress into stages:
- 0-10%: Script parsing
- 10-40%: Image generation
- 40-70%: Video generation
- 70-95%: Video composition
- 95-100%: Metadata saving

Sub-progress is mapped using `_create_sub_progress_callback()` to translate child task progress to overall progress.

### Concurrent Image/Video Generation
Both image and video agents support concurrent processing with configurable limits:
- Set via `max_concurrent` in config.yaml or settings.py
- Uses `asyncio.Semaphore` for concurrency control
- Progress callbacks track individual task completion
- **Candidate Generation**: When character consistency judging is enabled, multiple candidate images are generated concurrently using `asyncio.gather()`
- **Concurrent Judging**: LLM evaluation of candidates also runs concurrently, with all judge tasks executed in parallel
- Example: With `candidate_images_per_scene: 3`, all 3 candidates are generated simultaneously, then all 3 are judged simultaneously

### Script Parsing Format
Expected script format (see `examples/sample_scripts/programmer_day.txt`):
```
标题: [Title]

场景1: [Location] - [Time]
[Shot type indication]
[Description and action]
[Character]: "[Dialogue]"
```

### API Integration Points
- **Nano Banana Pro**: Synchronous polling for image generation completion
- **Veo3**: Async task submission + polling for video generation status
- Both services implement retry logic for transient failures

### Testing Strategy
- Use `pytest.fixture` for reusable test data (e.g., `sample_scenes`)
- Use `@pytest.mark.asyncio` for async tests
- Mock external API calls with `unittest.mock.AsyncMock`
- Integration tests in `tests/test_integration/`
- Performance benchmarks in `tests/test_performance/`

## Development Guidelines

### Agent Implementation
When creating new agents:
1. Inherit from `BaseAgent`
2. Implement `execute(input_data)` - core processing logic
3. Implement `validate_input(input_data)` - input validation
4. Call `await self.on_error(e)` and `await self.on_complete(result)` appropriately
5. Update state via `self.state = AgentState.RUNNING`

### Error Handling
- Use `@async_retry` decorator for API calls
- Register custom error handlers with `ErrorHandler.register_handler()`
- Include context dict when calling `error_handler.handle_error(e, context)`
- Log errors with correlation_id for request tracing

### Resource Management
- Always call `await agent.close()` to cleanup resources
- Use `async with` context managers where possible
- Clear checkpoints after successful completion
- Clean up temp files in output/temp directories

### Configuration
- Never commit API keys - use `.env` file
- Access config via `config.settings` singleton
- Override config per-agent via constructor `config` parameter
- Use `Optional[str]` for optional API keys (e.g., openai_api_key)

## Project Status

Current development status (see 开发计划.md):
- ✅ TODO 1: Environment setup and base architecture
- ✅ TODO 2: Script parsing and data models
- ✅ TODO 3: Image and video generation modules
- ✅ TODO 4: Video composition and post-processing
- ✅ TODO 5: Testing, deployment, and documentation

Key files demonstrate working implementation:
- `examples/complete_workflow_example.py` - Full workflow examples
- `agents/orchestrator_agent.py` - Main orchestration logic
- `models/script_models.py` - Complete data model with validation

## External Dependencies

### Required
- **Python 3.9+**
- **FFmpeg 4.0+** - Must be installed separately and available in PATH

### Python Packages
- `pydantic` 2.5.0 - Data validation
- `httpx` 0.25.2 - HTTP client for API calls
- `aiohttp` 3.9.1 - Async HTTP operations
- `moviepy` 1.0.3 - Video editing
- `loguru` 0.7.2 - Advanced logging
- `pytest` 7.4.3 + `pytest-asyncio` 0.21.1 - Testing

### API Services
- **Nano Banana Pro** - Image generation (requires API key)
- **Veo3** - Video generation (requires API key)
- **OpenAI** (optional) - Script optimization

## File Structure Highlights

```
agents/               # All agent implementations
  base_agent.py       # BaseAgent + MessageBus + WorkflowStateManager + ErrorHandler
  orchestrator_agent.py  # Main coordinator with SimpleDramaGenerator
models/
  script_models.py    # Script, Scene, Character, Dialogue models
services/             # External API wrappers
  nano_banana_service.py
  veo3_service.py
utils/                # Shared utilities
  retry.py            # @async_retry decorator
  concurrency.py      # ConcurrencyLimiter, RateLimiter, ResultCache
  checkpoint.py       # CheckpointManager
  progress_monitor.py # Progress tracking
  task_queue.py       # Async task queue
config/
  settings.py         # Pydantic settings (loads from .env)
examples/
  complete_workflow_example.py  # Comprehensive usage examples
tests/
  test_agents/        # Agent unit tests
  test_integration/   # End-to-end workflow tests
  test_performance/   # Performance benchmarks
```
