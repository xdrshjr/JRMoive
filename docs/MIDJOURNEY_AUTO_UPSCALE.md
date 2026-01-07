# Midjourney自动Upscale功能说明

## 问题背景

Midjourney的imagine命令默认生成2x2的四宫格图片（4张变体），但在AI短剧生成场景中，我们需要的是单张完整的图片，而不是多宫格。

## 解决方案

系统现已实现**自动Upscale**功能，在生成四宫格后自动选择其中一张进行upscale，获得单张高清图片。

### 工作流程

1. **Step 1**: 提交imagine任务 → 生成2x2四宫格（4张变体）
2. **Step 2**: 等待imagine完成
3. **Step 3**: 自动提交upscale任务（选择U1-U4其中一张）
4. **Step 4**: 等待upscale完成 → 获得单张高清图

### 配置选项

在`.env`文件中添加以下配置：

```bash
# 是否自动upscale（获取单张图而非四宫格）
MIDJOURNEY_AUTO_UPSCALE=true  # true或false

# 选择upscale哪一张（1-4）
MIDJOURNEY_UPSCALE_INDEX=1  # 1=左上, 2=右上, 3=左下, 4=右下
```

### 位置对应关系

四宫格的编号：
```
+------+------+
|  U1  |  U2  |  ← 上排
+------+------+
|  U3  |  U4  |  ← 下排
+------+------+
   ↑      ↑
  左列   右列
```

## 使用方法

### 方法1: 使用默认配置（推荐）

配置文件设置后，无需修改代码：

```python
from services.midjourney_service import MidjourneyService

service = MidjourneyService()

# 自动使用配置中的auto_upscale和upscale_index
result = await service.generate_image(prompt="a beautiful landscape")

# 返回的是单张高清图
print(f"Is upscaled: {result['is_upscaled']}")  # True
print(f"Image URL: {result['image_url']}")  # 单张图的URL
```

### 方法2: 临时覆盖配置

```python
# 禁用自动upscale，获取四宫格
result = await service.generate_image(
    prompt="a beautiful landscape",
    auto_upscale=False  # 覆盖配置
)

# 或选择不同的upscale位置
result = await service.generate_image(
    prompt="a beautiful landscape",
    upscale_index=2  # 选择右上角的图
)
```

### 方法3: 在初始化时指定

```python
# 创建服务时指定默认行为
service = MidjourneyService(
    auto_upscale=True,
    upscale_index=1
)

# 后续调用都会使用这个配置
result = await service.generate_image(prompt="...")
```

## 返回结果

### Upscale后的结果

```python
{
    "task_id": "upscale_task_id",  # upscale任务的ID
    "original_task_id": "imagine_task_id",  # 原始四宫格任务的ID
    "image_url": "https://...",  # 单张高清图的URL
    "status": "SUCCESS",
    "progress": "100%",
    "prompt": "original prompt",
    "is_upscaled": True,  # 标识这是upscale后的图
    "upscale_index": 1,  # 使用的upscale索引
    "raw_response": {...}  # 完整的API响应
}
```

### 四宫格结果（auto_upscale=False）

```python
{
    "task_id": "imagine_task_id",
    "image_url": "https://...",  # 四宫格图片的URL
    "status": "SUCCESS",
    "progress": "100%",
    "prompt": "original prompt",
    "is_upscaled": False,  # 这是四宫格
    "raw_response": {...}
}
```

## 集成到工作流

### ImageGenerationAgent自动支持

`ImageGenerationAgent`会自动使用`MidjourneyService`的配置：

```python
from agents.image_generator_agent import ImageGenerationAgent

# 创建Agent（会自动读取.env中的MIDJOURNEY_AUTO_UPSCALE配置）
agent = ImageGenerationAgent(service_type="midjourney")

# 批量生成（每张都会自动upscale）
results = await agent.execute_concurrent(scenes)

# 所有结果都是单张高清图
for result in results:
    print(f"Scene: {result['scene_id']}")
    print(f"Image: {result['image_path']}")
    print(f"Is upscaled: {result.get('is_upscaled', False)}")
```

### CharacterReferenceAgent自动支持

角色参考图生成也会自动使用upscale：

```python
from agents.character_reference_agent import CharacterReferenceAgent

# 也会自动使用配置
agent = CharacterReferenceAgent(service_type="midjourney")

# 生成的角色参考图都是单张高清图
reference_data = await agent.execute(characters)
```

## 性能影响

### 时间成本

- **四宫格生成**: ~30-60秒
- **Upscale**: 额外~30-40秒
- **总计**: ~60-100秒/张

虽然时间增加了约50%，但质量显著提升。

### 质量对比

| 特性 | 四宫格 | Upscale单张 |
|------|--------|-------------|
| 分辨率 | ~1024x1024 | ~2048x2048 |
| 细节 | 中等 | 高 |
| 适用场景 | 快速预览 | 最终制作 |

## 注意事项

1. **API配额消耗**
   - 每次生成会消耗2次API调用（imagine + upscale）
   - 建议合理设置`max_concurrent`控制并发

2. **失败处理**
   - 如果upscale失败或按钮未找到，会自动降级返回四宫格
   - 不会中断整个流程

3. **索引选择**
   - 通常U1（左上）就是不错的选择
   - 如果对某些场景不满意，可以尝试其他索引

## 禁用自动Upscale

如果希望快速生成用于测试，可以临时禁用：

```bash
# 在.env中设置
MIDJOURNEY_AUTO_UPSCALE=false
```

或在代码中：

```python
result = await service.generate_image(
    prompt="test",
    auto_upscale=False
)
```

## 测试脚本

运行测试脚本验证功能：

```bash
python test_auto_upscale.py
```

这会：
1. 生成一张测试图片
2. 自动upscale
3. 下载并保存到`./output/test_upscale.png`
4. 显示完整的进度和结果

## 更新日志

### 2026-01-07
- ✅ 添加`submit_action`方法支持upscale操作
- ✅ 更新`generate_image`方法实现自动upscale
- ✅ 添加配置选项`MIDJOURNEY_AUTO_UPSCALE`和`MIDJOURNEY_UPSCALE_INDEX`
- ✅ 全流程自动支持（ImageGenerationAgent + CharacterReferenceAgent）
- ✅ 添加测试脚本`test_auto_upscale.py`

## 常见问题

**Q: 为什么要自动upscale？**
A: Midjourney的imagine默认生成四宫格，不适合直接用于视频制作，upscale后可获得单张高清图。

**Q: 可以选择不同位置的图片吗？**
A: 可以，通过`MIDJOURNEY_UPSCALE_INDEX`配置（1-4）或在代码中传递`upscale_index`参数。

**Q: 如果upscale失败会怎样？**
A: 系统会自动降级返回四宫格图片，不会中断流程。

**Q: 会增加多少成本？**
A: 每张图从1次API调用变成2次（imagine + upscale），时间增加约50%。

**Q: 可以关闭自动upscale吗？**
A: 可以，设置`MIDJOURNEY_AUTO_UPSCALE=false`或在代码中传递`auto_upscale=False`。
