# 角色一致性增强功能 - LLM评分系统

## 功能概述

为了提高生成视频中角色的一致性，系统新增了基于LLM的图片质量评分功能。该功能会为每个场景生成多张候选图片，然后使用LLM对比角色参考图和场景图，自动选择最符合角色特征的图片。

## 工作流程

```
1. 生成多个候选图片
   ├─ 场景1: 生成3张候选图片
   ├─ 场景2: 生成3张候选图片
   └─ ...

2. LLM评分
   ├─ 拼接参考图和候选图
   ├─ 调用Judge LLM进行评分
   └─ 评估角色一致性（面部、发型、服装等）

3. 选择最佳候选
   ├─ 根据评分选择最高分图片
   ├─ 删除其他候选图片（可配置）
   └─ 使用最佳图片进行视频生成
```

## 配置说明

### 1. 环境变量配置 (.env)

在 `.env` 文件中添加以下配置：

```bash
# Judge LLM配置（用于角色一致性评分）
JUDGE_LLM_API_KEY=your_judge_llm_api_key_here
JUDGE_LLM_API_URL=https://ark.cn-beijing.volces.com/api/v3
JUDGE_LLM_MODEL=doubao-seed-1-6-251015

# 是否启用角色一致性评分
ENABLE_CHARACTER_CONSISTENCY_JUDGE=true

# 每个场景生成的候选图片数量（1-5，建议3-5）
CANDIDATE_IMAGES_PER_SCENE=3

# Judge LLM温度参数（0.0-1.0，越低越稳定）
JUDGE_TEMPERATURE=0.3
```

### 2. 项目配置 (config.yaml)

在项目的 `config.yaml` 中添加：

```yaml
image:
  # ... 其他配置 ...

  # 角色一致性增强配置
  enable_character_consistency_judge: true  # 是否启用LLM评分
  candidate_images_per_scene: 3  # 每个场景生成的候选图片数量
  save_all_candidates: false  # 是否保存所有候选图片
```

## API要求

### 支持的LLM服务

目前支持火山引擎方舟API（兼容豆包模型）：

- **API URL**: `https://ark.cn-beijing.volces.com/api/v3`
- **推荐模型**: `doubao-seed-1-6-251015`（支持多模态输入）
- **API格式**: 火山引擎方舟 Responses API

### API调用示例

```python
import httpx

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

payload = {
    "model": "doubao-seed-1-6-251015",
    "input": [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_image",
                    "image_url": f"data:image/png;base64,{image_base64}"
                },
                {
                    "type": "input_text",
                    "text": "评分提示词"
                }
            ]
        }
    ],
    "temperature": 0.3
}

response = await client.post(
    f"{api_url}/responses",
    headers=headers,
    json=payload
)
```

## 评分标准

LLM会从以下5个方面评估角色一致性：

| 评分维度 | 权重 | 说明 |
|---------|------|------|
| 面部特征一致性 | 30分 | 五官、脸型、表情等是否与参考图一致 |
| 发型和发色一致性 | 20分 | 发型、发色、发长等是否与参考图一致 |
| 服装风格一致性 | 20分 | 服装款式、颜色、配饰等是否与参考图一致 |
| 整体气质一致性 | 15分 | 角色的整体气质、姿态是否与参考图一致 |
| 场景融合度 | 15分 | 角色是否自然地融入场景，没有违和感 |

**总分**: 0-100分

## 使用示例

### 基本使用

```python
from agents.image_generator_agent import ImageGenerationAgent
from models.script_models import Scene, Script

# 创建Agent（自动启用评分功能）
agent = ImageGenerationAgent(
    agent_id="image_gen",
    config={
        'enable_character_consistency_judge': True,
        'candidate_images_per_scene': 3,
        'save_all_candidates': False
    }
)

# 生成图片（自动进行多候选评分）
results = await agent.execute_concurrent(
    scenes=scenes,
    script=script,
    reference_data=reference_data
)

# 查看评分结果
for result in results:
    print(f"Scene: {result['scene_id']}")
    print(f"Score: {result['judge_score']}/100")
    print(f"Reasoning: {result['judge_reasoning']}")
    print(f"Selected: candidate {result['candidate_index']}/{result['total_candidates']}")
```

### 自定义评分服务

```python
from services.llm_judge_service import LLMJudgeService

# 创建自定义评分服务
judge_service = LLMJudgeService(
    api_key="your_api_key",
    api_url="https://custom.api.com",
    model="custom-model",
    temperature=0.2
)

# 单张图片评分
result = await judge_service.judge_character_consistency(
    reference_image_path=Path("reference.png"),
    scene_image_path=Path("scene.png"),
    scene_prompt="办公室场景，程序员在工作",
    character_name="小明"
)

print(f"Score: {result['score']}/100")
print(f"Reasoning: {result['reasoning']}")
```

### 批量评分

```python
# 批量评分多个候选图片
candidate_paths = [
    Path("candidate_0.png"),
    Path("candidate_1.png"),
    Path("candidate_2.png")
]

results = await judge_service.batch_judge(
    reference_image_path=Path("reference.png"),
    candidate_images=candidate_paths,
    scene_prompt="办公室场景",
    character_name="小明"
)

# 选择最佳候选
best = judge_service.select_best_candidate(results)
print(f"Best candidate: {best['candidate_index']} with score {best['score']}")
```

## 性能优化建议

### 1. 候选数量选择

- **候选数量越多，一致性越好，但耗时越长**
- 推荐配置：
  - 快速模式：`candidate_images_per_scene: 2`
  - 平衡模式：`candidate_images_per_scene: 3`（推荐）
  - 高质量模式：`candidate_images_per_scene: 5`

### 2. 并发控制

```yaml
image:
  max_concurrent: 3  # 控制并发生成数量
  candidate_images_per_scene: 3
```

- 如果 `max_concurrent=3`, `candidate_images_per_scene=3`
- 实际并发数 = `max_concurrent` × `candidate_images_per_scene` = 9
- 建议根据API限流调整

### 3. 成本优化

- **只对有角色的场景启用评分**：系统会自动检测场景是否有角色
- **保存候选图片**：设置 `save_all_candidates: true` 可保留所有候选供后续分析
- **禁用评分**：对于不重要的场景，可以在场景级别禁用评分

## 故障排查

### 1. Judge LLM初始化失败

**错误信息**: `Failed to initialize LLM judge service`

**解决方案**:
- 检查 `JUDGE_LLM_API_KEY` 是否正确配置
- 确认API URL可访问
- 查看日志获取详细错误信息

### 2. 评分失败返回0分

**可能原因**:
- API调用失败
- 响应格式解析错误
- 图片格式不支持

**解决方案**:
- 查看日志中的详细错误信息
- 检查网络连接
- 确认图片格式为PNG/JPEG

### 3. 所有候选分数相近

**可能原因**:
- 参考图质量不佳
- 场景提示词不够详细
- Judge LLM温度参数过高

**解决方案**:
- 提高参考图质量
- 优化场景提示词
- 降低 `JUDGE_TEMPERATURE` 参数（如0.1-0.3）

## 技术架构

### 核心组件

1. **ImageComparator** (`utils/image_comparison.py`)
   - 图片拼接工具
   - 支持水平/垂直拼接
   - Base64编码转换

2. **LLMJudgeService** (`services/llm_judge_service.py`)
   - LLM评分服务
   - 批量评分支持
   - 最佳候选选择

3. **ImageGenerationAgent** (`agents/image_generator_agent.py`)
   - 集成评分逻辑
   - 多候选生成
   - 自动选择最佳

### 数据流

```
Scene → ImageGenerationAgent
  ↓
  ├─ Generate Candidate 1 → Image 1
  ├─ Generate Candidate 2 → Image 2
  └─ Generate Candidate 3 → Image 3
  ↓
ImageComparator
  ├─ Stitch Reference + Image 1 → Comparison 1
  ├─ Stitch Reference + Image 2 → Comparison 2
  └─ Stitch Reference + Image 3 → Comparison 3
  ↓
LLMJudgeService
  ├─ Judge Comparison 1 → Score 1
  ├─ Judge Comparison 2 → Score 2
  └─ Judge Comparison 3 → Score 3
  ↓
Select Best (Score 2 = 90) → Image 2
  ↓
Video Generation
```

## 测试

运行测试：

```bash
# 运行所有角色一致性测试
python -m pytest tests/test_agents/test_character_consistency.py -v

# 运行特定测试
python -m pytest tests/test_agents/test_character_consistency.py::TestImageComparator -v
python -m pytest tests/test_agents/test_character_consistency.py::TestLLMJudgeService -v
```

## 常见问题

### Q: 评分功能会增加多少时间？

A: 假设单张图片生成需要10秒，LLM评分需要3秒：
- 不启用评分：10秒/场景
- 启用评分（3候选）：10×3 + 3×3 = 39秒/场景
- 增加约3-4倍时间，但角色一致性显著提升

### Q: 可以使用其他LLM服务吗？

A: 可以，需要修改 `LLMJudgeService` 中的 `_call_llm_api` 方法以适配不同的API格式。

### Q: 评分标准可以自定义吗？

A: 可以，修改 `LLMJudgeService._build_judge_prompt` 方法中的评分标准和权重。

### Q: 如何提高评分准确性？

A:
1. 使用高质量的角色参考图
2. 提供详细的场景提示词
3. 降低Judge LLM的温度参数
4. 增加候选图片数量

## 更新日志

### v1.0.0 (2026-01-08)
- ✅ 初始版本发布
- ✅ 支持多候选图片生成
- ✅ 集成LLM评分系统
- ✅ 自动选择最佳候选
- ✅ 完整的测试覆盖

## 贡献

欢迎提交Issue和Pull Request来改进这个功能！

## 许可证

与主项目保持一致
