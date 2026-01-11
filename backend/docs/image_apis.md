# Image Generation APIs Documentation

This document describes the Image Generation API endpoints supporting multiple services (Doubao, NanoBanana, Midjourney).

## Overview

The Image APIs provide:
- **Text-to-Image**: Generate images from text prompts
- **Image-to-Image**: Generate images based on reference images
- **Multiple Services**: Choose between Doubao, NanoBanana, or Midjourney
- **Prompt Optimization**: Auto-enhance prompts with LLM

## Base URLs

- **REST API**: `http://localhost:8000/api/v1/images`
- **OpenAI Compatible**: `http://localhost:8000/v1/images`

## Available Services

| Service | Text-to-Image | Image-to-Image | Features |
|---------|---------------|----------------|----------|
| **Doubao** | ✅ | ✅ | High quality, fast, supports i2i |
| **NanoBanana** | ✅ | ❌ | Multiple models, good quality |
| **Midjourney** | ✅ | ❌ | Artistic, auto-upscale option |

## Endpoints

### 1. List Available Services

Get list of configured image services.

**Endpoint**: `GET /api/v1/images/services`

**Response**:
```json
["doubao", "nano_banana", "midjourney"]
```

**Example**:
```bash
curl http://localhost:8000/api/v1/images/services
```

### 2. Generate Image (Text-to-Image)

Generate an image from a text prompt.

**Endpoint**: `POST /api/v1/images/generate`

**Request Body**:
```json
{
  "prompt": "A serene mountain landscape at golden hour",
  "service": "doubao",
  "width": 1920,
  "height": 1080,
  "quality": "high",
  "style": "photorealistic",
  "negative_prompt": "blur, low quality, distorted",
  "seed": 42,
  "cfg_scale": 7.5,
  "steps": 50,
  "optimize_prompt": true
}
```

**Parameters**:
- `prompt` (required): Image description
- `service` (optional): Service to use (`doubao`, `nano_banana`, `midjourney`)
  - Default: From configuration
- `width` (optional): Image width in pixels (64-4096, default: 1920)
- `height` (optional): Image height in pixels (64-4096, default: 1080)
- `quality` (optional): Quality level (`low`, `medium`, `high`, `ultra`)
- `style` (optional): Style specification
- `negative_prompt` (optional): What to avoid
- `seed` (optional): Random seed for reproducibility
- `cfg_scale` (optional): Guidance scale (1.0-20.0)
- `steps` (optional): Generation steps (20-100)
- `optimize_prompt` (optional): Auto-optimize with LLM (default: false)

**Response**:
```json
{
  "image_url": "https://cdn.example.com/image123.png",
  "image_b64": null,
  "service": "doubao",
  "duration": 3.5
}
```

**Example (curl)**:
```bash
curl -X POST http://localhost:8000/api/v1/images/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A majestic lion in the savanna",
    "width": 1024,
    "height": 1024,
    "service": "doubao"
  }'
```

**Example (Python)**:
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/images/generate",
    json={
        "prompt": "A futuristic cityscape at night",
        "width": 1920,
        "height": 1080,
        "quality": "high",
        "optimize_prompt": True
    }
)

result = response.json()
print(f"Image URL: {result['image_url']}")
print(f"Generated in: {result['duration']}s")
```

### 3. Image-to-Image Generation

Generate an image based on a reference image.

**Endpoint**: `POST /api/v1/images/generate-i2i`

**Request Body**:
```json
{
  "prompt": "Transform into a watercolor painting",
  "image": "base64_encoded_image_or_url",
  "service": "doubao",
  "width": 1920,
  "height": 1080,
  "reference_weight": 0.7,
  "negative_prompt": "realistic, photographic",
  "seed": 42,
  "cfg_scale": 7.5,
  "steps": 50
}
```

**Parameters**:
- `prompt` (required): Transformation description
- `image` (required): Base64 encoded image or URL
- `service` (optional): Only `doubao` supported for i2i
- `width`, `height`: Output dimensions
- `reference_weight` (optional): Weight of reference image (0.0-1.0, default: 0.7)
  - Higher = closer to original
  - Lower = more creative interpretation
- Other parameters: Same as text-to-image

**Response**: Same as text-to-image

**Example**:
```python
import requests
import base64

# Read and encode image
with open("input.jpg", "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode()

response = requests.post(
    "http://localhost:8000/api/v1/images/generate-i2i",
    json={
        "prompt": "Convert to anime style",
        "image": image_b64,
        "reference_weight": 0.6
    }
)

result = response.json()
print(f"Generated: {result['image_url']}")
```

### 4. Generate Image (OpenAI Compatible)

OpenAI-format image generation endpoint.

**Endpoint**: `POST /v1/images/generations`

**Request Body**:
```json
{
  "prompt": "A cute cat playing with yarn",
  "n": 1,
  "size": "1024x1024",
  "response_format": "url",
  "quality": "standard"
}
```

**Parameters**:
- `prompt` (required): Image description
- `n` (optional): Number of images (currently only 1 supported)
- `size` (optional): Image size (`256x256`, `512x512`, `1024x1024`, `1792x1024`, `1024x1792`)
- `response_format` (optional): `url` or `b64_json`
- `quality` (optional): `standard` or `hd`

**Response**:
```json
{
  "created": 1677652288,
  "data": [
    {
      "url": "https://..."
    }
  ]
}
```

**Example (OpenAI SDK)**:
```python
import openai

openai.api_base = "http://localhost:8000/v1"
openai.api_key = "not-needed"

response = openai.Image.create(
    prompt="A beautiful sunset over the ocean",
    n=1,
    size="1024x1024"
)

image_url = response['data'][0]['url']
print(f"Image: {image_url}")
```

## Service-Specific Features

### Doubao

Best for: High quality, fast generation, image-to-image

```python
response = requests.post(
    "http://localhost:8000/api/v1/images/generate",
    json={
        "prompt": "A photorealistic portrait",
        "service": "doubao",
        "width": 1920,
        "height": 1080,
        "cfg_scale": 7.5,
        "steps": 60
    }
)
```

### NanoBanana

Best for: Variety, multiple model support

```python
response = requests.post(
    "http://localhost:8000/api/v1/images/generate",
    json={
        "prompt": "An abstract digital art piece",
        "service": "nano_banana",
        "width": 1024,
        "height": 1024,
        "style": "digital-art"
    }
)
```

### Midjourney

Best for: Artistic images, creative compositions

```python
response = requests.post(
    "http://localhost:8000/api/v1/images/generate",
    json={
        "prompt": "A fantasy landscape with dragons",
        "service": "midjourney",
        "width": 1024,
        "height": 1024
    }
)
```

## Configuration

Configure image services in `backend/.env`:

```bash
# Default service
IMAGE_SERVICE_TYPE=doubao

# Doubao
DOUBAO_API_KEY=your_key_here
DOUBAO_BASE_URL=https://ark.cn-beijing.volces.com
DOUBAO_MODEL=doubao-seedream-4-5-251128

# NanoBanana
NANO_BANANA_API_KEY=your_key_here
NANO_BANANA_BASE_URL=https://api.nanobananapro.com/v1
NANO_BANANA_MODEL=dall-e-3

# Midjourney
MIDJOURNEY_API_KEY=your_key_here
MIDJOURNEY_BASE_URL=https://api.kuai.host
MIDJOURNEY_AUTO_UPSCALE=false

# Concurrency
IMAGE_MAX_CONCURRENT=3
```

## Best Practices

### 1. Prompt Engineering

Good prompts lead to better results:

```
Bad: "A cat"
Good: "A fluffy orange tabby cat with green eyes, sitting on a wooden windowsill, soft natural lighting, shallow depth of field, 8K, photorealistic"
```

Use prompt optimization for automatic enhancement:
```python
response = requests.post(
    "http://localhost:8000/api/v1/images/generate",
    json={
        "prompt": "A cat on a windowsill",
        "optimize_prompt": True  # LLM enhances prompt
    }
)
```

### 2. Reproducibility

Use seed for consistent results:

```python
# Generate with specific seed
response = requests.post(
    "http://localhost:8000/api/v1/images/generate",
    json={
        "prompt": "A mountain landscape",
        "seed": 42,  # Same seed = same result
        "cfg_scale": 7.5,
        "steps": 50
    }
)
```

### 3. Quality vs Speed

Balance quality and generation time:

- **Fast**: `steps=20-30`, `quality="medium"`
- **Balanced**: `steps=40-50`, `quality="high"`
- **High Quality**: `steps=60-80`, `quality="ultra"`

### 4. Negative Prompts

Avoid unwanted elements:

```python
response = requests.post(
    "http://localhost:8000/api/v1/images/generate",
    json={
        "prompt": "A portrait photo",
        "negative_prompt": "blur, distorted, low quality, ugly, deformed"
    }
)
```

### 5. Image-to-Image Weight

Control transformation strength:

```python
# Subtle changes (reference_weight=0.8-0.9)
response = requests.post(
    "http://localhost:8000/api/v1/images/generate-i2i",
    json={
        "prompt": "Enhance colors",
        "image": image_b64,
        "reference_weight": 0.9  # Stay close to original
    }
)

# Major transformation (reference_weight=0.3-0.5)
response = requests.post(
    "http://localhost:8000/api/v1/images/generate-i2i",
    json={
        "prompt": "Transform to anime style",
        "image": image_b64,
        "reference_weight": 0.4  # More creative freedom
    }
)
```

## Error Handling

**Common Errors**:

```json
{
  "error": {
    "code": "SERVICE_ERROR",
    "message": "Image generation failed: Content policy violation",
    "details": {"service": "doubao", "retryable": false}
  }
}
```

**Error Codes**:
- `VALIDATION_ERROR`: Invalid parameters
- `SERVICE_ERROR`: Service failure
- `CONTENT_POLICY_VIOLATION`: Prompt violates content policy

## Performance

- **Average Generation Time**:
  - Doubao: 2-5 seconds
  - NanoBanana: 3-8 seconds
  - Midjourney: 30-60 seconds (includes upscaling)
- **Concurrent Requests**: Configured via `IMAGE_MAX_CONCURRENT`
- **Max Image Size**: 4096x4096 pixels

## Limitations

1. **Concurrent Generation**: Limited by `IMAGE_MAX_CONCURRENT` setting
2. **File Size**: Large images may take longer
3. **Content Policy**: Some prompts may be rejected
4. **Service Availability**: Depends on upstream services

## See Also

- [LLM APIs](llm_apis.md) - Prompt optimization
- [Video APIs](video_apis.md) - Generate videos from images
- [OpenAI Compatibility](openai_compatibility.md) - OpenAI SDK usage

