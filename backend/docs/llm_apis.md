# LLM APIs Documentation

This document describes the LLM (Large Language Model) API endpoints for chat completion and prompt optimization.

## Overview

The LLM APIs provide:
- **Chat Completion**: Generate conversational responses
- **Prompt Optimization**: Enhance prompts for better image/video generation

## Base URLs

- **REST API**: `http://localhost:8000/api/v1/llm`
- **OpenAI Compatible**: `http://localhost:8000/v1/chat`

## Authentication

Currently no authentication is required. For production, add API key authentication.

## Endpoints

### 1. Chat Completion (REST)

Generate a chat completion response.

**Endpoint**: `POST /api/v1/llm/chat`

**Request Body**:
```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is AI?"}
  ],
  "temperature": 0.7,
  "max_tokens": 1000,
  "stream": false
}
```

**Parameters**:
- `messages` (required): Array of message objects with `role` and `content`
  - Roles: `system`, `user`, `assistant`
- `model` (optional): Model name (uses configured model if not specified)
- `temperature` (optional): Sampling temperature 0.0-2.0 (default: 0.7)
- `max_tokens` (optional): Maximum tokens to generate
- `stream` (optional): Enable streaming (not yet supported)

**Response**:
```json
{
  "id": "chatcmpl-1234567890",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "qwen3-next-80b-a3b-instruct",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "AI (Artificial Intelligence) refers to..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 50,
    "total_tokens": 65
  }
}
```

**Example (curl)**:
```bash
curl -X POST http://localhost:8000/api/v1/llm/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Explain neural networks in simple terms"}
    ],
    "temperature": 0.7
  }'
```

**Example (Python)**:
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/llm/chat",
    json={
        "messages": [
            {"role": "user", "content": "What is machine learning?"}
        ],
        "temperature": 0.7
    }
)

result = response.json()
assistant_message = result["choices"][0]["message"]["content"]
print(assistant_message)
```

### 2. Prompt Optimization

Optimize a prompt for image or video generation.

**Endpoint**: `POST /api/v1/llm/optimize-prompt`

**Request Body**:
```json
{
  "prompt": "A cat sitting on a chair",
  "type": "image",
  "style": "photorealistic",
  "enhance_details": true
}
```

**Parameters**:
- `prompt` (required): Original prompt to optimize
- `type` (required): Optimization type (`image` or `video`)
- `style` (optional): Desired style
- `enhance_details` (optional): Add more details (default: true)

**Response**:
```json
{
  "original_prompt": "A cat sitting on a chair",
  "optimized_prompt": "A photorealistic image of an elegant tabby cat with detailed fur texture, sitting gracefully on a vintage wooden chair with intricate carvings, soft natural lighting from a nearby window, shallow depth of field, 8K resolution, professional photography",
  "improvements": [
    "Enhanced visual details",
    "Improved composition structure",
    "Added technical parameters",
    "Optimized for generation quality"
  ]
}
```

**Example (curl)**:
```bash
curl -X POST http://localhost:8000/api/v1/llm/optimize-prompt \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Mountain landscape at sunset",
    "type": "image"
  }'
```

**Example (Python)**:
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/llm/optimize-prompt",
    json={
        "prompt": "A serene ocean scene",
        "type": "video"
    }
)

result = response.json()
print(f"Original: {result['original_prompt']}")
print(f"Optimized: {result['optimized_prompt']}")
```

### 3. Chat Completion (OpenAI Compatible)

OpenAI-format chat completion endpoint.

**Endpoint**: `POST /v1/chat/completions`

**Request/Response**: Same format as OpenAI API

**Example (OpenAI SDK)**:
```python
import openai

openai.api_base = "http://localhost:8000/v1"
openai.api_key = "not-needed"

response = openai.ChatCompletion.create(
    model="qwen3-next-80b-a3b-instruct",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Tell me a joke"}
    ],
    temperature=0.7
)

print(response.choices[0].message.content)
```

## Configuration

Configure LLM service in `backend/.env`:

```bash
# Fast LLM (for prompt optimization)
FAST_LLM_API_KEY=your_api_key_here
FAST_LLM_API_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
FAST_LLM_MODEL=qwen3-next-80b-a3b-instruct
ENABLE_PROMPT_OPTIMIZATION=true

# Judge LLM (for image quality scoring)
JUDGE_LLM_API_KEY=your_judge_api_key_here
JUDGE_LLM_API_URL=https://ark.cn-beijing.volces.com/api/v3
JUDGE_LLM_MODEL=doubao-seed-1-6-251015
```

## Best Practices

### 1. System Messages

Use system messages to set the behavior:

```json
{
  "messages": [
    {"role": "system", "content": "You are an expert photographer helping with image prompts."},
    {"role": "user", "content": "Create a prompt for a landscape photo"}
  ]
}
```

### 2. Temperature Control

- **Low (0.1-0.3)**: Deterministic, factual responses
- **Medium (0.5-0.7)**: Balanced creativity
- **High (0.8-1.5)**: More creative, varied outputs

### 3. Conversation History

Maintain conversation context:

```json
{
  "messages": [
    {"role": "user", "content": "What is AI?"},
    {"role": "assistant", "content": "AI is..."},
    {"role": "user", "content": "How does it work?"}
  ]
}
```

### 4. Prompt Optimization

Enable automatic prompt optimization for better results:

```python
# When generating images
response = requests.post(
    "http://localhost:8000/api/v1/images/generate",
    json={
        "prompt": "A cat",
        "optimize_prompt": True  # Enable optimization
    }
)
```

## Error Handling

**Common Errors**:

```json
{
  "error": {
    "code": "SERVICE_ERROR",
    "message": "LLM service unavailable",
    "details": {"retryable": true}
  }
}
```

**Error Codes**:
- `VALIDATION_ERROR`: Invalid request parameters
- `SERVICE_ERROR`: LLM service error (usually retryable)
- `RATE_LIMIT_EXCEEDED`: Too many requests

## Performance

- **Average Latency**: 1-3 seconds for chat completion
- **Max Tokens**: Configurable, affects response time
- **Concurrent Requests**: Handled asynchronously

## Limitations

1. **Streaming**: Not yet supported (returns error if `stream=true`)
2. **Context Length**: Limited by configured model
3. **Rate Limits**: Depends on upstream LLM service

## See Also

- [Image APIs](image_apis.md) - Use optimized prompts for image generation
- [Video APIs](video_apis.md) - Use optimized prompts for video generation
- [OpenAI Compatibility](openai_compatibility.md) - Full OpenAI SDK guide

