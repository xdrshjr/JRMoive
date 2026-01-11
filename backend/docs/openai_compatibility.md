# OpenAI SDK Compatibility Guide

This document explains how to use the OpenAI Python SDK with this API as a drop-in replacement for OpenAI services.

## Overview

This API provides OpenAI-compatible endpoints that work with the official OpenAI Python SDK, allowing you to:

- Use familiar OpenAI SDK syntax
- Migrate existing code easily
- Leverage local/custom AI services
- Maintain compatibility with OpenAI-based tools

## Setup

### 1. Install OpenAI SDK

```bash
pip install openai
```

### 2. Configure API Base

Point the SDK to your local API:

```python
import openai

# Configure to use local API
openai.api_base = "http://localhost:8000/v1"
openai.api_key = "not-needed"  # No auth required (dev mode)
```

## Supported Endpoints

| OpenAI Endpoint | Status | Notes |
|----------------|---------|-------|
| `/v1/chat/completions` | ✅ Full | Chat completion |
| `/v1/images/generations` | ✅ Full | Image generation |
| `/v1/videos` | ✅ Custom | Video generation (not in official API) |
| `/v1/embeddings` | ❌ Not supported | |
| `/v1/audio/*` | ❌ Not supported | |
| `/v1/models` | ❌ Not supported | |

## Chat Completions

### Basic Usage

```python
import openai

openai.api_base = "http://localhost:8000/v1"
openai.api_key = "not-needed"

response = openai.ChatCompletion.create(
    model="qwen3-next-80b-a3b-instruct",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is AI?"}
    ]
)

print(response.choices[0].message.content)
```

### With Temperature

```python
response = openai.ChatCompletion.create(
    model="qwen3-next-80b-a3b-instruct",
    messages=[
        {"role": "user", "content": "Write a creative story"}
    ],
    temperature=0.9,  # Higher = more creative
    max_tokens=500
)

print(response.choices[0].message.content)
```

### Conversation Context

```python
messages = [
    {"role": "system", "content": "You are a helpful coding assistant."}
]

# First question
messages.append({"role": "user", "content": "How do I sort a list in Python?"})
response = openai.ChatCompletion.create(
    model="qwen3-next-80b-a3b-instruct",
    messages=messages
)
messages.append({"role": "assistant", "content": response.choices[0].message.content})

# Follow-up question
messages.append({"role": "user", "content": "Can you show an example?"})
response = openai.ChatCompletion.create(
    model="qwen3-next-80b-a3b-instruct",
    messages=messages
)

print(response.choices[0].message.content)
```

## Image Generation

### Basic Usage

```python
import openai

openai.api_base = "http://localhost:8000/v1"
openai.api_key = "not-needed"

response = openai.Image.create(
    prompt="A beautiful sunset over mountains",
    n=1,
    size="1024x1024"
)

image_url = response['data'][0]['url']
print(f"Image URL: {image_url}")
```

### Different Sizes

```python
# Square formats
response = openai.Image.create(
    prompt="A cute cat",
    size="256x256"   # or "512x512", "1024x1024"
)

# Landscape
response = openai.Image.create(
    prompt="Mountain landscape",
    size="1792x1024"
)

# Portrait
response = openai.Image.create(
    prompt="Portrait photo",
    size="1024x1792"
)
```

### Base64 Response

```python
import base64
from PIL import Image
from io import BytesIO

response = openai.Image.create(
    prompt="A futuristic city",
    n=1,
    size="1024x1024",
    response_format="b64_json"  # Get base64 instead of URL
)

# Decode and save
image_b64 = response['data'][0]['b64_json']
image_data = base64.b64decode(image_b64)
image = Image.open(BytesIO(image_data))
image.save("output.png")
```

### High Quality

```python
response = openai.Image.create(
    prompt="Professional portrait photo",
    size="1024x1024",
    quality="hd"  # Use 'hd' for higher quality
)
```

## Video Generation

**Note**: Video generation is a custom extension (not in official OpenAI API).

### Basic Usage

Since video generation isn't in the official SDK, use requests directly or create a custom wrapper:

```python
import requests
import time

api_base = "http://localhost:8000/v1"

# Submit video generation
response = requests.post(
    f"{api_base}/videos",
    json={
        "prompt": "Gentle camera pan across scene",
        "input_reference": image_base64,
        "size": "1920x1080",
        "seconds": 5
    }
)

video_info = response.json()
video_id = video_info['id']

# Poll for completion
while True:
    status_response = requests.get(f"{api_base}/videos/{video_id}")
    status = status_response.json()
    
    print(f"Status: {status['status']}, Progress: {status['progress']}%")
    
    if status['status'] == 'completed':
        print(f"Video URL: {status['video_url']}")
        break
    
    time.sleep(5)
```

### Custom Wrapper

Create an OpenAI-style wrapper:

```python
class VideoAPI:
    def __init__(self, api_base):
        self.api_base = api_base
    
    def create(self, prompt, input_reference, size="1920x1080", seconds=5):
        """Submit video generation"""
        response = requests.post(
            f"{self.api_base}/videos",
            json={
                "prompt": prompt,
                "input_reference": input_reference,
                "size": size,
                "seconds": seconds
            }
        )
        return response.json()
    
    def retrieve(self, video_id):
        """Get video status"""
        response = requests.get(f"{self.api_base}/videos/{video_id}")
        return response.json()
    
    def wait_for_completion(self, video_id, timeout=300):
        """Wait for video to complete"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.retrieve(video_id)
            if status['status'] == 'completed':
                return status
            elif status['status'] == 'failed':
                raise Exception(f"Video generation failed: {status.get('error')}")
            time.sleep(5)
        raise TimeoutError("Video generation timeout")

# Usage
openai.Video = VideoAPI("http://localhost:8000/v1")

response = openai.Video.create(
    prompt="Slow camera pan",
    input_reference=image_base64,
    seconds=5
)

result = openai.Video.wait_for_completion(response['id'])
print(f"Video URL: {result['video_url']}")
```

## Error Handling

### Standard Error Format

```python
import openai
from openai.error import APIError, RateLimitError

try:
    response = openai.ChatCompletion.create(
        model="qwen3-next-80b-a3b-instruct",
        messages=[{"role": "user", "content": "Hello"}]
    )
except RateLimitError:
    print("Rate limit exceeded - wait and retry")
except APIError as e:
    print(f"API error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Retry with Backoff

```python
import time
from openai.error import APIError

def chat_with_retry(messages, max_retries=3):
    """Chat completion with exponential backoff"""
    for attempt in range(max_retries):
        try:
            response = openai.ChatCompletion.create(
                model="qwen3-next-80b-a3b-instruct",
                messages=messages
            )
            return response
        except APIError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Retry {attempt + 1}/{max_retries} after {wait_time}s")
                time.sleep(wait_time)
            else:
                raise
```

## Configuration

### Environment Variables

```python
import os
import openai

# Load from environment
openai.api_base = os.getenv("OPENAI_API_BASE", "http://localhost:8000/v1")
openai.api_key = os.getenv("OPENAI_API_KEY", "not-needed")
```

### Per-Request Configuration

```python
# Override for specific request
response = openai.ChatCompletion.create(
    model="qwen3-next-80b-a3b-instruct",
    messages=[{"role": "user", "content": "Hello"}],
    api_base="http://another-server:8000/v1",
    api_key="custom-key"
)
```

## Differences from OpenAI API

### 1. No API Key Required (Development)

```python
# This API (dev mode)
openai.api_key = "not-needed"

# Real OpenAI
openai.api_key = "sk-..."  # Required
```

### 2. Model Names

```python
# This API - use configured model names
response = openai.ChatCompletion.create(
    model="qwen3-next-80b-a3b-instruct",  # Your LLM
    messages=[...]
)

# OpenAI
response = openai.ChatCompletion.create(
    model="gpt-4",  # OpenAI models
    messages=[...]
)
```

### 3. Image Services

```python
# This API - multiple services available
# Configured via IMAGE_SERVICE_TYPE in backend/.env
response = openai.Image.create(
    prompt="...",
    # Uses: doubao, nano_banana, or midjourney
)

# OpenAI - DALL-E only
response = openai.Image.create(
    prompt="...",
    model="dall-e-3"
)
```

### 4. Video Generation

```python
# This API - custom extension
# Not available in official OpenAI API (yet)

# OpenAI - not supported
```

### 5. Streaming

```python
# This API - not yet supported
response = openai.ChatCompletion.create(
    messages=[...],
    stream=True  # Will return error
)

# OpenAI - supported
for chunk in openai.ChatCompletion.create(..., stream=True):
    print(chunk)
```

## Migration Guide

### From OpenAI to This API

1. **Change API Base**:
```python
# Before
import openai
openai.api_key = "sk-..."

# After
import openai
openai.api_base = "http://localhost:8000/v1"
openai.api_key = "not-needed"
```

2. **Update Model Names**:
```python
# Before
model="gpt-4"

# After
model="qwen3-next-80b-a3b-instruct"  # Or your configured model
```

3. **Remove Unsupported Features**:
```python
# Remove streaming
stream=False  # Or omit

# Remove embeddings, audio, etc.
```

### To OpenAI from This API

Simply restore original configuration:

```python
import openai

# Restore OpenAI endpoints
openai.api_base = "https://api.openai.com/v1"
openai.api_key = "sk-..."  # Your OpenAI key

# Update model names back
model="gpt-4"
```

## Complete Example

```python
import openai
import base64
import time

# Configure
openai.api_base = "http://localhost:8000/v1"
openai.api_key = "not-needed"

# 1. Chat to get image prompt
print("1. Getting prompt suggestion...")
chat_response = openai.ChatCompletion.create(
    model="qwen3-next-80b-a3b-instruct",
    messages=[
        {"role": "user", "content": "Suggest a creative prompt for a landscape image"}
    ]
)
prompt = chat_response.choices[0].message.content
print(f"Prompt: {prompt}")

# 2. Generate image
print("\n2. Generating image...")
image_response = openai.Image.create(
    prompt=prompt,
    size="1024x1024",
    response_format="b64_json"
)
image_b64 = image_response['data'][0]['b64_json']
print("Image generated!")

# 3. Generate video (custom extension)
print("\n3. Generating video...")
video_response = requests.post(
    f"{openai.api_base}/videos",
    json={
        "prompt": "Slow camera pan revealing the landscape",
        "input_reference": image_b64,
        "seconds": 5
    }
)
video_id = video_response.json()['id']

# Wait for video
while True:
    status = requests.get(f"{openai.api_base}/videos/{video_id}").json()
    print(f"Video progress: {status['progress']}%")
    if status['status'] == 'completed':
        print(f"\nVideo URL: {status['video_url']}")
        break
    time.sleep(5)
```

## See Also

- [Chat APIs](llm_apis.md) - LLM chat completion details
- [Image APIs](image_apis.md) - Image generation details
- [Video APIs](video_apis.md) - Video generation details
- [Task Management](task_management.md) - Async task handling

