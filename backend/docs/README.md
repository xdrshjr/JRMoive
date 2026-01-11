# AI Movie Agent API - Backend

Comprehensive FastAPI backend that exposes all AI generation capabilities (LLM, Image, Video) through RESTful and OpenAI-compatible API endpoints.

## Features

- 🎨 **Multiple Image Services**: Doubao, NanoBanana, Midjourney
- 🎥 **Video Generation**: Veo3 image-to-video conversion
- 🤖 **LLM Integration**: Chat completion and prompt optimization
- 📊 **Async Task Management**: Submit long-running tasks and poll for results
- 🔄 **OpenAI Compatible**: Drop-in replacement for OpenAI SDK
- 📝 **Enterprise Logging**: Structured logs with rotation
- 🚀 **Production Ready**: Error handling, validation, CORS support

## Quick Start

### 1. Installation

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configuration

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
# Edit .env with your actual API keys
```

Required configuration:
- `FAST_LLM_API_KEY`: LLM service API key
- `DOUBAO_API_KEY`: Doubao image service key
- `VEO3_API_KEY`: Veo3 video service key
- Other service keys as needed

### 3. Start Server

Development mode:
```bash
python run_dev.py
```

Or directly:
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Production mode:
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4. Access API

- **API Docs (Swagger)**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## API Endpoints Overview

### REST API (v1)

#### LLM Endpoints
- `POST /api/v1/llm/chat` - Chat completion
- `POST /api/v1/llm/optimize-prompt` - Prompt optimization

#### Image Endpoints
- `POST /api/v1/images/generate` - Generate image from text
- `POST /api/v1/images/generate-i2i` - Image-to-image generation
- `GET /api/v1/images/services` - List available services

#### Video Endpoints
- `POST /api/v1/videos/generate` - Generate video (async)
- `GET /api/v1/videos/{video_id}` - Get video status

#### Task Management
- `GET /api/v1/tasks/{task_id}` - Get task status
- `DELETE /api/v1/tasks/{task_id}` - Cancel task
- `GET /api/v1/tasks` - List all tasks

### OpenAI Compatible API

#### Chat
- `POST /v1/chat/completions` - Chat completion (OpenAI format)

#### Images
- `POST /v1/images/generations` - Generate images (OpenAI format)

#### Videos
- `POST /v1/videos` - Generate video (async)
- `GET /v1/videos/{id}` - Get video status
- `GET /v1/videos/{id}/content` - Download video

## Usage Examples

### 1. Generate an Image (REST API)

```bash
curl -X POST http://localhost:8000/api/v1/images/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A beautiful sunset over mountains",
    "width": 1920,
    "height": 1080,
    "service": "doubao"
  }'
```

Response:
```json
{
  "image_url": "https://...",
  "service": "doubao",
  "duration": 3.5
}
```

### 2. Generate a Video (Async)

Submit task:
```bash
curl -X POST http://localhost:8000/api/v1/videos/generate \
  -H "Content-Type: application/json" \
  -d '{
    "image": "base64_encoded_image_or_url",
    "prompt": "Gentle camera pan across the scene",
    "duration": 5,
    "fps": 30
  }'
```

Response:
```json
{
  "task_id": "vid_abc123",
  "status": "pending",
  "message": "Video generation task submitted..."
}
```

Poll for status:
```bash
curl http://localhost:8000/api/v1/tasks/vid_abc123
```

Response (when completed):
```json
{
  "task_id": "vid_abc123",
  "status": "completed",
  "progress": 100,
  "result": {
    "service": "veo3",
    "result": {
      "video_url": "https://..."
    }
  }
}
```

### 3. Chat Completion

```bash
curl -X POST http://localhost:8000/api/v1/llm/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello!"}
    ],
    "temperature": 0.7
  }'
```

### 4. Using OpenAI Python SDK

```python
import openai

# Configure to use local API
openai.api_base = "http://localhost:8000/v1"
openai.api_key = "not-needed"

# Chat completion
response = openai.ChatCompletion.create(
    model="qwen3-next-80b-a3b-instruct",
    messages=[
        {"role": "user", "content": "Hello!"}
    ]
)
print(response.choices[0].message.content)

# Image generation
response = openai.Image.create(
    prompt="A cute cat",
    n=1,
    size="1024x1024"
)
print(response['data'][0]['url'])
```

## Documentation

Detailed API documentation is available in the `/docs` folder:

- **[README.md](docs/README.md)** - This file
- **[llm_apis.md](docs/llm_apis.md)** - LLM service APIs
- **[image_apis.md](docs/image_apis.md)** - Image generation APIs
- **[video_apis.md](docs/video_apis.md)** - Video generation APIs
- **[task_management.md](docs/task_management.md)** - Task management guide
- **[openai_compatibility.md](docs/openai_compatibility.md)** - OpenAI SDK usage

## Architecture

```
┌─────────────────┐
│   Client App    │
└────────┬────────┘
         │
    ┌────▼────┐
    │ FastAPI │
    │ Backend │
    └────┬────┘
         │
    ┌────▼────────────────┐
    │  Task Manager       │
    │  (Async Processing) │
    └────┬────────────────┘
         │
    ┌────▼─────────────────┐
    │  Service Wrappers    │
    ├──────────────────────┤
    │ • LLM Service        │
    │ • Image Services     │
    │ • Video Service      │
    └──────────────────────┘
```

## Logging

Logs are stored in `./logs/` directory:

- `api.log` - API requests and responses (INFO level)
- `error.log` - Errors and exceptions (ERROR level)
- `debug.log` - Detailed debug info (DEBUG level, if enabled)

Logs rotate daily and are kept for 30 days.

## Configuration

All configuration is done through environment variables in `.env` file.

### Server Configuration

```bash
HOST=0.0.0.0              # Server host
PORT=8000                 # Server port
LOG_LEVEL=INFO            # Log level (DEBUG, INFO, WARNING, ERROR)
```

### Service Configuration

See `.env.example` for complete list of configuration options including:
- LLM service settings
- Image service settings (Doubao, NanoBanana, Midjourney)
- Video service settings (Veo3)
- Task management settings
- Concurrency settings

## Error Handling

All errors follow a consistent format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {}
  }
}
```

Common error codes:
- `VALIDATION_ERROR` - Invalid request parameters
- `SERVICE_ERROR` - External service failure
- `TASK_NOT_FOUND` - Task ID not found
- `TASK_CANCELLED` - Task was cancelled
- `RATE_LIMIT_EXCEEDED` - Too many requests

## Development

### Project Structure

```
backend/
├── main.py                 # FastAPI app entry point
├── config.py               # Configuration management
├── requirements.txt        # Dependencies
├── run_dev.py              # Development server
│
├── api/                    # API endpoints
│   ├── router.py           # Main router
│   ├── v1/                 # REST API v1
│   │   ├── llm.py
│   │   ├── images.py
│   │   ├── videos.py
│   │   └── tasks.py
│   └── openai/             # OpenAI-compatible
│       ├── chat.py
│       ├── images.py
│       └── videos.py
│
├── core/                   # Core business logic
│   ├── task_manager.py     # Async task management
│   ├── service_wrapper.py  # Service wrappers
│   ├── models.py           # Pydantic models
│   └── exceptions.py       # Custom exceptions
│
├── middleware/             # Middleware
│   ├── logging.py          # Request/response logging
│   └── error_handler.py    # Global error handling
│
├── utils/                  # Utilities
│   ├── logger.py           # Logging setup
│   └── helpers.py          # Helper functions
│
└── docs/                   # API documentation
    └── *.md
```

### Running Tests

```bash
pytest backend/tests/
```

## Deployment

### Using Docker

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY backend/ /app/backend/
COPY services/ /app/services/
COPY config/ /app/config/
COPY requirements.txt /app/

RUN pip install -r requirements.txt

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Using Systemd

Create `/etc/systemd/system/ai-api.service`:

```ini
[Unit]
Description=AI Movie Agent API
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/ai-movie-agent
Environment="PATH=/opt/ai-movie-agent/venv/bin"
ExecStart=/opt/ai-movie-agent/venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable ai-api
sudo systemctl start ai-api
```

## Performance

- **Concurrency**: Configurable via `MAX_CONCURRENT_TASKS`, `IMAGE_MAX_CONCURRENT`, `VIDEO_MAX_CONCURRENT`
- **Task Retention**: Tasks are kept for 24 hours by default (`TASK_RETENTION_HOURS`)
- **Connection Pooling**: HTTP clients use connection pooling for efficiency
- **Async Processing**: All I/O operations are async for better performance

## Security

**Important**: This is a development/internal API. For production:

1. Add authentication (API keys, OAuth2)
2. Enable HTTPS/TLS
3. Add rate limiting
4. Implement user-specific task isolation
5. Configure proper CORS origins
6. Add request validation and sanitization
7. Use secrets management (not .env files)

## Support

For issues or questions:
1. Check the API docs at `/docs`
2. Review the documentation in `backend/docs/`
3. Check logs in `./logs/`
4. Create an issue in the repository

## License

MIT License

