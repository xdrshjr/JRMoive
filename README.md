# AI短剧自动化生成系统

基于Python和多Agent架构的AI短剧自动生成工具。

## 功能特性

- 🎬 自动剧本解析与分镜设计
- 🖼️ AI驱动的分镜图片生成（Nano Banana Pro）
- 🎥 图片到视频的智能转换（Veo3）
- ✂️ 自动视频合成与后期处理
- 🔄 断点续传与错误恢复
- 📊 实时进度监控

## 系统架构

系统采用多Agent协作架构，主要包含以下组件：

- **剧本解析Agent**: 解析文本剧本，生成结构化分镜脚本
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
```

### 4. 运行示例

```bash
# 运行完整工作流示例
python examples/complete_workflow_example.py

# 或运行图片视频生成示例
python examples/image_video_generation_example.py
```

## 项目结构

```
ai-drama-generator/
│
├── agents/                          # Agent模块
│   ├── base_agent.py               # Agent基类
│   ├── script_parser_agent.py      # 剧本解析Agent
│   ├── image_generator_agent.py    # 图片生成Agent
│   ├── video_generator_agent.py    # 视频生成Agent
│   ├── video_composer_agent.py     # 视频合成Agent
│   └── orchestrator_agent.py       # 主控Agent
│
├── services/                        # 服务层
│   ├── nano_banana_service.py      # Nano Banana API封装
│   ├── veo3_service.py             # Veo3 API封装
│   └── storage_service.py          # 文件存储服务
│
├── utils/                           # 工具模块
│   ├── logger.py                   # 日志工具
│   ├── retry.py                    # 重试机制
│   ├── validators.py               # 数据验证
│   └── video_utils.py              # 视频处理工具
│
├── config/                          # 配置模块
│   └── settings.py                 # 配置管理
│
├── models/                          # 数据模型
│   ├── script_models.py            # 剧本数据模型
│   ├── scene_models.py             # 场景数据模型
│   └── agent_models.py             # Agent通信模型
│
├── tests/                           # 测试模块
│   ├── test_agents/
│   ├── test_services/
│   └── test_integration/
│
├── examples/                        # 示例代码
│   └── sample_scripts/
│
├── docs/                            # 文档
│
├── .env                             # 环境变量（gitignore）
├── .env.example                     # 环境变量模板
├── .gitignore
├── requirements.txt                 # 依赖清单
└── README.md                        # 项目说明
```

## 开发状态

### TODO 1: 环境准备与项目架构搭建 ✅

- [x] 开发环境配置
- [x] 依赖包安装
- [x] 项目结构初始化
- [x] API密钥配置
- [x] 基础架构代码（BaseAgent、MessageBus、WorkflowStateManager、ErrorHandler）

### TODO 2: 剧本解析与数据模型模块 🚧

- [ ] 数据模型设计
- [ ] 剧本解析Agent实现
- [ ] 分镜设计优化
- [ ] 单元测试
- [ ] 示例剧本准备

### TODO 3: 图片生成与视频生成模块 ⏳

### TODO 4: 视频合成与后期处理模块 ⏳

### TODO 5: 测试、部署与文档完善 ⏳

## 技术栈

**核心技术**
- 编程语言: Python 3.9+
- 异步框架: asyncio、aiohttp
- 数据验证: Pydantic
- HTTP客户端: httpx

**视频处理**
- FFmpeg: 底层视频处理
- MoviePy: Python视频编辑
- Pillow: 图像处理

**AI服务集成**
- Nano Banana Pro: 图片生成API
- Veo3: 视频生成API

**测试与部署**
- pytest: 单元测试
- Docker: 容器化部署

## 文档

完整教程请参考[教程文档](./docs/)：

- [01-系统架构设计与环境准备](./docs/01-系统架构设计与环境准备.md)
- [02-核心代码实现-剧本解析与图片生成](./docs/02-核心代码实现-剧本解析与图片生成.md)
- [03-核心代码实现-视频生成与合成](./docs/03-核心代码实现-视频生成与合成.md)
- [04-使用示例与最佳实践](./docs/04-使用示例与最佳实践.md)
- [05-常见问题与项目部署](./docs/05-常见问题与项目部署.md)

## 成本提示

- Nano Banana Pro和Veo3都是按使用量计费的API服务
- 建议在正式使用前先阅读官方定价文档
- 开发阶段可使用较低分辨率和较短时长进行测试
- 预估成本：生成一个5分钟短剧约需调用API 20-30次

## 贡献指南

欢迎提交Issue和Pull Request！

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交Issue。
