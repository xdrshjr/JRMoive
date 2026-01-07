# Midjourney图片生成模型集成指南

## 概述

系统现已支持Midjourney图片生成模型，用户可以在配置中自由选择使用Nano Banana或Midjourney作为默认图片生成服务。

## 配置说明

### 1. 环境变量配置

在`.env`文件中添加以下配置：

```bash
# 选择默认图片生成模型 (nano_banana 或 midjourney)
IMAGE_GENERATOR=midjourney

# Midjourney API配置
MIDJOURNEY_API_KEY=your_api_key_here
MIDJOURNEY_BASE_URL=https://api.kuai.host
MIDJOURNEY_BOT_TYPE=MID_JOURNEY  # 可选：MID_JOURNEY 或 NIJI_JOURNEY
MIDJOURNEY_POLL_INTERVAL=3.0  # 轮询间隔（秒）
MIDJOURNEY_MAX_POLL_ATTEMPTS=100  # 最大轮询次数
```

### 2. Bot类型说明

- `MID_JOURNEY`: 标准Midjourney模型（默认）
- `NIJI_JOURNEY`: Niji风格模型（适合动漫风格）

## 使用方法

### 方法1: 使用默认配置

在`.env`中设置`IMAGE_GENERATOR=midjourney`后，所有图片生成将自动使用Midjourney：

```python
from agents.image_generator_agent import ImageGenerationAgent
from models.script_models import Scene, ShotType, CameraMovement

# 创建场景
scene = Scene(
    scene_id="scene_001",
    location="森林",
    time="黄昏",
    description="一只猫坐在树下",
    duration=3.0,
    shot_type=ShotType.MEDIUM_SHOT,
    camera_movement=CameraMovement.STATIC
)

# 创建Agent（自动使用配置中的默认服务）
agent = ImageGenerationAgent()

# 生成图片
results = await agent.execute_concurrent([scene])
```

### 方法2: 显式指定服务类型

即使配置默认为Nano Banana，也可以临时切换到Midjourney：

```python
from agents.image_generator_agent import ImageGenerationAgent

# 显式指定使用Midjourney
agent = ImageGenerationAgent(service_type="midjourney")

# 或使用Nano Banana
agent = ImageGenerationAgent(service_type="nano_banana")
```

### 方法3: 直接使用MidjourneyService

如果需要更精细的控制，可以直接使用服务类：

```python
from services.midjourney_service import MidjourneyService
from pathlib import Path

# 创建服务实例
service = MidjourneyService(
    api_key="your_api_key",
    base_url="https://api.kuai.host",
    bot_type="MID_JOURNEY",
    poll_interval=3.0,
    max_poll_attempts=100
)

# 生成并保存图片
result = await service.generate_and_save(
    prompt="a cat sitting under a tree at sunset, digital art",
    save_path=Path("./output/cat.png")
)

print(f"Image saved to: {result['image_path']}")
print(f"Task ID: {result['task_id']}")

# 关闭服务
await service.close()
```

## API功能说明

### MidjourneyService 主要方法

#### 1. submit_imagine()
提交图片生成任务

```python
task_id = await service.submit_imagine(
    prompt="a beautiful landscape",
    base64_array=["base64_encoded_image"],  # 可选：垫图
    notify_hook="https://your-webhook.com",  # 可选：回调地址
    state="custom_data"  # 可选：自定义参数
)
```

#### 2. fetch_task()
查询任务状态

```python
task_info = await service.fetch_task(task_id)
print(f"Status: {task_info['status']}")
print(f"Progress: {task_info['progress']}")
```

#### 3. wait_for_completion()
等待任务完成（带进度回调）

```python
def progress_callback(progress: str, status: str):
    print(f"Progress: {progress}, Status: {status}")

result = await service.wait_for_completion(
    task_id,
    progress_callback=progress_callback
)
```

#### 4. generate_image()
一步生成图片（提交+等待）

```python
result = await service.generate_image(
    prompt="a cat",
    progress_callback=lambda p, s: print(f"{p} - {s}")
)

print(f"Image URL: {result['image_url']}")
```

#### 5. generate_and_save()
生成并保存到本地

```python
result = await service.generate_and_save(
    prompt="a cat",
    save_path=Path("./cat.png")
)
```

## 工作流程集成

在完整的剧本生成工作流中使用Midjourney：

```python
from agents.orchestrator_agent import DramaGenerationOrchestrator
from config.settings import settings

# 在配置中设置使用Midjourney
settings.image_generator = "midjourney"

# 创建编排器
orchestrator = DramaGenerationOrchestrator()

# 执行完整工作流（将使用Midjourney生成图片）
result = await orchestrator.execute(script_path="script.txt")
```

## 注意事项

1. **API密钥**: 确保在`.env`文件中正确配置`MIDJOURNEY_API_KEY`
2. **轮询配置**: Midjourney采用异步生成，需要轮询等待。默认配置：
   - 轮询间隔：3秒
   - 最大轮询次数：100次（约5分钟）
3. **超时处理**: 如果任务超时，会抛出`TimeoutError`
4. **失败处理**: 如果生成失败，会抛出`ValueError`并包含失败原因
5. **并发限制**: 建议根据API限制调整`max_concurrent`配置

## 切换模型对比

| 特性 | Nano Banana | Midjourney |
|------|-------------|------------|
| 生成速度 | 快（同步） | 慢（异步，需轮询） |
| 图片质量 | 高 | 非常高 |
| 风格控制 | 通过prompt | 通过prompt + bot类型 |
| 垫图支持 | 支持 | 支持（base64数组） |
| 适用场景 | 快速原型、批量生成 | 高质量艺术创作 |

## 故障排查

### 问题1: 导入错误
```python
# 确保正确导入
from services.midjourney_service import MidjourneyService
from agents.image_generator_agent import ImageGenerationAgent
```

### 问题2: API密钥未配置
```
ValueError: API key not configured
```
解决方案：在`.env`中配置`MIDJOURNEY_API_KEY`

### 问题3: 任务超时
```
TimeoutError: Task did not complete within ...
```
解决方案：
- 增加`MIDJOURNEY_MAX_POLL_ATTEMPTS`
- 检查网络连接
- 查看API服务状态

### 问题4: 生成失败
```
ValueError: Task failed: Invalid prompt
```
解决方案：
- 检查prompt是否符合Midjourney规范
- 查看failReason详细信息
- 调整prompt内容

## 示例脚本

完整示例见 `examples/midjourney_example.py`（即将添加）

```python
import asyncio
from pathlib import Path
from agents.image_generator_agent import ImageGenerationAgent
from models.script_models import Scene, ShotType, CameraMovement

async def main():
    # 创建场景
    scenes = [
        Scene(
            scene_id="scene_001",
            location="古老的城堡",
            time="夜晚",
            description="月光照耀下的神秘城堡",
            duration=3.0,
            shot_type=ShotType.LONG_SHOT,
            camera_movement=CameraMovement.DOLLY,
            visual_style="哥特式",
            color_tone="冷色调"
        ),
        Scene(
            scene_id="scene_002",
            location="城堡大厅",
            time="夜晚",
            description="华丽的水晶吊灯",
            duration=2.5,
            shot_type=ShotType.CLOSE_UP,
            camera_movement=CameraMovement.STATIC,
            visual_style="古典",
            color_tone="暖色调"
        )
    ]

    # 使用Midjourney生成
    agent = ImageGenerationAgent(
        service_type="midjourney",
        output_dir=Path("./output/midjourney_images")
    )

    # 执行生成
    results = await agent.execute_concurrent(scenes)

    # 输出结果
    for result in results:
        print(f"Scene: {result['scene_id']}")
        print(f"Image: {result['image_path']}")
        print(f"Prompt: {result['prompt'][:50]}...")
        print("---")

    await agent.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## 更新日志

- **2026-01-07**: 添加Midjourney模型支持
  - 新增`MidjourneyService`类
  - 更新`ImageGenerationAgent`支持多模型
  - 添加配置选项`IMAGE_GENERATOR`
  - 完整的测试覆盖
