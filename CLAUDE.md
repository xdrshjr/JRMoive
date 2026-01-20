# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI短剧自动化生成系统 (AI Drama Automation System) - A multi-agent architecture system that generates complete short drama videos from text scripts. The system provides **dual interfaces**:

1. **CLI Interface**: Direct command-line access for project management and video generation
2. **Web Interface**: FastAPI backend + Next.js frontend for browser-based workflows

Both interfaces share the same core video generation pipeline, which integrates Nano Banana Pro (image generation), Veo3/Sora2 (video generation with runtime selection), and optional LLM services for character consistency judging.

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

### CLI Interface

**CLI Commands**:
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
python cli.py generate projects/my_drama --resume  # Resume from checkpoint
python cli.py generate projects/my_drama --skip-characters  # Skip character reference generation
```

### Web Interface (Backend + Frontend)

**Backend (FastAPI)**:
```bash
# Run development server
cd backend
python run_dev.py

# Server will start at http://localhost:8000
# API docs: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

**Frontend (Next.js)**:
```bash
# Install dependencies
cd frontend
npm install

# Run development server
npm run dev
# Starts at http://localhost:3000

# Build for production
npm run build
npm start

# Type check
npm run type-check
```

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

### Dual Interface Architecture

The system operates with two distinct entry points that share the same core generation pipeline:

**CLI Path**: `cli.py` → `ProjectManager` → `ProjectRunner` → Agents
**Web Path**: Frontend → `FastAPI` → `WorkflowService` → `ProjectRunner` → Agents

Both paths converge at the agent layer, ensuring consistent video generation logic.

### Backend API Architecture (FastAPI)

**API Router Structure** (`backend/api/router.py`):
- **REST API v1** (`/api/v1/*`):
  - `/llm/*` - LLM services (script polishing, judging)
  - `/images/*` - Image generation endpoints
  - `/videos/*` - Video generation endpoints
  - `/tasks/*` - Async task management
  - `/workflow/*` - Complete workflow orchestration
  - `/projects/*` - Project CRUD operations

- **OpenAI-Compatible API** (`/v1/*`):
  - `/chat/completions` - Chat completion endpoint
  - `/images/generations` - Image generation endpoint
  - `/videos/generations` - Video generation endpoint

**Key Backend Services**:
1. **TaskManager** (`backend/core/task_manager.py`):
   - Async task submission and tracking
   - In-memory task storage with automatic cleanup
   - Status callback system for project synchronization
   - Semaphore-based concurrency control

2. **WorkflowService** (`backend/core/workflow_service.py`):
   - Bridges FastAPI and CLI-based generation logic
   - Creates temporary project structures for web-based workflows
   - Manages asset URL generation and storage
   - Progress callback translation

3. **ProjectManager** (`backend/core/project_manager.py`):
   - Project persistence and metadata management
   - Task-to-project synchronization
   - Status tracking and result aggregation

**Middleware**:
- CORS middleware for frontend communication
- Custom logging middleware
- Exception handlers for consistent error responses

### Frontend Architecture (Next.js)

**Tech Stack**:
- Next.js 14.2 (App Router)
- React 18.3
- TypeScript 5.3
- Tailwind CSS 3.4

**Key Pages**:
- `/` - Home page with project grid
- `/projects/new` - New project creation wizard
- `/projects/[projectId]` - Project detail view
- `/workflow/[projectId]` - Workflow execution page

**Component Structure**:
- Step-based workflow (Step0-Step5)
- Reusable UI components (`components/ui/*`)
- ModeSidebar for workflow type selection
- Real-time progress monitoring with LogViewer

**API Integration** (`lib/api.ts`):
- Centralized API client with fetch wrappers
- Type-safe request/response handling
- Error boundary integration

### Multi-Agent Video Generation Pipeline

The core video generation pipeline uses specialized agents that collaborate:

1. **DramaGenerationOrchestrator** (`agents/orchestrator_agent.py`) - Main coordinator that orchestrates the entire workflow
2. **ScriptParserAgent** (`agents/script_parser_agent.py`) - Parses text scripts into structured Scene objects
3. **ImageGenerationAgent** (`agents/image_generator_agent.py`) - Generates storyboard images using Nano Banana Pro API
4. **VideoGenerationAgent** (`agents/video_generator_agent.py`) - Converts images to video clips using Veo3 or Sora2 API (runtime selectable via VideoServiceFactory)
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

**Sora2 Service** (`services/sora2_service.py`):
- Async video generation API client (OpenAI format)
- Supports multiple resolutions and styles
- Character consistency via character_url parameter
- Storyboard mode for multi-shot videos
- Retry logic via `@async_retry` decorator

**Video Service Factory** (`services/video_service_factory.py`):
- Factory pattern for creating video services
- Runtime service selection based on config
- Config override support for custom parameters

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

### Character Consistency Judging

**LLM-Based Quality Scoring** (see `docs/CHARACTER_CONSISTENCY_JUDGING.md`):
- Generate N candidate images per scene (configurable: 1-5, recommended: 3-5)
- Use Judge LLM (e.g., Doubao multimodal) to score each candidate against character reference images
- Automatically select highest-scoring candidate for video generation
- Optionally save/delete non-selected candidates

**Configuration**:
```bash
# .env
ENABLE_CHARACTER_CONSISTENCY_JUDGE=true
CANDIDATE_IMAGES_PER_SCENE=3
JUDGE_LLM_API_KEY=your_judge_api_key
JUDGE_LLM_MODEL=doubao-seed-1-6-251015
JUDGE_TEMPERATURE=0.3
```

**Judge LLM API Requirements**:
- Must support multimodal input (image + text)
- Currently supports 火山引擎方舟 API (Volcano Engine Ark)
- API format: Responses API with `input_image` and `input_text` content types

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
- **Veo3**: Async task submission + polling for video generation status (default service)
- **Sora2**: Async task submission + polling for video generation status (alternative service, OpenAI format)
- All services implement retry logic for transient failures

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

**Enhanced Error Handling (2025-01)**:
- API services (Nano Banana Pro, Veo3, Sora2) capture complete error responses
- `ServiceException` includes: error_code, error_type, stage, api_response, retryable flag
- Task manager preserves full error context including traceback and service details
- Frontend displays detailed error information with expandable details section
- Errors show: service name, stage, error type, API error code, retryability, full API response
- Backend exceptions are properly propagated through task manager to frontend
- Custom exception classes in `backend/core/exceptions.py`:
  - `TaskNotFoundException` - Task ID not found
  - `TaskCancelledException` - Task was cancelled
  - `StorageException` - Storage operation failed
  - `ServiceException` - External service error (contains full API response)

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
- Backend config loaded via `backend/config.py` using Pydantic settings
- Frontend uses environment variables via Next.js `.env.local`

### Backend Development Notes

**Path Management**:
- Backend adds parent directory to `sys.path` to import CLI modules
- Temporary projects stored in `backend/temp_projects/workflow_*`
- Permanent projects stored in `backend/projects/`
- Assets managed via `AssetManager` (`backend/utils/asset_manager.py`)

**Task Lifecycle**:
1. Frontend submits workflow request to `/api/v1/workflow/execute`
2. WorkflowService creates temp project and invokes ProjectRunner
3. TaskManager tracks progress via status callbacks
4. ProjectManager syncs task status back to project metadata
5. Frontend polls `/api/v1/tasks/{task_id}` for progress updates

**Async Patterns**:
- All service methods are `async def`
- Use `asyncio.gather()` for parallel operations
- Use `asyncio.Semaphore` for rate limiting
- TaskManager provides callback registration for status updates

**Logging**:
- Structured logging via `loguru` in CLI
- Custom logger setup in `backend/utils/logger.py`
- Request/response logging via middleware
- Log helpers in `backend/utils/log_helpers.py` truncate sensitive data (base64 images)

### Frontend Development Notes

**State Management**:
- No Redux/Zustand - uses React state and URL params
- Project state stored in backend, fetched on page load
- Real-time progress via polling (not WebSockets)

**Routing**:
- App Router (Next.js 14+) with TypeScript
- Dynamic routes: `[projectId]` for project-specific pages
- Server components for static content, client components for interactivity

**API Calls**:
- Centralized in `lib/api.ts`
- Type definitions in `lib/types.ts` and `lib/types/*.ts`
- Error handling with try-catch and user-friendly messages

**Styling**:
- Tailwind CSS with custom Apple-inspired design
- Component library in `components/ui/*`
- Responsive design with mobile-first approach

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

### Required System Dependencies
- **Python 3.9+**
- **Node.js 18.0+** and **npm 9.0+** (for frontend)
- **FFmpeg 4.0+** - Must be installed separately and available in PATH

### Python Packages (requirements.txt)
- `pydantic` 2.5.0 - Data validation
- `httpx` 0.25.2 - HTTP client for API calls
- `aiohttp` 3.9.1 - Async HTTP operations
- `moviepy` >=2.0.0 - Video editing
- `loguru` 0.7.2 - Advanced logging
- `pytest` 7.4.3 + `pytest-asyncio` 0.21.1 - Testing
- `fastapi` + `uvicorn` - Web API framework (backend)

### Frontend Packages (frontend/package.json)
- `next` 14.2.0 - React framework
- `react` 18.3.0 + `react-dom` - UI library
- `typescript` 5.3.0 - Type safety
- `tailwindcss` 3.4.1 - Styling framework
- `js-yaml` 4.1.0 - YAML parsing

### External API Services
- **Nano Banana Pro** - Image generation (requires API key in `NANO_BANANA_API_KEY`)
- **Veo3** - Video generation (default, requires API key in `VEO3_API_KEY`)
- **Sora2** - Video generation (alternative, requires API key in `SORA2_API_KEY`)
  - OpenAI format API
  - Supports styles: anime, comic, nostalgic, thanksgiving, news, selfie
  - Supports character consistency via character_url
  - Duration constraints: 4, 8, 12 seconds (basic mode); 10, 15, 25 seconds (storyboard mode)
  - Service selection via `VIDEO_SERVICE_TYPE` env var or project config
- **Doubao / 火山引擎方舟** - Optional LLM services:
  - Script polishing (`DOUBAO_API_KEY`)
  - Character consistency judging (`JUDGE_LLM_API_KEY`)
- **Midjourney** - Optional alternative image service (see `docs/midjourney_integration.md`)

## File Structure Highlights

```
ai-movie-agent-guide/
├── cli.py                      # CLI entry point
├── init_project.py             # Project initialization script
├── requirements.txt            # Python dependencies
│
├── agents/                     # Core agent implementations
│   ├── base_agent.py           # BaseAgent + MessageBus + WorkflowStateManager + ErrorHandler
│   ├── orchestrator_agent.py   # Main coordinator with SimpleDramaGenerator
│   ├── script_parser_agent.py
│   ├── image_generator_agent.py
│   ├── video_generator_agent.py
│   └── video_composer_agent.py
│
├── backend/                    # FastAPI web backend
│   ├── main.py                 # FastAPI app initialization
│   ├── run_dev.py              # Development server runner
│   ├── config.py               # Pydantic settings
│   │
│   ├── api/                    # API routes
│   │   ├── router.py           # Main router combining v1 and OpenAI APIs
│   │   ├── v1/                 # REST API v1
│   │   │   ├── llm.py
│   │   │   ├── images.py
│   │   │   ├── videos.py
│   │   │   ├── tasks.py
│   │   │   └── workflow.py
│   │   ├── openai/             # OpenAI-compatible endpoints
│   │   │   ├── chat.py
│   │   │   ├── images.py
│   │   │   └── videos.py
│   │   └── routes/
│   │       └── projects.py     # Project CRUD
│   │
│   ├── core/                   # Core backend services
│   │   ├── task_manager.py     # Async task execution and tracking
│   │   ├── workflow_service.py # Bridges FastAPI and CLI generation
│   │   ├── project_manager.py  # Project persistence
│   │   ├── models.py           # Pydantic models for API
│   │   └── exceptions.py       # Custom exception classes
│   │
│   ├── middleware/             # FastAPI middleware
│   │   ├── logging.py
│   │   └── error_handler.py
│   │
│   └── utils/                  # Backend utilities
│       ├── logger.py
│       ├── asset_manager.py
│       └── log_helpers.py
│
├── frontend/                   # Next.js web frontend
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   │
│   └── src/
│       ├── app/                # App Router pages
│       │   ├── page.tsx        # Home page
│       │   ├── layout.tsx      # Root layout
│       │   ├── projects/
│       │   │   ├── new/page.tsx
│       │   │   └── [projectId]/page.tsx
│       │   └── workflow/
│       │       └── [projectId]/page.tsx
│       │
│       ├── components/         # React components
│       │   ├── steps/          # Step-based workflow components
│       │   └── ui/             # Reusable UI components
│       │
│       └── lib/                # Utilities and types
│           ├── api.ts          # API client
│           ├── types.ts        # TypeScript type definitions
│           └── types/          # Additional type definitions
│
├── models/                     # Data models
│   ├── script_models.py        # Script, Scene, Character, Dialogue models
│   └── config_models.py        # Configuration models
│
├── services/                   # External API wrappers
│   ├── nano_banana_service.py
│   ├── veo3_service.py
│   ├── sora2_service.py
│   ├── video_service_factory.py
│   └── doubao_service.py
│
├── utils/                      # Shared utilities (CLI)
│   ├── retry.py                # @async_retry decorator
│   ├── concurrency.py          # ConcurrencyLimiter, RateLimiter, ResultCache
│   ├── checkpoint.py           # CheckpointManager
│   ├── progress_monitor.py     # Progress tracking
│   ├── task_queue.py           # Async task queue
│   └── video_utils.py          # FFmpeg wrapper
│
├── config/                     # Configuration (CLI)
│   └── settings.py             # Pydantic settings (loads from .env)
│
├── core/                       # Core modules (CLI)
│   ├── project_manager.py      # CLI project manager
│   ├── config_loader.py        # YAML config loader
│   ├── runner.py               # Project execution runner
│   ├── validators.py           # Validation logic
│   └── errors.py               # Error definitions
│
├── projects/                   # User projects (CLI)
│   └── [project_name]/
│       ├── config.yaml
│       ├── script.txt
│       ├── characters/
│       └── outputs/
│
├── examples/                   # Example code
│   ├── complete_workflow_example.py
│   └── sample_scripts/
│
├── tests/                      # Test suite
│   ├── test_agents/
│   ├── test_services/
│   ├── test_integration/
│   └── test_performance/
│
└── docs/                       # Documentation
    ├── CHARACTER_CONSISTENCY_JUDGING.md
    ├── MIDJOURNEY_INTEGRATION_STATUS.md
    └── ...
```
