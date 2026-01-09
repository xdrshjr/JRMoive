# AI短剧自动化生成系统

基于Python和多Agent架构的AI短剧自动生成工具，通过统一的CLI界面管理项目和生成视频。

## 功能特性

- 🎬 自动剧本解析与分镜设计
- 🖼️ AI驱动的分镜图片生成（Nano Banana Pro）
- 🎥 图片到视频的智能转换（Veo3）
- ✂️ 自动视频合成与后期处理
- 👤 角色一致性参考图生成（支持加载/自动生成）
- 🔄 断点续传与错误恢复
- 📊 实时进度监控
- 🛠️ 统一CLI项目管理

## 系统架构

系统采用多Agent协作架构，主要包含以下组件：

- **剧本解析Agent**: 解析文本剧本，生成结构化分镜脚本
- **角色参考Agent**: 生成多视角角色参考图，确保角色一致性
- **图片生成Agent**: 调用Nano Banana Pro API生成分镜图片
- **视频生成Agent**: 调用Veo3 API将图片转换为视频片段
- **视频合成Agent**: 拼接视频片段并进行后期处理
- **主控Agent**: 协调所有Agent的执行，管理工作流状态

## 快速开始

### 1. 环境要求

- Python 3.9+
- FFmpeg 4.0+

### 2. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境 (Windows)
.\venv\Scripts\activate

# 激活虚拟环境 (macOS/Linux)
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置API密钥

复制`.env.example`为`.env`并填入你的API密钥：

```bash
cp .env.example .env
```

编辑`.env`文件，填入以下配置：

```bash
NANO_BANANA_API_KEY=your_nano_banana_api_key_here
VEO3_API_KEY=your_veo3_api_key_here
DOUBAO_API_KEY=your_doubao_api_key_here  # 可选，用于剧本优化
```

### 4. 使用CLI创建和生成项目

```bash
# 创建新项目
python cli.py init my_drama

# 编辑项目脚本和配置
# - 编辑 projects/my_drama/script.txt
# - 编辑 projects/my_drama/config.yaml

# 验证项目配置
python cli.py validate projects/my_drama

# 生成视频
python cli.py generate projects/my_drama

# 查看所有项目
python cli.py list
```

### 5. 高级用法

```bash
# 使用自定义脚本创建项目
python cli.py init my_drama --script examples/sample_scripts/programmer_day.txt

# 覆盖配置参数
python cli.py generate projects/my_drama --override video.fps=60

# 仅验证不生成
python cli.py generate projects/my_drama --dry-run

# 自定义输出文件名
python cli.py generate projects/my_drama --output my_video.mp4

# 调试模式
python cli.py generate projects/my_drama --log-level DEBUG
```

## 项目结构

```
ai-movie-agent-guide/
│
├── cli.py                           # 统一CLI入口
│
├── agents/                          # Agent模块
│   ├── base_agent.py               # Agent基类
│   ├── script_parser_agent.py      # 剧本解析Agent
│   ├── character_reference_agent.py # 角色参考图生成Agent
│   ├── image_generator_agent.py    # 图片生成Agent
│   ├── video_generator_agent.py    # 视频生成Agent
│   ├── video_composer_agent.py     # 视频合成Agent
│   └── orchestrator_agent.py       # 主控Agent
│
├── core/                            # 核心模块
│   ├── project_manager.py          # 项目管理器
│   ├── config_loader.py            # 配置加载器
│   ├── runner.py                   # 项目运行器
│   ├── validators.py               # 验证器
│   └── errors.py                   # 错误定义
│
├── services/                        # 服务层
│   ├── nano_banana_service.py      # Nano Banana API封装
│   ├── veo3_service.py             # Veo3 API封装
│   └── doubao_service.py           # 豆包API封装
│
├── utils/                           # 工具模块
│   ├── logger.py                   # 日志工具
│   ├── retry.py                    # 重试机制
│   ├── concurrency.py              # 并发控制
│   ├── checkpoint.py               # 断点管理
│   ├── progress_monitor.py         # 进度监控
│   └── video_utils.py              # 视频处理工具
│
├── config/                          # 配置模块
│   └── settings.py                 # 配置管理
│
├── models/                          # 数据模型
│   ├── script_models.py            # 剧本数据模型
│   └── config_models.py            # 配置数据模型
│
├── projects/                        # 项目目录
│   └── [project_name]/             # 单个项目
│       ├── config.yaml             # 项目配置
│       ├── script.txt              # 剧本文件
│       ├── characters/             # 角色参考图
│       └── outputs/                # 输出目录
│           ├── images/             # 生成的图片
│           ├── videos/             # 生成的视频片段
│           └── final/              # 最终视频
│
├── templates/                       # 项目模板
│   └── default/                    # 默认模板
│       └── config.yaml             # 模板配置
│
├── tests/                           # 测试模块
│   ├── test_agents/
│   ├── test_services/
│   └── test_integration/
│
├── examples/                        # 示例代码
│   └── sample_scripts/             # 示例剧本
│
├── .env                             # 环境变量（gitignore）
├── .env.example                     # 环境变量模板
├── .gitignore
├── requirements.txt                 # 依赖清单
├── CLAUDE.md                        # Claude Code项目指南
└── README.md                        # 项目说明
```

## CLI命令参考

### init - 创建新项目
```bash
python cli.py init <project_name> [options]

选项:
  --template TEMPLATE    使用指定模板 (默认: default)
  --script FILE          从文件复制剧本
  --description TEXT     项目描述
```

### generate - 生成视频
```bash
python cli.py generate <project_path> [options]

选项:
  --log-level LEVEL      日志级别 (DEBUG|INFO|WARNING|ERROR)
  --output FILENAME      自定义输出文件名
  --override KEY=VALUE   覆盖配置参数
  --dry-run              仅验证不生成
  --resume               从断点恢复
  --skip-characters      跳过角色参考图生成
```

### validate - 验证项目
```bash
python cli.py validate <project_path>
```

### list - 列出所有项目
```bash
python cli.py list
```

## 配置文件说明

项目配置文件 `config.yaml` 包含以下主要部分：

```yaml
# 项目元信息
title: "我的短剧"
description: "项目描述"

# 剧本配置
script:
  file: "script.txt"

# 图片生成配置
image:
  service: "nano_banana"
  model: "flux-dev"
  width: 1280
  height: 720
  max_concurrent: 3  # 图片生成最大并发数 (1-10)，推荐3-5

# 视频生成配置
video:
  service: "veo3"
  duration: 5
  fps: 24
  max_concurrent: 2  # 视频生成最大并发数 (1-5)，推荐2-3

# 角色一致性配置
characters:
  enable_references: true
  reference_images:
    角色名:
      mode: "generate"  # 或 "load"
      path: "characters/character.jpg"  # mode=load时使用

# 输出配置
output:
  filename: "output.mp4"
  format: "mp4"
```

### 并发配置优化

系统支持多线程并发生成图片和视频，可以显著提升生成速度：

- **image.max_concurrent**: 图片生成最大并发数
  - 范围: 1-10
  - 推荐值: 3-5
  - 说明: 值越大生成越快，但会增加API负载和内存占用

- **video.max_concurrent**: 视频生成最大并发数
  - 范围: 1-5
  - 推荐值: 2-3
  - 说明: 视频生成较慢，建议使用较低并发数

**示例**: 如果设置 `image.max_concurrent: 3` 和 `video.max_concurrent: 3`，系统将同时生成3张图片和3个视频，大幅提升整体生成速度。

## 剧本格式

剧本文件 `script.txt` 应遵循以下格式：

```
标题: 程序员的一天

场景1: 办公室 - 早晨
特写镜头
小明坐在电脑前，眼神疲惫，手指快速敲击键盘。
小明: "又是一个bug，这代码谁写的？"

场景2: 办公室 - 中午
中景镜头
小明和同事们围坐在一起吃外卖。
同事: "今天又要加班吗？"
小明: "项目deadline快到了，没办法。"
```

格式说明：
- 标题行：`标题: [剧名]`
- 场景行：`场景N: [地点] - [时间]`
- 镜头类型：特写镜头、中景镜头、远景镜头等
- 场景描述：描述场景中的动作和氛围
- 对话：`角色名: "对话内容"`

## 工作流程

1. **项目初始化**: 使用 `cli.py init` 创建项目结构
2. **编写剧本**: 在 `script.txt` 中编写剧本
3. **配置参数**: 在 `config.yaml` 中调整生成参数
4. **验证项目**: 使用 `cli.py validate` 检查配置
5. **生成视频**: 使用 `cli.py generate` 开始生成
   - 解析剧本 (0-10%)
   - 生成角色参考图 (10-15%)
   - 生成分镜图片 (15-40%)
   - 生成视频片段 (40-70%)
   - 合成最终视频 (70-100%)

## 成本提示

- Nano Banana Pro和Veo3都是按使用量计费的API服务
- 建议在正式使用前先阅读官方定价文档
- 开发阶段可使用较低分辨率和较短时长进行测试
- 预估成本：生成一个5分钟短剧约需调用API 20-30次

## 常见问题

### 如何跳过角色参考图生成？
```bash
python cli.py generate projects/my_drama --skip-characters
```

### 如何从断点恢复生成？
```bash
python cli.py generate projects/my_drama --resume
```

### 如何调整视频质量？
在 `config.yaml` 中修改：
```yaml
image:
  width: 1920  # 提高分辨率
  height: 1080
video:
  fps: 30  # 提高帧率
```

### 如何使用自己的角色参考图？
在 `config.yaml` 中配置：
```yaml
characters:
  enable_references: true
  reference_images:
    小明:
      mode: "load"
      path: "characters/xiaoming.jpg"
```

## 开发指南

### 运行测试
```bash
# 运行所有测试
python -m pytest

# 运行特定测试
python -m pytest tests/test_agents/test_image_video_generation.py -v

# 运行异步测试
python -m pytest tests/test_agents/test_script_parser.py -v
```

### 代码格式化
```bash
# 格式化代码
black .

# 代码检查
flake8

# 类型检查
mypy .
```

## 技术栈

- **Python 3.9+**: 核心语言
- **Pydantic**: 数据验证和配置管理
- **httpx/aiohttp**: 异步HTTP客户端
- **MoviePy**: 视频编辑
- **FFmpeg**: 视频处理
- **pytest**: 测试框架
- **loguru**: 日志管理

## 贡献指南

欢迎提交Issue和Pull Request！

开发流程：
1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 许可证

MIT License

## 联系方式

xdrshjr@gmail.com

如有问题或建议，请提交Issue。
