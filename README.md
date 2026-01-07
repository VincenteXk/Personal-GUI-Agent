# PersonalUI - 个性化GUI Agent系统

## 项目概述

PersonalUI 是一个基于 AutoGLM 框架的个性化 GUI agent 系统，专为 Android 设备设计。系统通过两个核心模式为用户提供个性化的自动化操作体验：

1. **学习模式** - 从用户操作择机截图，将操作历史记录和截图的 VLM 语义理解一并生成 action-chain，再根据 action-chain 维护图数据库
2. **任务执行模式** - 接收用户语音指令，基于 AutoGLM 架构执行相应操作

系统集成了用户行为观察、知识库存储、指令优化和自动化执行等核心功能。

## 项目结构

```
personalUI/
├── main.py                    # 主程序入口
├── observer.py                # 用户观察者模块
├── knowledge_base.py          # 知识库模块
├── refiner.py                 # 指令优化器模块
├── README.md                  # 项目文档
├── config.json                # 配置文件
├── pyproject.toml             # 项目配置
├── .gitignore                 # Git忽略文件
├── Open-AutoGLM/              # AutoGLM框架（简化版，仅支持 Android）
│   ├── phone_agent/           # 手机自动化核心模块
│   │   ├── adb/               # ADB 连接模块（Android）
│   │   │   ├── connection.py  # ADB 连接
│   │   │   ├── device.py      # 设备管理
│   │   │   ├── input.py       # 输入处理
│   │   │   └── screenshot.py  # 截图功能
│   │   ├── model/             # 模型客户端
│   │   │   └── client.py      # 模型客户端实现
│   │   ├── actions/           # 动作处理模块
│   │   │   └── handler.py     # Android 动作处理器
│   │   ├── agent.py           # Android 手机代理
│   │   ├── device_factory.py  # 设备工厂（仅支持 ADB）
│   │   └── config/            # 配置模块
│   │       ├── apps.py        # Android 应用配置
│   │       ├── i18n.py        # 国际化配置
│   │       ├── prompts.py     # 提示词配置
│   │       ├── prompts_en.py  # 英文提示词
│   │       ├── prompts_zh.py  # 中文提示词
│   │       └── timing.py      # 时间配置
│   ├── main.py                # AutoGLM 主入口
│   ├── requirements.txt        # 依赖列表
│   └── setup.py               # 安装脚本
├── learning_mode/             # 用户行为学习模块
│   ├── __init__.py
│   ├── behavior_analyzer.py   # 行为分析器
│   ├── vlm_analyzer.py        # VLM 分析器
│   ├── utils.py               # 工具函数
│   └── data/                  # 数据存储目录
│       ├── raw/               # 原始数据
│       ├── sessions/          # 会话数据
│       ├── processed/         # 处理后数据
│       └── screenshots/       # 截图数据
└── graphrag/                  # 知识图谱存储模块
    ├── simple_graphrag/       # 简化版 GraphRAG 实现
    │   ├── src/               # 源代码
    │   ├── config/            # 配置目录
    │   ├── examples/          # 示例代码
    │   └── tests/             # 测试代码
    └── backend/               # 后端 API 服务
```

## 核心模块详解

### 1. 主程序 (main.py)

`main.py` 是整个系统的入口点，负责初始化各个模块并提供命令行界面。主要功能：

- 系统环境检查（ADB 工具安装、设备连接状态等）
- 模型 API 连接检查
- 用户交互处理
- 个性化自动化任务执行

### 2. 用户观察者模块 (observer.py)

`observer.py` 实现了 `UserObserver` 类，用于监控用户行为并存储到知识库。主要功能：

- 启动学习循环
- 分析收集的数据
- 存储分析结果到知识库

### 3. 知识库模块 (knowledge_base.py)

`knowledge_base.py` 使用 NetworkX 构建有向图存储用户交互数据。主要功能：

- 加载/保存知识库
- 添加用户交互数据
- 同步到 GraphRAG

### 4. 指令优化器模块 (refiner.py)

`refiner.py` 实现了 `InstructionRefiner` 类，使用知识库中的用户习惯优化指令。

### 5. 学习模式模块 (learning_mode/)

#### 5.1 行为分析器 (behavior_analyzer.py)

实现了数据收集、解析和处理功能，用于从 Android 设备收集用户行为数据。

#### 5.2 VLM 分析器 (vlm_analyzer.py)

使用视觉语言模型分析用户行为，包括截图和文本信息。

### 6. GraphRAG 模块 (graphrag/)

知识图谱存储和查询模块，用于维护用户行为的结构化知识图谱。

### 7. AutoGLM 框架 (Open-AutoGLM/)

简化后的 AutoGLM 框架，专为 Android 设备设计：

- **设备支持**：仅支持 Android 设备（通过 ADB）
- **移除支持**：iOS 和 HarmonyOS 相关代码已删除
- **核心功能**：设备连接、操作执行、模型交互

## 系统工作流程

1. **初始化阶段**：检查系统环境和模型 API 连接
2. **学习阶段**：收集用户行为，使用 VLM 分析，存储到知识库和 GraphRAG
3. **优化阶段**：接收指令并结合用户习惯优化
4. **执行阶段**：通过 ADB 在 Android 设备上执行操作
5. **反馈阶段**：记录执行结果和用户反馈

## 使用方法

### 基本使用

```bash
# 查看帮助
python main.py --help

# 检查系统环境
python main.py check

# 启动学习模式（收集用户行为 300 秒）
python main.py learn --duration 300

# 后台学习模式
python main.py learn --background

# 执行自动化任务
python main.py run "打开微信"

# 语音指令执行
python main.py run --voice

# 列出支持的应用
python main.py list-apps
```

### 设备管理命令

```bash
# 列出连接的 Android 设备
python main.py --list-devices

# 连接远程设备
python main.py --connect 192.168.1.100:5555

# 断开设备
python main.py --disconnect 192.168.1.100:5555

# 启用 TCP/IP 调试（设置端口）
python main.py --enable-tcpip 5555
```

## 系统要求

- **Python**：3.8 或更高版本
- **Android 设备**：
  - 已安装 ADB 工具
  - 已启用 USB 调试
  - 已安装 ADB Keyboard（用于文本输入）
- **磁盘空间**：用于存储用户行为数据

## 配置说明

### 模型配置

在 `config.json` 中配置模型 API 信息：

```json
{
  "model_config": {
    "base_url": "http://localhost:8000/v1",
    "model": "autoglm-phone-9b",
    "api_key": "your_api_key"
  },
  "agent_config": {
    "max_steps": 100,
    "device_id": null,
    "lang": "cn"
  },
  "learning_config": {
    "api_key": "your_glm_api_key",
    "model": "glm-4.1v-thinking-flash",
    "output_dir": "data"
  }
}
```

## 依赖说明

### 主项目依赖

见 `pyproject.toml`：

```toml
dependencies = [
    "aiohttp>=3.13.2",
    "fastapi>=0.128.0",
    "graphrag>=2.7.0",
    "pydantic>=2.12.5",
    "pyvis>=0.3.2",
    "pyyaml>=6.0.3",
    "uvicorn>=0.40.0",
    "volcengine-python-sdk[ark]>=4.0.43",
]
```

### Open-AutoGLM 依赖

见 `Open-AutoGLM/requirements.txt`：

```txt
Pillow>=12.0.0
openai>=2.9.0
requests>=2.31.0
```

### GraphRAG 依赖

见 `graphrag/simple_graphrag/requirements.txt`：

```txt
openai>=1.0.0
pyyaml>=6.0
networkx>=3.0
```

## 开发指南

### 代码规范

1. 遵循 PEP 8 Python 代码风格指南
2. 使用类型提示提高代码可读性
3. 为公共 API 编写文档字符串
4. 为新功能编写单元测试

### 扩展开发

系统设计为模块化架构，可以方便地扩展：

1. **添加新的分析器**：在 `learning_mode` 下添加新的分析模块
2. **扩展知识库**：修改 `knowledge_base.py` 添加新的数据结构
3. **优化指令处理**：修改 `refiner.py` 添加新的优化策略
4. **扩展 GraphRAG**：在 `graphrag/simple_graphrag/src/` 下添加新模块

## 注意事项

1. 首次使用前，请确保已正确安装 ADB 工具
2. 使用学习模式时，请确保 Android 设备已连接并授权调试
3. 分析用户行为数据需要配置有效的模型 API
4. 系统会收集用户行为数据，请注意隐私保护

## 许可证

本项目基于 AutoGLM 框架开发，遵循相应的开源许可证。
