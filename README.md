# PersonalUI - 个性化GUI Agent系统

## 项目概述

PersonalUI是一个基于AutoGLM框架的个性化GUI agent系统，旨在通过学习用户行为习惯，提供更加个性化的手机自动化操作体验。系统集成了多个核心模块，包括用户行为观察、知识库存储、指令优化和自动化执行等功能。

## 项目结构

```
personalUI/
├── main.py                 # 主程序入口
├── observer.py             # 用户观察者模块
├── knowledge_base.py       # 知识库模块
├── refiner.py             # 指令优化器模块
├── pyproject.toml         # 项目配置文件
├── .gitignore             # Git忽略文件
├── Open-AutoGLM/          # AutoGLM框架
│   ├── .github/           # GitHub模板和配置
│   ├── docs/              # 文档目录
│   ├── examples/          # 示例代码
│   ├── resources/         # 资源文件
│   ├── scripts/           # 脚本工具
│   ├── phone_agent/       # 手机自动化核心模块
│   │   ├── actions/       # 动作处理模块
│   │   │   ├── handler.py         # Android动作处理器
│   │   │   └── handler_ios.py     # iOS动作处理器
│   │   ├── adb/           # ADB连接模块
│   │   │   ├── connection.py      # ADB连接
│   │   │   ├── device.py          # 设备管理
│   │   │   ├── input.py           # 输入处理
│   │   │   └── screenshot.py      # 截图功能
│   │   ├── hdc/           # HDC连接模块
│   │   │   ├── connection.py      # HDC连接
│   │   │   ├── device.py          # 设备管理
│   │   │   ├── input.py           # 输入处理
│   │   │   └── screenshot.py      # 截图功能
│   │   ├── xctest/        # XCTest连接模块
│   │   │   ├── connection.py      # XCTest连接
│   │   │   ├── device.py          # 设备管理
│   │   │   ├── input.py           # 输入处理
│   │   │   └── screenshot.py      # 截图功能
│   │   ├── config/        # 配置模块
│   │   │   ├── apps.py            # Android应用配置
│   │   │   ├── apps_harmonyos.py  # HarmonyOS应用配置
│   │   │   ├── apps_ios.py        # iOS应用配置
│   │   │   ├── i18n.py            # 国际化配置
│   │   │   ├── prompts.py         # 提示词配置
│   │   │   ├── prompts_en.py      # 英文提示词
│   │   │   ├── prompts_zh.py      # 中文提示词
│   │   │   └── timing.py          # 时间配置
│   │   ├── model/         # 模型客户端模块
│   │   │   └── client.py          # 模型客户端
│   │   ├── agent.py       # Android手机代理
│   │   ├── agent_ios.py   # iOS手机代理
│   │   └── device_factory.py # 设备工厂
│   ├── ios.py             # iOS入口文件
│   ├── main.py            # 主入口文件
│   ├── requirements.txt   # 依赖列表
│   └── setup.py           # 安装脚本
├── learning_mode/         # 用户行为学习模块
│   ├── behavior_analyzer.py  # 行为分析器
│   ├── vlm_analyzer.py       # VLM分析器
│   ├── unified_cli.py        # 统一命令行工具
│   ├── utils.py              # 工具函数
│   ├── error_handling.py     # 错误处理
│   ├── demo_system.py        # 演示系统
│   ├── config.json           # 配置文件
│   └── data/                 # 数据存储目录
│       ├── index.json        # 数据索引
│       ├── raw/              # 原始数据
│       ├── processed/        # 处理后数据
│       │   ├── analysis/     # 分析结果
│       │   └── screenshots/  # 截图数据
│       ├── screenshots/      # 截图存储
│       └── sessions/         # 会话数据
└── graphrag/             # 知识图谱存储模块
    ├── simple_graphrag/  # 简化版GraphRAG实现
    │   ├── src/          # 源代码目录
    │   │   ├── builders/     # 构建器模块
    │   │   │   └── system_builder.py
    │   │   ├── combiners/    # 合并器模块
    │   │   │   ├── combiner.py
    │   │   │   └── smart_merger.py
    │   │   ├── database/     # 数据库模块
    │   │   │   └── manager.py
    │   │   ├── extractors/   # 提取器模块
    │   │   │   └── extractor.py
    │   │   ├── llm/          # LLM客户端模块
    │   │   │   └── client.py
    │   │   ├── models/       # 数据模型
    │   │   │   ├── delta.py
    │   │   │   ├── entity.py
    │   │   │   ├── graph.py
    │   │   │   ├── relationship.py
    │   │   │   └── task.py
    │   │   ├── pipeline/     # 管道模块
    │   │   │   └── async_pipeline.py
    │   │   ├── search/       # 搜索模块
    │   │   │   └── search_engine.py
    │   │   ├── updaters/     # 更新器模块
    │   │   │   └── system_updater.py
    │   │   └── utils/        # 工具模块
    │   │       └── logger.py
    │   ├── config/        # 配置目录
    │   │   ├── config.yaml   # 主配置文件
    │   │   └── prompts/      # 提示词模板
    │   │       ├── analyze_system.txt
    │   │       ├── build_system.txt
    │   │       ├── check_extraction.txt
    │   │       ├── extract_graph.txt
    │   │       ├── smart_merge.txt
    │   │       ├── summarize_descriptions.txt
    │   │       ├── system_core.txt
    │   │       ├── system_rules.txt
    │   │       ├── text_converter.txt
    │   │       └── validate_and_extend_system.txt
    │   ├── examples/      # 示例代码
    │   ├── tests/         # 测试代码
    │   ├── requirements.txt # 依赖列表
    │   └── pyproject.toml # 项目配置
    └── backend/          # 后端API服务
        ├── graph_service.py # 图服务
        ├── main.py         # 后端主入口
        ├── test_api.py     # API测试
        ├── API_DOCUMENTATION.md # API文档
        ├── QUICKSTART.md   # 快速开始
        └── SYSTEM_ENHANCEMENT_SUMMARY.md # 系统增强摘要
```

## 核心模块详解

### 1. 主程序 (main.py)

`main.py`是整个系统的入口点，负责初始化各个模块并提供命令行界面。主要功能包括：

- 系统环境检查（ADB/HDC/iOS工具安装、设备连接状态等）
- 模型API连接检查
- 用户交互处理
- 个性化自动化任务执行

主要类和函数：
- `check_system_requirements()`: 检查系统环境是否满足运行要求
- `check_model_api()`: 检查模型API是否可访问
- `main()`: 主函数，处理命令行参数并启动相应功能

### 2. 用户观察者模块 (observer.py)

`observer.py`实现了`UserObserver`类，用于监控用户行为并存储到知识库。主要功能包括：

- 启动学习循环（定时或连续模式）
- 分析收集的数据
- 存储分析结果到知识库

主要类和函数：
- `UserObserver`: 用户观察者类
  - `start_learning()`: 启动学习模式
  - `_analyze_collected_data()`: 分析收集的数据
  - `_store_analysis_result()`: 存储分析结果

### 3. 知识库模块 (knowledge_base.py)

`knowledge_base.py`实现了`KnowledgeBase`类，使用NetworkX构建有向图存储用户交互数据。主要功能包括：

- 初始化图结构
- 加载/保存知识库
- 添加用户交互数据到图节点和边
- 同步到GraphRAG

主要类和函数：
- `KnowledgeBase`: 知识库类
  - `add_interaction()`: 添加用户交互数据
  - `search_habits()`: 搜索相关习惯
  - `get_app_habits()`: 获取特定应用的习惯
  - `add_feedback()`: 添加反馈

### 4. 指令优化器模块 (refiner.py)

`refiner.py`实现了`InstructionRefiner`类，使用知识库中的用户习惯优化指令。主要功能包括：

- 从本地知识库和GraphRAG查询相关习惯
- 结合习惯优化指令
- 添加反馈用于优化未来的指令

主要类和函数：
- `InstructionRefiner`: 指令优化器类
  - `refine_task()`: 优化任务指令
  - `_combine_habits_with_task()`: 结合用户习惯优化任务指令
  - `add_feedback()`: 添加反馈

### 5. 学习模式模块 (learning_mode/)

`learning_mode`目录包含用户行为学习与分析相关的模块：

#### 5.1 行为分析器 (behavior_analyzer.py)

实现了`BehaviorAnalyzer`、`ScreenshotCollector`和`DataCollector`类，用于收集和分析用户行为数据：

- `ScreenshotCollector`: 截图收集器，负责在特定事件触发时捕获屏幕截图
- `DataCollector`: 数据收集器，负责从三个adb命令收集原始数据
- `DataParser`: 数据解析器，负责解析原始数据
- `BehaviorAnalyzer`: 行为分析器，整合数据收集和分析功能

#### 5.2 VLM分析器 (vlm_analyzer.py)

实现了`VLMAnalyzer`类，使用GLM-4.1V-Thinking-Flash模型分析用户行为：

- `encode_image_to_base64()`: 将图片编码为base64格式
- `analyze_session_with_screenshots()`: 分析会话数据中的截图和文本
- `analyze_latest_session()`: 分析最新的会话数据

#### 5.3 统一命令行工具 (unified_cli.py)

实现了`UnifiedCLI`和`ConfigManager`类，提供统一的命令行接口：

- `ConfigManager`: 统一配置管理
- `UnifiedCLI`: 统一命令行工具
  - `collect_data()`: 数据收集功能
  - `analyze_data()`: VLM分析功能
  - `show_latest_session()`: 显示最新会话数据

### 6. GraphRAG模块 (graphrag/)

`graphrag`目录包含知识图谱存储相关的模块：

#### 6.1 简化版GraphRAG (simple_graphrag/simplegraph.py)

实现了`SimpleGraph`类，提供知识图谱管理核心功能：

- 提交任务（submit_task）
- 取消任务（cancel_task）
- 查询任务状态（get_task_status）
- 保存和可视化（save, visualize）
- 统计信息（get_statistics）
- 进度追踪（set_progress_callback, get_task_progress）

### 7. AutoGLM框架 (Open-AutoGLM/)

`Open-AutoGLM`目录包含手机自动化框架的核心模块：

#### 7.1 手机代理 (phone_agent/agent.py, agent_ios.py)

- `PhoneAgent`: Android手机代理类，使用视觉语言模型理解屏幕内容并决定操作
- `IOSPhoneAgent`: iOS手机代理类，提供iOS设备的自动化操作

#### 7.2 动作处理 (phone_agent/actions/)

- `ActionHandler`: 动作处理器，负责执行各种手机操作
- `IOSActionHandler`: iOS动作处理器，专门处理iOS设备的操作

#### 7.3 设备连接 (phone_agent/adb/, hdc/, xctest/)

- ADB连接模块：提供Android设备的连接和操作
- HDC连接模块：提供HarmonyOS设备的连接和操作
- XCTest连接模块：提供iOS设备的连接和操作

#### 7.4 模型客户端 (phone_agent/model/)

- `ModelClient`: 模型客户端，负责与视觉语言模型交互
- `MessageBuilder`: 消息构建器，构建发送给模型的请求消息

## 系统工作流程

1. **初始化阶段**：
   - 检查系统环境（ADB/HDC/iOS工具、设备连接等）
   - 检查模型API连接
   - 初始化各个模块（观察者、知识库、指令优化器等）

2. **学习阶段**：
   - 启动用户观察者，收集用户行为数据
   - 使用行为分析器分析收集的数据
   - 使用VLM分析器分析截图和交互信息
   - 将分析结果存储到知识库和GraphRAG

3. **优化阶段**：
   - 接收用户指令
   - 使用指令优化器结合用户习惯优化指令
   - 将优化后的指令发送给手机代理执行

4. **执行阶段**：
   - 手机代理接收优化后的指令
   - 使用视觉语言模型理解屏幕内容
   - 执行相应操作完成任务
   - 收集执行结果和用户反馈

5. **反馈阶段**：
   - 将执行结果和用户反馈存储到知识库
   - 更新用户行为模型
   - 为未来的指令优化提供依据

## 使用方法

### 基本使用

```bash
# 启动系统
python main.py --help

# 检查系统环境
python main.py --check

# 启动学习模式
python main.py --learn

# 执行个性化任务
python main.py --task "打开微信发送消息给张三"
```

### 学习模式使用

```bash
# 收集用户行为数据
cd learning_mode
python unified_cli.py collect --duration 300

# 分析收集的数据
python unified_cli.py analyze

# 显示最新会话数据
python unified_cli.py show
```

### GraphRAG使用

```bash
# 启动GraphRAG服务
cd graphrag/backend
python main.py

# 使用GraphRAG API
python test_api.py
```

## 配置说明

### 模型配置

系统需要配置视觉语言模型的API信息，可以在`config.json`中设置：

```json
{
  "api_key": "your_api_key",
  "model": "glm-4.1v-thinking-flash",
  "base_url": "https://api.example.com/v1"
}
```

### 设备配置

根据使用的设备类型，可能需要配置以下信息：

- Android设备：ADB连接信息
- HarmonyOS设备：HDC连接信息
- iOS设备：WebDriverAgent URL

## 依赖说明

### 主项目依赖

主项目的依赖在`pyproject.toml`中定义：

```toml
dependencies = [
    "aiohttp>=3.13.2",      # 异步HTTP客户端
    "fastapi>=0.128.0",     # Web框架
    "graphrag>=2.7.0",      # 图检索增强生成
    "pydantic>=2.12.5",     # 数据验证
    "pyvis>=0.3.2",         # 图可视化
    "pyyaml>=6.0.3",        # YAML解析
    "uvicorn>=0.40.0",      # ASGI服务器
    "volcengine-python-sdk[ark]>=4.0.43",  # 火山引擎SDK
]
```

### Open-AutoGLM依赖

Open-AutoGLM模块的依赖在`requirements.txt`中定义：

```txt
Pillow>=12.0.0            # 图像处理
openai>=2.9.0             # OpenAI API客户端
requests>=2.31.0          # HTTP请求库
# 可选依赖
# sglang>=0.5.6.post1     # 模型部署
# vllm>=0.12.0            # 模型部署
# transformers>=5.0.0rc0  # Transformers库
```

### GraphRAG依赖

GraphRAG模块的依赖在`simple_graphrag/requirements.txt`中定义：

```txt
openai>=1.0.0             # OpenAI API客户端
pyyaml>=6.0                # YAML解析
networkx>=3.0             # 图处理库
```

## 系统要求

- Python 3.8+
- Android设备：ADB工具
- HarmonyOS设备：HDC工具
- iOS设备：libimobiledevice工具和WebDriverAgent
- 足够的磁盘空间用于存储用户行为数据

## 注意事项

1. 首次使用前，请确保已正确安装所需的系统工具
2. 使用学习模式时，请确保设备已连接并授权调试
3. 分析用户行为数据需要配置有效的模型API
4. 系统会收集用户行为数据，请注意隐私保护

## 扩展开发

系统设计为模块化架构，可以方便地扩展新功能：

1. **添加新的设备支持**：在`phone_agent`下添加新的连接模块
   - 创建新的设备连接目录（如`new_device/`）
   - 实现`connection.py`、`device.py`、`input.py`和`screenshot.py`
   - 在`device_factory.py`中添加设备识别和创建逻辑
   - 在`config/`目录下添加设备特定的配置文件

2. **实现新的分析器**：在`learning_mode`下添加新的分析器
   - 创建新的分析器文件（如`new_analyzer.py`）
   - 实现分析器类，继承基础分析器接口
   - 在`unified_cli.py`中添加新的命令行选项

3. **扩展知识库**：修改`knowledge_base.py`添加新的数据结构
   - 添加新的节点类型或边类型
   - 实现相应的查询和更新方法
   - 更新数据序列化和反序列化逻辑

4. **优化指令处理**：修改`refiner.py`添加新的优化策略
   - 实现新的优化算法
   - 添加新的提示词模板
   - 扩展反馈收集和处理机制

5. **扩展GraphRAG功能**：
   - 在`simple_graphrag/src/`下添加新的模块
   - 实现新的提取器、合并器或更新器
   - 在`config/prompts/`下添加新的提示词模板

6. **添加新的动作处理器**：
   - 在`phone_agent/actions/`下添加新的处理器
   - 实现特定平台或应用的动作处理逻辑
   - 在`agent.py`中注册新的动作处理器

## 开发指南

### 代码规范

1. 遵循PEP 8 Python代码风格指南
2. 使用类型提示提高代码可读性
3. 为公共API编写文档字符串
4. 为新功能编写单元测试

### 测试

1. 运行主项目测试：
   ```bash
   python -m pytest tests/
   ```

2. 运行Open-AutoGLM测试：
   ```bash
   cd Open-AutoGLM
   python -m pytest tests/
   ```

3. 运行GraphRAG测试：
   ```bash
   cd graphrag/simple_graphrag
   python -m pytest tests/
   ```

### 贡献流程

1. Fork项目仓库
2. 创建功能分支
3. 提交代码更改
4. 创建Pull Request
5. 等待代码审查

## 许可证

本项目基于AutoGLM框架开发，遵循相应的开源许可证。