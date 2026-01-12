# PersonalUI - 个性化Android GUI Agent系统

## 📋 项目概述

PersonalUI 是一个基于 AutoGLM 框架的个性化 Android GUI agent 系统。系统通过两个核心模式为用户提供个性化的自动化操作体验：

1. **学习模式** - 从用户操作择机截图，将操作历史记录和截图的 VLM 语义理解一并生成 action-chain，再根据 action-chain 维护图数据库
2. **任务执行模式** - 接收用户语音或文本指令，基于 AutoGLM 架构执行相应操作，支持个性化和多agent协作

系统集成了用户行为观察、知识图谱存储、多agent协作和自动化执行等核心功能。

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目（包含 GraphRAG 子模块）
git clone --recursive https://github.com/VincenteXk/Personal-GUI-Agent.git
cd Personal-GUI-Agent

# 安装依赖
pip install -e .

# 验证安装
python -c "from task_framework import TaskAgentConfig; print('✓ Installation successful')"
```

### 2. 配置API和环境变量

根据不同的模型API，按以下方式配置：

#### 🔧 环境变量配置 (设置以下任意所需的API)

```bash
# AutoGLM Phone-9B 模型（本地部署或远程API）
export PHONE_MODEL_BASE_URL="http://localhost:8000/v1"
export PHONE_MODEL_API_KEY="EMPTY"  # 本地可为 EMPTY
export PHONE_MODEL_NAME="autoglm-phone-9b"

# 火山引擎 ARK（如果使用火山LLM服务）
export ARK_API_KEY="your_ark_api_key"
export ARK_BASE_URL="https://ark.cn-beijing.volces.com/api/v3"

# 小米 MIMO（如果使用小米LLM服务）
export MIMO_API_KEY="your_mimo_api_key"
export MIMO_BASE_URL="https://api.xiaomi.com/llm"
```

#### 📄 config.json 配置（放在项目根目录）

```json
{
  "model_config": {
    "base_url": "http://localhost:8000/v1",
    "model": "autoglm-phone-9b",
    "api_key": "EMPTY"
  },
  "agent_config": {
    "max_steps": 100,
    "device_id": null,
    "lang": "cn"
  },
  "learning_config": {
    "api_key": "your_deepseek_api_key",
    "model": "deepseek-chat",
    "output_dir": "data"
  },
  "graphrag_config": {
    "api_url": "http://localhost:8001"
  }
}
```

### 🔑 API 配置速查表

| API | 配置位置 | 说明 |
|-----|---------|------|
| **Phone-9B** | 环境变量 | AutoGLM模型，用于任务执行 |
| **DeepSeek** | config.json | 用于文本处理和指令优化 |
| **GLM-4V** (VLM) | config.json | 用于视觉理解和行为分析 |
| **火山 ARK** | 环境变量 | 可选，用于LLM推理 |
| **小米 MIMO** | 环境变量 | 可选，用于LLM推理 |

## 📁 项目结构

```
Personal-GUI-Agent/
├── main.py                         # v1版本主程序入口
├── demo_agent_v2.py               # v2版本主程序入口（推荐使用）
├── pyproject.toml                 # 项目配置和依赖
├── config.json                    # 运行时配置（需要创建）
├── README.md                      # 项目文档
│
├── src/                           # 源代码
│   ├── AutoGLM/                  # 自动化执行引擎
│   │   ├── agent.py              # PhoneAgent 主类
│   │   ├── device_factory.py     # 设备工厂
│   │   ├── voice.py              # 语音处理（ASR + TTS）
│   │   ├── adb/                  # ADB 设备控制
│   │   ├── actions/              # 动作执行处理
│   │   ├── model/                # AI 模型交互
│   │   └── config/               # 配置模块
│   │
│   ├── learning/                 # 用户行为学习
│   │   ├── behavior_analyzer.py  # 行为分析器
│   │   ├── vlm_analyzer.py       # VLM 视觉分析
│   │   └── utils.py              # 学习模块工具
│   │
│   ├── shared/                   # 共享模块
│   │   ├── config.py             # 应用配置和包名映射
│   │   └── utils.py              # 通用工具函数
│   │
│   └── core/                     # 核心集成模块（已清理）
│
├── task_framework/               # 任务调度框架 v2（推荐）
│   ├── agent_v2.py              # TaskAgentV2 核心实现
│   ├── integration.py            # 多agent集成
│   ├── config.py                 # 框架配置
│   ├── context.py                # 执行上下文
│   ├── interfaces/               # 接口定义
│   ├── implementations/          # 具体实现
│   │   ├── phone_task_executor.py
│   │   ├── profile_manager.py
│   │   ├── voice_input.py
│   │   ├── voice_interaction.py
│   │   └── ...
│   ├── subagents/               # 多个专业化agent
│   │   ├── onboarding_agent.py
│   │   ├── minimal_ask_agent.py
│   │   ├── plan_agent.py
│   │   ├── preference_update_agent.py
│   │   └── ...
│   ├── utils/                   # 框架工具
│   ├── prompts/                 # 提示词管理
│   └── actions/                 # 调度动作
│
├── tests/                        # 测试文件
│   ├── test_agent_v2_integration.py
│   ├── test_integrated_flow.py
│   ├── test_minimal_ask_agent.py
│   └── ...
│
├── data/                         # 数据存储目录
│   ├── sessions/                # 会话数据
│   ├── processed/               # 处理后数据
│   └── screenshots/             # 截图数据
│
└── graphrag/                     # 知识图谱模块（Git子模块）
    ├── simple_graphrag/         # SimpleGraphRAG 实现
    ├── backend/                 # GraphRAG API服务
    └── frontend/                # GraphRAG 可视化前端
```

## 🏗️ 核心架构

### 版本说明

- **v1 (main.py)**：基于 AutoGLM PhoneAgent 的直接调用
  - 支持学习模式和执行模式
  - 简单直接的任务执行
  - 适合简单场景

- **v2 (demo_agent_v2.py)** ⭐ **推荐**：基于 TaskAgentV2 的多agent框架
  - 4步工作流：归一化 → 规划 → 执行 → 偏好更新
  - 7个专业化subagents
  - 支持语音和文本交互
  - GraphRAG用户画像管理
  - 更强大的个性化能力

### 工作流程

```
用户输入（语音/文本）
    ↓
MinimalAskAgent（指令归一化和澄清）
    ↓
PlanGenerationAgent（任务规划）
    ↓
PhoneTaskExecutor（通过PhoneAgent执行）
    ↓
PreferenceUpdateAgent（学习和更新偏好）
    ↓
GraphRAG（存储用户知识）
```

## 💻 使用方法

### v2 版本（推荐）

```bash
# 启动 TaskAgentV2 演示
python demo_agent_v2.py

# 支持的交互方式
# - 文本输入: 直接输入任务描述
# - 语音输入: 使用麦克风进行语音交互
# - 终端交互: 支持多轮交互
```

### v1 版本

```bash
# 查看帮助
python main.py --help

# 执行任务
python main.py run "打开微信"

# 语音指令执行
python main.py run --voice

# 启动学习模式（收集用户行为 300 秒）
python main.py learn --duration 300
```

## 🎯 核心功能模块

### 1. TaskAgentV2（v2框架核心）

多agent框架，统一协调任务执行流程：
- **agent_v2.py**: 主协调器
- **integration.py**: 多agent集成层
- **subagents/**: 7个专业化agent

### 2. AutoGLM（自动化执行层）

- **PhoneAgent**: Android设备自动化的核心
- **ADB**: 低级设备操作
- **VoiceAssistant**: ASR + TTS 语音处理

### 3. 学习层（src/learning/）

- **BehaviorAnalyzer**: 收集和分析用户行为
- **VLMAnalyzer**: 使用视觉语言模型理解截图

### 4. GraphRAG（知识图谱）

Git子模块，用于存储和查询用户习惯和行为知识。

## ⚙️ 配置详解

### config.json 详细说明

```json
{
  "model_config": {
    "base_url": "http://localhost:8000/v1",    // Phone-9B API地址
    "model": "autoglm-phone-9b",               // 模型名称
    "api_key": "EMPTY"                          // API密钥（本地为EMPTY）
  },
  "agent_config": {
    "max_steps": 100,                          // 最大执行步数
    "device_id": null,                         // 设备ID（null=自动检测）
    "lang": "cn"                               // 语言：cn/en
  },
  "learning_config": {
    "api_key": "sk-...",                       // DeepSeek API密钥
    "model": "deepseek-chat",                  // DeepSeek模型
    "output_dir": "data"                       // 数据输出目录
  },
  "graphrag_config": {
    "api_url": "http://localhost:8001"        // GraphRAG API地址
  }
}
```

### 环境变量优先级

如果同时设置环境变量和config.json，优先级为：
1. 环境变量（最高）
2. config.json
3. 默认值（最低）

## 📋 系统要求

- **Python**: 3.11+
- **Android 设备**:
  - 已安装 ADB 工具
  - 已启用 USB 调试
  - 已安装 ADB Keyboard（用于文本输入）
- **API 服务**:
  - Phone-9B 模型（本地或远程）
  - DeepSeek API（可选，用于优化）
  - GLM-4V API（可选，用于视觉分析）
- **磁盘空间**: 用于存储会话数据和截图

## 🔧 故障排查

### 导入错误

```python
# 如果遇到导入错误，确保已安装项目
pip install -e .

# 验证环境
python -c "from task_framework import TaskAgentV2; print('OK')"
```

### API 连接失败

```bash
# 检查 Phone-9B 服务
curl http://localhost:8000/v1/models

# 检查 GraphRAG 服务
curl http://localhost:8001/health
```

### ADB 问题

```bash
# 检查 ADB 连接
adb devices

# 启用 USB 调试后重新连接
adb kill-server
adb start-server
```

## 📚 API 文档

### TaskAgentV2 基本使用

```python
from task_framework.agent_v2 import TaskAgentV2
from task_framework.implementations import TerminalUserInput, PhoneTaskExecutor

# 初始化
config = TaskAgentV2Config(...)
agent = TaskAgentV2(config)

# 执行任务
result = agent.run()
```

### PhoneAgent 基本使用

```python
from src.AutoGLM.agent import PhoneAgent

agent = PhoneAgent()
# 执行Android自动化任务
result = agent.run("打开微信")
```

## 📝 最近改进

### 代码清理 (v0.2.0)

✅ 删除了所有未使用的代码
- examples/ 目录（4个示例脚本）
- task_framework/agent.py（旧TaskAgent）
- src/core/refiner.py（未完成的指令优化器）
- 移除了~22个未使用的函数

✅ 简化了项目结构
- 统一了导入系统
- 清晰的v1/v2版本划分
- 保留了graphrag完整功能

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

基于 AutoGLM 框架开发，遵循相应的开源许可证。

## 📞 联系方式

如有问题，请通过以下方式联系：
- GitHub Issues
- 项目讨论区

## 更新日志

### v0.2.0 (代码清理版)
- 删除未使用的示例文件和函数
- 清理了~2800行无用代码
- 统一了v1和v2版本的管理
- 保留graphrag完整功能

### v0.1.0 (初始版本)
- TaskAgentV2 框架发布
- 多agent协作支持
- GraphRAG 集成
- 语音交互支持
