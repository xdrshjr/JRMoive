# Task Management Guide

This document describes the async task management system for handling long-running operations like video generation.

## Overview

Many operations (especially video generation) take significant time to complete. Instead of blocking HTTP connections, the API uses an async task system:

1. **Submit** a task → Get `task_id`
2. **Poll** task status → Check progress
3. **Retrieve** result → Get output when complete

## Task Lifecycle

```
pending → processing → completed
                    ↓
                  failed
                    ↓
                cancelled
```

- **pending**: Task is queued, waiting to start
- **processing**: Task is currently executing
- **completed**: Task finished successfully
- **failed**: Task encountered an error
- **cancelled**: Task was cancelled by user

## Endpoints

### 1. Get Task Status

Primary endpoint for checking task progress.

**Endpoint**: `GET /api/v1/tasks/{task_id}`

**Response** (processing):
```json
{
  "task_id": "vid_abc123",
  "status": "processing",
  "progress": 45,
  "created_at": "2026-01-11T10:30:00Z",
  "updated_at": "2026-01-11T10:30:15Z",
  "completed_at": null,
  "result": null,
  "error": null
}
```

**Response** (completed):
```json
{
  "task_id": "vid_abc123",
  "status": "completed",
  "progress": 100,
  "created_at": "2026-01-11T10:30:00Z",
  "updated_at": "2026-01-11T10:31:00Z",
  "completed_at": "2026-01-11T10:31:00Z",
  "result": {
    "service": "veo3",
    "result": {
      "video_url": "https://cdn.example.com/video.mp4"
    },
    "duration": 60.5
  },
  "error": null
}
```

**Response** (failed):
```json
{
  "task_id": "vid_abc123",
  "status": "failed",
  "progress": 35,
  "created_at": "2026-01-11T10:30:00Z",
  "updated_at": "2026-01-11T10:30:45Z",
  "completed_at": null,
  "result": null,
  "error": {
    "type": "VideoGenerationError",
    "message": "Content policy violation"
  }
}
```

### 2. Cancel Task

Cancel a running or pending task.

**Endpoint**: `DELETE /api/v1/tasks/{task_id}`

**Response**:
```json
{
  "success": true,
  "message": "Task vid_abc123 has been cancelled",
  "task_id": "vid_abc123"
}
```

**Note**: Completed or already failed tasks cannot be cancelled.

### 3. List All Tasks

List all tasks in the system.

**Endpoint**: `GET /api/v1/tasks`

**Response**:
```json
[
  {
    "task_id": "vid_abc123",
    "status": "completed",
    "progress": 100,
    "created_at": "2026-01-11T10:30:00Z",
    "updated_at": "2026-01-11T10:31:00Z",
    "message": "Task completed successfully"
  },
  {
    "task_id": "vid_def456",
    "status": "processing",
    "progress": 60,
    "created_at": "2026-01-11T10:32:00Z",
    "updated_at": "2026-01-11T10:32:30Z",
    "message": "Task processing started"
  }
]
```

**Note**: In production, implement user-specific filtering and pagination.

## Polling Best Practices

### Basic Polling

Simple polling loop:

```python
import requests
import time

def wait_for_task(task_id, timeout=300):
    """Wait for task to complete with simple polling"""
    start_time = time.time()
    
    while True:
        # Check timeout
        if time.time() - start_time > timeout:
            raise TimeoutError(f"Task timeout after {timeout}s")
        
        # Get status
        response = requests.get(
            f"http://localhost:8000/api/v1/tasks/{task_id}"
        )
        response.raise_for_status()
        status = response.json()
        
        # Check if done
        if status['status'] == 'completed':
            return status['result']
        elif status['status'] == 'failed':
            raise Exception(f"Task failed: {status['error']}")
        elif status['status'] == 'cancelled':
            raise Exception("Task was cancelled")
        
        # Wait before next poll
        time.sleep(5)
```

### Exponential Backoff

More efficient polling with increasing intervals:

```python
import time

def wait_for_task_smart(task_id, max_wait=600):
    """Wait for task with exponential backoff"""
    interval = 2  # Start with 2 seconds
    max_interval = 30  # Max 30 seconds between polls
    elapsed = 0
    
    while elapsed < max_wait:
        response = requests.get(
            f"http://localhost:8000/api/v1/tasks/{task_id}"
        )
        status = response.json()
        
        print(f"[{elapsed}s] Status: {status['status']}, Progress: {status['progress']}%")
        
        if status['status'] in ['completed', 'failed', 'cancelled']:
            return status
        
        time.sleep(interval)
        elapsed += interval
        
        # Increase interval (exponential backoff)
        interval = min(interval * 1.5, max_interval)
    
    raise TimeoutError(f"Task did not complete within {max_wait}s")
```

### Progress-Based Polling

Adjust polling based on progress:

```python
def wait_for_task_adaptive(task_id, max_wait=600):
    """Adaptive polling based on progress"""
    elapsed = 0
    last_progress = 0
    stalled_count = 0
    
    while elapsed < max_wait:
        response = requests.get(
            f"http://localhost:8000/api/v1/tasks/{task_id}"
        )
        status = response.json()
        current_progress = status['progress']
        
        print(f"Progress: {current_progress}%")
        
        if status['status'] in ['completed', 'failed', 'cancelled']:
            return status
        
        # Detect stalled progress
        if current_progress == last_progress:
            stalled_count += 1
            if stalled_count > 10:  # 10 polls with no progress
                print("Warning: Task appears stalled")
        else:
            stalled_count = 0
        
        last_progress = current_progress
        
        # Dynamic interval based on progress
        if current_progress < 20:
            interval = 3  # Early stage: check frequently
        elif current_progress < 80:
            interval = 5  # Mid stage: normal polling
        else:
            interval = 2  # Near completion: check frequently
        
        time.sleep(interval)
        elapsed += interval
    
    raise TimeoutError("Task timeout")
```

### Async Polling (Python)

Using asyncio for concurrent task monitoring:

```python
import asyncio
import httpx

async def poll_task_async(task_id, client):
    """Async task polling"""
    while True:
        response = await client.get(
            f"http://localhost:8000/api/v1/tasks/{task_id}"
        )
        status = response.json()
        
        if status['status'] in ['completed', 'failed', 'cancelled']:
            return status
        
        await asyncio.sleep(5)

async def monitor_multiple_tasks(task_ids):
    """Monitor multiple tasks concurrently"""
    async with httpx.AsyncClient() as client:
        tasks = [poll_task_async(task_id, client) for task_id in task_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

# Usage
task_ids = ["vid_abc", "vid_def", "vid_ghi"]
results = asyncio.run(monitor_multiple_tasks(task_ids))
```

## Error Handling

### Retry Strategy

Implement smart retry logic:

```python
def submit_with_retry(endpoint, payload, max_retries=3):
    """Submit task with retry on failure"""
    for attempt in range(max_retries):
        try:
            response = requests.post(endpoint, json=payload)
            response.raise_for_status()
            task_info = response.json()
            
            # Wait for completion
            result = wait_for_task(task_info['task_id'])
            return result
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code >= 500:  # Server error
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"Retry {attempt + 1}/{max_retries} after {wait_time}s")
                    time.sleep(wait_time)
                    continue
            raise
        except Exception as e:
            # Check if error is retryable
            if hasattr(e, 'retryable') and e.retryable:
                if attempt < max_retries - 1:
                    time.sleep(5)
                    continue
            raise
    
    raise Exception(f"Failed after {max_retries} attempts")
```

### Graceful Degradation

Handle various error scenarios:

```python
def safe_task_execution(task_func, fallback=None):
    """Execute task with fallback"""
    try:
        result = task_func()
        return result
    except TimeoutError:
        print("Task timeout - check server logs")
        return fallback
    except Exception as e:
        error_msg = str(e)
        if 'content_policy' in error_msg.lower():
            print("Content rejected - modify input")
        elif 'rate_limit' in error_msg.lower():
            print("Rate limited - wait and retry")
        else:
            print(f"Unexpected error: {e}")
        return fallback
```

## Configuration

Task management settings in `backend/.env`:

```bash
# Task Management
TASK_STORAGE_BACKEND=memory  # or redis
TASK_RETENTION_HOURS=24      # Keep tasks for 24 hours
MAX_CONCURRENT_TASKS=10       # Max tasks running simultaneously

# For Redis backend
REDIS_URL=redis://localhost:6379
```

## Task Retention

- Tasks are automatically cleaned up after `TASK_RETENTION_HOURS` (default: 24 hours)
- Completed tasks remain accessible during retention period
- Store important results immediately after completion

## Concurrency Limits

The system limits concurrent task execution:

```bash
MAX_CONCURRENT_TASKS=10     # Total concurrent tasks
IMAGE_MAX_CONCURRENT=3      # Image generation tasks
VIDEO_MAX_CONCURRENT=2      # Video generation tasks
```

If limits are reached, new tasks wait in `pending` state.

## WebSocket Support (Future)

For real-time updates, WebSocket support is planned:

```javascript
// Future API (not yet implemented)
const ws = new WebSocket('ws://localhost:8000/ws/tasks/vid_abc123');

ws.onmessage = (event) => {
  const status = JSON.parse(event.data);
  console.log(`Progress: ${status.progress}%`);
  
  if (status.status === 'completed') {
    console.log(`Video ready: ${status.result.video_url}`);
    ws.close();
  }
};
```

## Best Practices Summary

1. **Implement Exponential Backoff**: Reduce server load
2. **Set Reasonable Timeouts**: Avoid indefinite waiting
3. **Handle All Status Types**: completed, failed, cancelled
4. **Check for Stalled Progress**: Detect stuck tasks
5. **Store Results Immediately**: Before task cleanup
6. **Implement Retry Logic**: For transient failures
7. **Monitor Multiple Tasks**: Use async patterns
8. **Graceful Error Handling**: Provide user feedback

## Troubleshooting

### Task Stuck in Pending

**Cause**: Concurrency limits reached

**Solution**: Wait for other tasks to complete or increase limits

### Task Stuck in Processing

**Cause**: Service error or network issue

**Solution**: 
- Check server logs
- Cancel and retry
- Report issue if persistent

### Task Not Found

**Cause**: Task expired (> 24 hours old)

**Solution**: Submit new task

## See Also

- [Video APIs](video_apis.md) - Primary use case for async tasks
- [Image APIs](image_apis.md) - Synchronous generation
- [README](README.md) - General API documentation

