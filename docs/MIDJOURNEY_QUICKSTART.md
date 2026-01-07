# Midjourney 快速开始指南

## 5分钟快速集成Midjourney

### 步骤1: 配置环境变量（1分钟）

编辑 `.env` 文件，添加以下配置：

```bash
# 切换到Midjourney作为默认图片生成器
IMAGE_GENERATOR=midjourney

# 配置Midjourney API
MIDJOURNEY_API_KEY=your_api_key_here
MIDJOURNEY_BASE_URL=https://api.kuai.host
MIDJOURNEY_BOT_TYPE=MID_JOURNEY
```

### 步骤2: 测试连接（2分钟）

创建测试文件 `test_midjourney.py`:

```python
import asyncio
from pathlib import Path
from services.midjourney_service import MidjourneyService

async def test():
    service = MidjourneyService()

    print("Generating image...")
    result = await service.generate_and_save(
        prompt="a cute cat",
        save_path=Path("./output/test_cat.png")
    )

    print(f"Success! Image saved to: {result['image_path']}")
    await service.close()

asyncio.run(test())
```

运行测试：
```bash
python test_midjourney.py
```

### 步骤3: 集成到工作流（2分钟）

修改你的现有代码，使用Midjourney：

**选项A: 使用默认配置**
```python
# 无需修改任何代码，只要在.env中设置IMAGE_GENERATOR=midjourney
agent = ImageGenerationAgent()
results = await agent.execute_concurrent(scenes)
```

**选项B: 显式指定**
```python
# 即使.env设置为nano_banana，也可以临时切换
agent = ImageGenerationAgent(service_type="midjourney")
results = await agent.execute_concurrent(scenes)
```

## 完成！

现在你的系统已经成功集成Midjourney。所有图片生成将使用Midjourney API。

## 下一步

- 查看 [`docs/midjourney_integration.md`](./midjourney_integration.md) 了解更多功能
- 运行 [`examples/midjourney_example.py`](../examples/midjourney_example.py) 查看完整示例
- 尝试使用 `NIJI_JOURNEY` bot类型生成动漫风格图片

## 常见问题

**Q: 如何切换回Nano Banana？**
```bash
# 在.env中修改
IMAGE_GENERATOR=nano_banana
```

**Q: 可以同时使用两个服务吗？**
```python
# 可以！在代码中显式指定
nano_agent = ImageGenerationAgent(service_type="nano_banana")
mj_agent = ImageGenerationAgent(service_type="midjourney")
```

**Q: 如何生成动漫风格？**
```bash
# 在.env中设置
MIDJOURNEY_BOT_TYPE=NIJI_JOURNEY
```

## 技术支持

如有问题，请查看：
- [完整文档](./midjourney_integration.md)
- [更新总结](./MIDJOURNEY_UPDATE_SUMMARY.md)
- [测试用例](../tests/test_services/test_midjourney_service.py)
