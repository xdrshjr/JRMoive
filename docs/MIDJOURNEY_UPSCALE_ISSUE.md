# Midjourney Upscale问题说明与解决方案

## 问题现状

当前使用的Midjourney API代理（`https://api.kuai.host`）在提交upscale action时返回400错误：

```
POST https://api.kuai.host/mj/submit/action
Response: 400 Bad Request
{"code":0,"description":" ","type":"upstream_error"}
```

## 可能的原因

1. **API endpoint不对** - 该API代理可能使用不同的endpoint
2. **Payload格式不匹配** - 需要不同的参数格式
3. **不支持action操作** - 该API代理可能只支持imagine，不支持upscale/variation等操作

## 临时解决方案

**已在`.env`中禁用自动upscale：**

```bash
MIDJOURNEY_AUTO_UPSCALE=false  # 暂时禁用
```

这样系统会直接返回四宫格图片，虽然不是单张，但能正常工作。

## 四宫格的处理方式

### 方案1: 手动裁剪（推荐）

可以在后续处理中自动裁剪四宫格的某一部分：

```python
from PIL import Image

def crop_grid_image(image_path, index=1):
    """
    裁剪四宫格图片的某一部分

    Args:
        image_path: 四宫格图片路径
        index: 要裁剪的索引 (1=左上, 2=右上, 3=左下, 4=右下)

    Returns:
        裁剪后的单张图片
    """
    img = Image.open(image_path)
    width, height = img.size

    # 计算单张图片的尺寸
    crop_width = width // 2
    crop_height = height // 2

    # 根据索引计算裁剪区域
    positions = {
        1: (0, 0, crop_width, crop_height),  # 左上
        2: (crop_width, 0, width, crop_height),  # 右上
        3: (0, crop_height, crop_width, height),  # 左下
        4: (crop_width, crop_height, width, height)  # 右下
    }

    box = positions.get(index, positions[1])
    cropped = img.crop(box)

    return cropped

# 使用示例
cropped_img = crop_grid_image("./output/grid_image.png", index=1)
cropped_img.save("./output/single_image.png")
```

### 方案2: 在Prompt中添加参数

尝试在prompt末尾添加参数（某些API支持）：

```python
prompt = "a beautiful landscape --no grid --single"
```

或者：

```python
prompt = "a beautiful landscape --ar 16:9"  # 指定宽高比可能避免四宫格
```

### 方案3: 联系API提供商

询问API提供商是否支持upscale操作，以及正确的API调用方式。可能需要：

- 不同的endpoint（如 `/mj/upsample` 等）
- 不同的认证方式
- 或者需要升级API计划

## 长期解决方案

### 选项A: 找到支持完整功能的API

寻找支持以下功能的Midjourney API代理：
- ✅ Imagine（生成四宫格）
- ✅ Upscale（放大单张）
- ✅ Variation（变体）
- ✅ Reroll（重新生成）

推荐的API代理：
1. Midjourney官方API（如果可用）
2. 其他经过验证的第三方代理

### 选项B: 实现本地裁剪功能

在`MidjourneyService`中添加自动裁剪功能：

```python
async def generate_and_crop(
    self,
    prompt: str,
    crop_index: int = 1,
    **kwargs
) -> Dict[str, Any]:
    """
    生成四宫格并自动裁剪为单张
    """
    # 生成四宫格
    result = await self.generate_image(prompt, auto_upscale=False, **kwargs)

    # 下载图片
    grid_path = Path("./temp/grid.png")
    await self.download_image(result['image_url'], grid_path)

    # 裁剪
    single_path = Path("./temp/single.png")
    from PIL import Image
    img = Image.open(grid_path)
    # ... 裁剪逻辑 ...

    return {
        'image_url': result['image_url'],
        'grid_path': str(grid_path),
        'cropped_path': str(single_path),
        'is_cropped': True
    }
```

## 当前配置建议

```bash
# .env配置
MIDJOURNEY_AUTO_UPSCALE=false  # 禁用upscale，使用四宫格
```

运行时会：
1. ✅ 正常生成四宫格
2. ⚠️ 跳过upscale步骤
3. ✅ 返回四宫格图片URL

## 测试API支持情况

创建测试脚本查看API支持的操作：

```python
import asyncio
from services.midjourney_service import MidjourneyService

async def test_api_capabilities():
    service = MidjourneyService()

    # 1. 测试imagine
    print("Testing imagine...")
    result = await service.submit_imagine(prompt="test")
    task_info = await service.wait_for_completion(result)
    print(f"Buttons available: {[b['label'] for b in task_info.get('buttons', [])]}")

    # 2. 尝试不同的action payloads
    if task_info.get('buttons'):
        button = task_info['buttons'][0]
        custom_id = button['customId']

        # 尝试方式1
        try:
            await service.client.post("/mj/submit/action", json={"customId": custom_id})
        except:
            pass

        # 尝试方式2
        try:
            await service.client.post("/mj/action", json={"taskId": result, "customId": custom_id})
        except:
            pass

        # 尝试方式3
        try:
            await service.client.post(f"/mj/task/{result}/action", json={"customId": custom_id})
        except:
            pass

    await service.close()

asyncio.run(test_api_capabilities())
```

## 下一步

1. **短期**：使用四宫格，在后续处理中裁剪
2. **中期**：联系API提供商了解正确的upscale方式
3. **长期**：考虑切换到支持完整功能的API

## 相关配置

```bash
# 使用四宫格
MIDJOURNEY_AUTO_UPSCALE=false

# 如果将来找到支持upscale的方法
MIDJOURNEY_AUTO_UPSCALE=true
MIDJOURNEY_UPSCALE_INDEX=1  # 选择左上角的图
```

## 参考

- 当前使用的API: `https://api.kuai.host`
- Imagine endpoint: `/mj/submit/imagine` ✅ 工作正常
- Action endpoint: `/mj/submit/action` ❌ 返回400
- Fetch endpoint: `/mj/task/{id}/fetch` ✅ 工作正常
