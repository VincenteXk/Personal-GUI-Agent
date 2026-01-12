# PersonalUI - Personalized Android GUI Agent System

[中文](README.md) | [English](README_en.md)

## 📋 Project Overview

PersonalUI is a personalized Android GUI agent system based on the AutoGLM framework. The system provides users with personalized automated operation experiences through two core modes:

1. **Learning Mode** - Opportunistically captures screenshots from user operations, generates action-chains from operation history and VLM semantic understanding of screenshots, and maintains a knowledge graph based on action-chains
2. **Task Execution Mode** - Receives voice or text instructions from users, executes corresponding operations based on the AutoGLM architecture, and supports personalization and multi-agent collaboration

The system integrates core functionalities including user behavior observation, knowledge graph storage, multi-agent collaboration, and automated execution.

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Clone the project (with GraphRAG submodule)
git clone --recursive https://github.com/VincenteXk/Personal-GUI-Agent.git
cd Personal-GUI-Agent

# Install dependencies
pip install -e .

# Verify installation
python -c "from task_framework import TaskAgentConfig; print('✓ Installation successful')"
```

### 2. Configure APIs and Environment Variables

Configure according to different model APIs:

#### 🔧 Environment Variables (Set any required APIs)

```bash
# AutoGLM Phone-9B Model (Local deployment or remote API)
export PHONE_MODEL_BASE_URL="http://localhost:8000/v1"
export PHONE_MODEL_API_KEY="EMPTY"  # Can be EMPTY for local
export PHONE_MODEL_NAME="autoglm-phone-9b"

# Volcano Engine ARK (if using Volcano LLM service)
export ARK_API_KEY="your_ark_api_key"
export ARK_BASE_URL="https://ark.cn-beijing.volces.com/api/v3"

# Xiaomi MIMO (if using Xiaomi LLM service)
export MIMO_API_KEY="your_mimo_api_key"
export MIMO_BASE_URL="https://api.xiaomi.com/llm"
```

#### 📄 config.json Configuration (Place in project root)

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
    "lang": "en"
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

### 🔑 API Configuration Quick Reference

| API | Configuration Location | Description |
|-----|----------------------|-------------|
| **Phone-9B** | Environment Variables | AutoGLM model for task execution |
| **DeepSeek** | config.json | For text processing and instruction optimization |
| **GLM-4V** (VLM) | config.json | For visual understanding and behavior analysis |
| **Volcano ARK** | Environment Variables | Optional, for LLM inference |
| **Xiaomi MIMO** | Environment Variables | Optional, for LLM inference |

## 📁 Project Structure

```
Personal-GUI-Agent/
├── main.py                         # v1 main entry point
├── demo_agent_v2.py               # v2 main entry point (recommended)
├── pyproject.toml                 # Project configuration and dependencies
├── config.json                    # Runtime configuration (needs to be created)
├── README.md                      # Chinese documentation
├── README_en.md                   # English documentation
│
├── src/                           # Source code
│   ├── AutoGLM/                  # Automation execution engine
│   │   ├── agent.py              # PhoneAgent main class
│   │   ├── device_factory.py     # Device factory
│   │   ├── voice.py              # Voice processing (ASR + TTS)
│   │   ├── adb/                  # ADB device control
│   │   ├── actions/              # Action execution handlers
│   │   ├── model/                # AI model interaction
│   │   └── config/               # Configuration module
│   │
│   ├── learning/                 # User behavior learning
│   │   ├── behavior_analyzer.py  # Behavior analyzer
│   │   ├── vlm_analyzer.py       # VLM visual analysis
│   │   └── utils.py              # Learning module utilities
│   │
│   ├── shared/                   # Shared modules
│   │   ├── config.py             # App configuration and package mappings
│   │   └── utils.py              # Common utility functions
│   │
│   └── core/                     # Core integration module (cleaned up)
│
├── task_framework/               # Task scheduling framework v2 (recommended)
│   ├── agent_v2.py              # TaskAgentV2 core implementation
│   ├── integration.py            # Multi-agent integration
│   ├── config.py                 # Framework configuration
│   ├── context.py                # Execution context
│   ├── interfaces/               # Interface definitions
│   ├── implementations/          # Concrete implementations
│   │   ├── phone_task_executor.py
│   │   ├── profile_manager.py
│   │   ├── voice_input.py
│   │   ├── voice_interaction.py
│   │   └── ...
│   ├── subagents/               # Multiple specialized agents
│   │   ├── onboarding_agent.py
│   │   ├── minimal_ask_agent.py
│   │   ├── plan_agent.py
│   │   ├── preference_update_agent.py
│   │   └── ...
│   ├── utils/                   # Framework utilities
│   ├── prompts/                 # Prompt management
│   └── actions/                 # Scheduling actions
│
├── tests/                        # Test files
│   ├── test_agent_v2_integration.py
│   ├── test_integrated_flow.py
│   ├── test_minimal_ask_agent.py
│   └── ...
│
├── data/                         # Data storage directory
│   ├── sessions/                # Session data
│   ├── processed/               # Processed data
│   └── screenshots/             # Screenshot data
│
└── graphrag/                     # Knowledge graph module (Git submodule)
    ├── simple_graphrag/         # SimpleGraphRAG implementation
    ├── backend/                 # GraphRAG API service
    └── frontend/                # GraphRAG visualization frontend
```

## 🏗️ Core Architecture

### Version Description

- **v1 (main.py)**: Direct invocation based on AutoGLM PhoneAgent
  - Supports learning mode and execution mode
  - Simple and straightforward task execution
  - Suitable for simple scenarios

- **v2 (demo_agent_v2.py)** ⭐ **Recommended**: Multi-agent framework based on TaskAgentV2
  - 4-step workflow: Normalization → Planning → Execution → Preference Update
  - 7 specialized subagents
  - Supports voice and text interaction
  - GraphRAG user profile management
  - More powerful personalization capabilities

### Workflow

```
User Input (Voice/Text)
    ↓
MinimalAskAgent (Instruction normalization and clarification)
    ↓
PlanGenerationAgent (Task planning)
    ↓
PhoneTaskExecutor (Execution via PhoneAgent)
    ↓
PreferenceUpdateAgent (Learning and preference updates)
    ↓
GraphRAG (Knowledge storage)
```

## 💻 Usage

### v2 Version (Recommended)

```bash
# Launch TaskAgentV2 demo
python demo_agent_v2.py

# Supported interaction modes
# - Text input: Directly input task description
# - Voice input: Use microphone for voice interaction
# - Terminal interaction: Support multi-turn interaction
```

### v1 Version

```bash
# View help
python main.py --help

# Execute a task
python main.py run "Open WeChat"

# Voice instruction execution
python main.py run --voice

# Start learning mode (collect user behavior for 300 seconds)
python main.py learn --duration 300
```

## 🎯 Core Function Modules

### 1. TaskAgentV2 (v2 Framework Core)

Multi-agent framework that unifies task execution flow coordination:
- **agent_v2.py**: Main coordinator
- **integration.py**: Multi-agent integration layer
- **subagents/**: 7 specialized agents

### 2. AutoGLM (Automation Execution Layer)

- **PhoneAgent**: Core for Android device automation
- **ADB**: Low-level device operations
- **VoiceAssistant**: ASR + TTS voice processing

### 3. Learning Layer (src/learning/)

- **BehaviorAnalyzer**: Collects and analyzes user behavior
- **VLMAnalyzer**: Uses vision language models to understand screenshots

### 4. GraphRAG (Knowledge Graph)

Git submodule for storing and querying user habits and behavior knowledge.

## ⚙️ Configuration Details

### config.json Detailed Explanation

```json
{
  "model_config": {
    "base_url": "http://localhost:8000/v1",    // Phone-9B API address
    "model": "autoglm-phone-9b",               // Model name
    "api_key": "EMPTY"                          // API key (EMPTY for local)
  },
  "agent_config": {
    "max_steps": 100,                          // Maximum execution steps
    "device_id": null,                         // Device ID (null=auto-detect)
    "lang": "en"                               // Language: en/zh
  },
  "learning_config": {
    "api_key": "sk-...",                       // DeepSeek API key
    "model": "deepseek-chat",                  // DeepSeek model
    "output_dir": "data"                       // Data output directory
  },
  "graphrag_config": {
    "api_url": "http://localhost:8001"        // GraphRAG API address
  }
}
```

### Environment Variable Priority

If both environment variables and config.json are set, the priority is:
1. Environment Variables (Highest)
2. config.json
3. Default values (Lowest)

## 📋 System Requirements

- **Python**: 3.11+
- **Android Device**:
  - ADB tool installed
  - USB debugging enabled
  - ADB Keyboard installed (for text input)
- **API Services**:
  - Phone-9B model (local or remote)
  - DeepSeek API (optional, for optimization)
  - GLM-4V API (optional, for visual analysis)
- **Disk Space**: For storing session data and screenshots

## 🔧 Troubleshooting

### Import Errors

```python
# If you encounter import errors, ensure the project is installed
pip install -e .

# Verify environment
python -c "from task_framework import TaskAgentV2; print('OK')"
```

### API Connection Failed

```bash
# Check Phone-9B service
curl http://localhost:8000/v1/models

# Check GraphRAG service
curl http://localhost:8001/health
```

### ADB Issues

```bash
# Check ADB connection
adb devices

# Reconnect after enabling USB debugging
adb kill-server
adb start-server
```

## 📚 API Documentation

### TaskAgentV2 Basic Usage

```python
from task_framework.agent_v2 import TaskAgentV2
from task_framework.implementations import TerminalUserInput, PhoneTaskExecutor

# Initialize
config = TaskAgentV2Config(...)
agent = TaskAgentV2(config)

# Execute task
result = agent.run()
```

### PhoneAgent Basic Usage

```python
from src.AutoGLM.agent import PhoneAgent

agent = PhoneAgent()
# Execute Android automation task
result = agent.run("Open WeChat")
```

## 📝 Recent Improvements

### Code Cleanup (v0.2.0)

✅ Removed all unused code
- examples/ directory (4 example scripts)
- task_framework/agent.py (old TaskAgent)
- src/core/refiner.py (incomplete instruction optimizer)
- Removed ~22 unused functions

✅ Simplified project structure
- Unified import system
- Clear v1/v2 version distinction
- Retained complete graphrag functionality

## 🤝 Contributing Guidelines

We welcome Issues and Pull Requests!

## 📄 License

Developed based on the AutoGLM framework, following corresponding open source licenses.

## 📞 Contact

If you have any questions, please contact us through:
- GitHub Issues
- Project Discussions

## Changelog

### v0.2.0 (Code Cleanup Version)
- Removed unused example files and functions
- Cleaned up ~2800 lines of unused code
- Unified v1 and v2 version management
- Retained complete graphrag functionality

### v0.1.0 (Initial Version)
- TaskAgentV2 framework released
- Multi-agent collaboration support
- GraphRAG integration
- Voice interaction support
