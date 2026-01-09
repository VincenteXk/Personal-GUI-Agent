# PersonalUI - 个性化GUI Agent系统

## 项目概述

PersonalUI 是一个基于 AutoGLM 框架的个性化 GUI agent 系统，专为 Android 设备设计。系统通过两个核心模式为用户提供个性化的自动化操作体验：

1. **学习模式** - 从用户操作择机截图，将操作历史记录和截图的 VLM 语义理解一并生成 action-chain，再根据 action-chain 维护图数据库
2. **任务执行模式** - 接收用户语音指令，基于 AutoGLM 架构执行相应操作

系统集成了用户行为观察、知识库存储、指令优化和自动化执行等核心功能。

## 📦 最新改进（v0.1.0）

项目已完成目录结构和导入系统的全面优化：

✅ **消除了所有 sys.path 操作** - 改用标准 Python 包导入
✅ **统一的目录结构** - 所有源代码在 `src/` 下，按功能分组
✅ **简化的包结构** - `AutoGLM/phone_agent/` → `src/AutoGLM/`
✅ **提取的公共工具** - `check_model_api()` 等函数统一到 `src/shared/`
✅ **清晰的包 API** - 每个模块通过 `__init__.py` 定义公共接口
✅ **统一的依赖管理** - 所有依赖在 `pyproject.toml` 中定义

**相关改动：**
- 41 个文件重组
- 16 处导入语句更新
- 5 处 sys.path 操作删除
- 94 个应用配置 (APP_PACKAGE_MAPPINGS)

## 项目结构

```
Personal-GUI-Agent/
├── main.py                    # 主程序入口
├── autoglm_cli.py             # AutoGLM CLI 工具
├── pyproject.toml             # 项目配置（统一的包管理）
├── config.json                # 运行时配置
├── README.md                  # 项目文档
├── .gitignore                 # Git忽略文件
│
├── src/                       # 所有源代码统一放在 src 目录下
│   ├── __init__.py
│   │
│   ├── shared/                # 共享模块
│   │   ├── __init__.py
│   │   ├── config.py          # 应用配置和包名映射
│   │   └── utils.py           # 通用工具函数
│   │
│   ├── AutoGLM/               # 自动化执行引擎（原 phone_agent）
│   │   ├── __init__.py        # 导出主要类和函数
│   │   ├── agent.py           # PhoneAgent 主类
│   │   ├── device_factory.py  # 设备工厂
│   │   ├── voice.py           # 语音处理模块
│   │   │
│   │   ├── adb/               # ADB 设备控制
│   │   │   ├── __init__.py
│   │   │   ├── connection.py  # ADB 连接管理
│   │   │   ├── device.py      # 设备控制命令
│   │   │   ├── input.py       # 输入处理
│   │   │   └── screenshot.py  # 截图功能
│   │   │
│   │   ├── actions/           # 动作执行处理
│   │   │   ├── __init__.py
│   │   │   └── handler.py     # 动作处理器
│   │   │
│   │   ├── model/             # AI 模型交互
│   │   │   ├── __init__.py
│   │   │   └── client.py      # 模型客户端
│   │   │
│   │   └── config/            # 配置模块
│   │       ├── __init__.py
│   │       ├── apps.py        # 应用包名配置
│   │       ├── i18n.py        # 国际化配置
│   │       ├── timing.py      # 时间相关配置
│   │       ├── prompts.py     # 通用提示词
│   │       ├── prompts_zh.py  # 中文提示词
│   │       └── prompts_en.py  # 英文提示词
│   │
│   ├── learning/              # 用户行为学习模块（原 learning_mode）
│   │   ├── __init__.py
│   │   ├── behavior_analyzer.py   # 行为分析器
│   │   ├── vlm_analyzer.py        # VLM 视觉分析
│   │   └── utils.py               # 学习模块工具函数
│   │
│   └── core/                  # 核心集成模块
│       ├── __init__.py
│       ├── observer.py        # 用户行为观察者
│       ├── refiner.py         # 指令优化器
│       └── knowledge_base.py  # 知识库（NetworkX 图数据库）
│
├── tests/                     # 测试文件
│   ├── __init__.py
│   ├── test_autoglm.py        # AutoGLM 测试
│   └── test_integration.py    # 集成测试（可选）
│
├── data/                      # 数据存储目录
│   ├── raw/                   # 原始数据
│   ├── sessions/              # 会话数据
│   ├── processed/             # 处理后数据
│   └── screenshots/           # 截图数据
│
└── graphrag/                  # 知识图谱存储模块（Git 子模块）
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

### 2. 用户观察者模块 (src/core/observer.py)

`observer.py` 实现了 `UserObserver` 类，用于监控用户行为并存储到知识库。主要功能：

- 启动学习循环
- 分析收集的数据
- 存储分析结果到知识库
### 3. 知识库模块 (src/core/knowledge_base.py)
已删除
### 4. 指令优化器模块 (src/core/refiner.py)

`refiner.py` 实现了 `InstructionRefiner` 类，用于优化用户指令。

### 5. 学习模式模块 (src/learning/)

学习模式模块负责从用户操作中学习并构建行为链，包含以下核心组件：

#### 5.1 行为分析器 (behavior_analyzer.py)

实现了数据收集、解析和处理功能，用于从 Android 设备收集用户行为数据。主要类：

- `ScreenshotCollector`: 截图收集器，负责在特定事件触发时捕获屏幕截图
- `DataCollector`: 数据收集器，负责从三个adb命令收集原始数据
- `BehaviorAnalyzer`: 行为分析器，负责分析收集的数据并构建行为链

#### 5.2 VLM 分析器 (vlm_analyzer.py)

使用视觉语言模型分析用户行为，包括截图和文本信息。主要类：

- `VLMAnalyzer`: VLM分析器，使用GLM-4.1V-Thinking-Flash模型分析用户行为链

#### 5.3 工具函数 (utils.py)

提供学习模块中使用的通用工具函数，包括：

- 文件操作工具
- 数据格式化工具
- 时间处理工具
- 异步事件循环管理等

### 6. 共享模块 (src/shared/)

共享配置和工具函数模块，为整个项目提供统一的接口：

#### 6.1 配置模块 (config.py)

- `APP_PACKAGE_MAPPINGS`: 应用包名映射（94个常用应用）
- `APP_NAME_TO_PACKAGE`: 应用名称到包名的反向映射
- `get_app_name_from_package()`: 通过包名获取应用名称
- `get_package_from_app_name()`: 通过应用名称获取包名

#### 6.2 工具函数 (utils.py)

- `check_model_api()`: 检查模型 API 是否可用
- 其他通用工具函数

### 7. AutoGLM 模块 (src/AutoGLM/)

简化后的 AutoGLM 框架，专为 Android 设备设计：

- **设备支持**：仅支持 Android 设备（通过 ADB）
- **核心功能**：设备连接、操作执行、模型交互
- **清晰的 API**：通过 `__init__.py` 导出主要类和函数

### 8. GraphRAG 模块 (graphrag/)

知识图谱存储和查询模块，用于维护用户行为的结构化知识图谱。

## 系统工作流程

1. **初始化阶段**：检查系统环境和模型 API 连接
2. **学习阶段**：收集用户行为，使用 VLM 分析
3. **优化阶段**：接收指令并优化
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

- **Python**：3.11 或更高版本（见 pyproject.toml）
- **Android 设备**：
  - 已安装 ADB 工具
  - 已启用 USB 调试
  - 已安装 ADB Keyboard（用于文本输入）
- **磁盘空间**：用于存储用户行为数据
- **模型API**：
  - AutoGLM 模型 API（用于任务执行）
  - GLM-4V 模型 API（用于行为分析）

## 配置说明

### 模型配置

在项目根目录创建 `config.json` 文件，配置模型 API 信息：

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
    "model": "glm-4v",
    "output_dir": "data"
  }
}
```

### 应用配置

应用配置存储在 [src/AutoGLM/config/apps.py](src/AutoGLM/config/apps.py) 中，包含常用应用的包名和启动方式。

## 依赖说明

### 主项目依赖

见 `pyproject.toml`：

```toml
dependencies = [
    "aiohttp>=3.13.2",
    "fastapi>=0.128.0",
    "pydantic>=2.12.5",
    "pyvis>=0.3.2",
    "pyyaml>=6.0.3",
    "uvicorn>=0.40.0",
    "volcengine-python-sdk[ark]>=4.0.43",
    "Pillow>=12.0.0",
    "openai>=2.9.0",
    "opencv-python>=4.8.0",
    "numpy>=1.24.0",
    "networkx>=3.0",
]
```

所有依赖统一管理，无需单独的 requirements.txt 文件。

## 开发指南

### 代码规范

1. 遵循 PEP 8 Python 代码风格指南
2. 使用类型提示提高代码可读性
3. 为公共 API 编写文档字符串
4. 为新功能编写单元测试

### 扩展开发

系统设计为模块化架构，可以方便地扩展：

1. **添加新的分析器**：在 `src/learning/` 下添加新的分析模块
2. **优化指令处理**：修改 `src/core/refiner.py` 添加新的优化策略
3. **扩展 GraphRAG**：在 `graphrag/simple_graphrag/src/` 下添加新模块
4. **添加新的工具函数**：在 `src/shared/utils.py` 中添加通用工具函数

## 注意事项

1. 首次使用前，请确保已正确安装 ADB 工具
2. 使用学习模式时，请确保 Android 设备已连接并授权调试
3. 分析用户行为数据需要配置有效的模型 API
4. 系统会收集用户行为数据，请注意隐私保护

## 许可证

本项目基于 AutoGLM 框架开发，遵循相应的开源许可证。