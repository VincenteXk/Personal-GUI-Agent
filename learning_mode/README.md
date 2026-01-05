# GUI Agent用户行为学习与分析系统

## 系统概述

本系统是一个专为GUI Agent设计的用户行为学习与分析框架，能够在后台持续学习用户操作行为，通过多模态数据分析技术，将用户行为转化为结构化数据，最终为图数据库提供高质量的知识图谱数据。

系统采用"在线记录+离线分析"的工作模式，通过全局变量控制学习与分析的切换，确保在不影响用户体验的前提下，高效收集和分析用户行为数据。

## 项目结构

```
├── README.md                    # 项目说明文档
├── GUI_Agent_用户行为学习与分析系统.md  # 详细系统文档
├── config.json                  # 配置文件
├── unified_cli.py               # 统一命令行工具
├── demo_system.py               # 系统演示脚本
├── behavior_analyzer.py         # 行为数据收集和处理
├── vlm_analyzer.py              # VLM分析器
├── utils.py                     # 工具模块
├── error_handling.py            # 错误处理和日志记录模块
└── data/                        # 数据存储目录
    ├── raw/                     # 原始数据
    ├── screenshots/             # 截图文件
    ├── sessions/                # 结构化会话数据
    ├── processed/               # 分析结果
    └── index.json               # 会话索引文件
```

## 主要优化

1. **功能整合**：
   - `unified_cli.py` 整合了原有的数据收集和VLM分析功能
   - `demo_system.py` 专注于演示模式，展示完整工作流程；支持通过命令行参数控制各步骤跳过

2. **代码复用**：
   - `utils.py` 提供通用工具函数
   - `error_handling.py` 统一错误处理机制
   - `ConfigManager` 类统一配置管理

3. **配置简化**：
   - 统一的配置文件 `config.json`
   - 支持通过命令行参数覆盖配置

## 使用方法

### 1. 统一命令行工具

```bash
# 数据收集
python unified_cli.py collect --duration 300

# 启动后台学习模式
python unified_cli.py collect --background

# 停止后台学习模式
python unified_cli.py collect --stop-background

# 分析最新会话
python unified_cli.py analyze

# 查看最新会话数据
python unified_cli.py show
```

### 演示模式

```bash
# 完整演示（数据收集 -> 分析）
python demo_system.py --duration 120

# 跳过数据收集
python demo_system.py --skip-collection

# 跳过VLM分析
python demo_system.py --skip-analysis
```

## 配置说明

系统配置存储在 `config.json` 文件中：

```json
{
  "api_key": "your_api_key_here",
  "model": "glm-4.1v-thinking-flash",
  "output_dir": "data",
  "background_check_interval": 60,
  "analysis_interval": 300,
  "max_screenshots_per_analysis": 5,
  "log_level": "INFO"
}
```

## 更多信息

更多详细信息请参考 `GUI_Agent_用户行为学习与分析系统.md` 文档。