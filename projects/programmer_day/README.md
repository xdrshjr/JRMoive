# 程序员的一天

这是一个使用AI短剧生成系统创建的示例项目。

## 项目简介

讲述一个年轻程序员日常工作的温馨故事。

**作者**: AI编剧
**类型**: 日常温馨剧

## 角色

- **小明**: 25岁的Python开发者，戴黑框眼镜，清秀
- **小红**: 27岁的产品经理，长发，活泼

## 场景概览

1. **清晨的咖啡馆**: 阳光明媚的早晨，小明在咖啡馆享受清晨时光
2. **现代化办公室**: 忙碌的上午，小明专注于修复bug

## 如何生成

### 1. 确保API密钥已配置

在项目根目录的 `.env` 文件中配置以下API密钥：

```bash
DOUBAO_API_KEY=your_doubao_key_here
VEO3_API_KEY=your_veo3_key_here
```

### 2. 验证项目配置

```bash
python cli.py validate projects/programmer_day
```

### 3. 生成短剧视频

```bash
# 基础生成
python cli.py generate projects/programmer_day

# 使用DEBUG日志查看详细信息
python cli.py generate projects/programmer_day --log-level DEBUG

# 自定义视频帧率
python cli.py generate projects/programmer_day --override video.fps=60
```

## 项目配置亮点

本项目配置了以下特性：

- ✅ **角色一致性**: 启用角色参考图生成，确保小明和小红在不同场景中保持视觉一致
- ✅ **高质量图像**: 1920x1080分辨率，使用高质量模式
- ✅ **平滑转场**: 场景间使用淡入淡出效果
- ✅ **自动断点**: 启用断点保存，可以从中断处恢复

## 输出结构

生成完成后，输出文件将保存在 `outputs/` 目录：

```
outputs/
├── character_references/      # 角色参考图
│   ├── 小明_reference_sheet.png
│   └── 小红_reference_sheet.png
├── images/                    # 场景图像
│   ├── scene_1.png
│   └── scene_2.png
├── videos/                    # 场景视频
│   ├── scene_1.mp4
│   └── scene_2.mp4
├── final/                     # 最终视频
│   ├── programmer_day.mp4     # 主输出
│   └── programmer_day.json    # 元数据
└── generation.log             # 生成日志
```

## 自定义配置

你可以通过编辑 `config.yaml` 来自定义项目：

### 使用已有角色图片

如果你有小明或小红的参考图片，可以这样配置：

```yaml
characters:
  enable_references: true
  reference_images:
    小明:
      mode: "load"
      images:
        - "characters/xiaoming_reference.png"
    小红:
      mode: "generate"  # 小红仍然自动生成
```

### 添加背景音乐

将BGM文件放入项目文件夹，然后配置：

```yaml
composer:
  bgm:
    enabled: true
    file: "programmer_day_bgm.mp3"
    volume: 0.3
```

### 调整视频质量

```yaml
video:
  fps: 60                    # 提高帧率
  motion_strength: 0.8       # 增强运镜效果

composer:
  preset: "slow"             # 使用慢速预设提高编码质量
```

## 预期生成时间

根据配置和API响应速度，完整生成预计需要：

- 角色参考生成: 2-3分钟
- 场景图像生成: 2-4分钟 (2个场景)
- 视频生成: 3-5分钟 (2个场景)
- 视频合成: 30秒-1分钟

**总计**: 约8-13分钟

## 故障排除

### 问题：API调用失败
- 检查 `.env` 文件中的API密钥是否正确
- 确认API账户有足够的配额

### 问题：角色外观不一致
- 确保 `enable_references: true`
- 增加 `reference_weight` 到 0.8-0.9
- 使用 `single_multi_view` 模式

### 问题：生成中断
使用 `--resume` 标志从断点恢复：
```bash
python cli.py generate projects/programmer_day --resume
```

## 扩展想法

基于这个项目，你可以：

1. **增加场景**: 在 `script.txt` 中添加更多场景（午餐时间、下午茶、下班等）
2. **添加配音**: 配置TTS服务为对话添加语音
3. **加入BGM**: 选择合适的背景音乐营造氛围
4. **自定义角色**: 使用自己的角色设计图片

## 许可

本项目使用 AI Drama Generation System 创建，遵循项目主仓库的许可协议。
