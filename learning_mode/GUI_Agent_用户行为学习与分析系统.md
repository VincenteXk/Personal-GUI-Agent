# GUI Agent用户行为学习与分析系统

## 系统概述

本系统是一个专为GUI Agent设计的用户行为学习与分析框架，能够在后台持续学习用户操作行为，通过多模态数据分析技术，将用户行为转化为结构化数据。

系统采用"在线记录+离线分析"的工作模式，通过全局变量控制学习与分析的切换，确保在不影响用户体验的前提下，高效收集和分析用户行为数据。

## 系统架构

### 核心组件

1. **行为数据收集器 (BehaviorAnalyzer)**
   - 负责从Android设备收集多源数据
   - 支持logcat日志、UI事件和窗口状态三种数据源
   - 集成截图收集功能，捕获用户交互关键时刻

2. **视觉语言模型分析器 (VLMAnalyzer)**
   - 使用GLM-4.1V-Thinking-Flash模型分析用户行为
   - 结合截图和文本数据，推理用户行为链
   - 输出结构化的行为分析结果

3. **数据处理器 (DataProcessor)**
   - 将原始数据转换为结构化格式
   - 提取用户交互事件序列
   - 生成适合VLM分析的会话数据

### 数据流程

```
Android设备 → 数据收集器 → 原始数据存储 → 数据处理器 → 结构化会话数据 → VLM分析器 → 行为分析结果
```

## 工作模式

### 在线学习模式

系统默认处于在线学习模式，特点如下：

- **持续数据收集**：通过三个并行线程持续收集logcat、UI事件和窗口状态数据
- **智能截图触发**：
  - 事件驱动：用户点击、输入、滑动等操作触发即时截图
  - 定时驱动：无交互30秒后自动截图，记录应用静态状态
- **全局变量控制**：通过`learning_active`全局变量控制学习状态
- **低资源占用**：优化数据收集频率，避免过度消耗设备资源

### 离线分析模式

当全局变量`learning_active`设置为False时，系统切换到离线分析模式：

- **停止数据收集**：终止所有数据收集线程
- **数据整理**：将收集的原始数据转换为结构化格式
- **VLM分析**：调用视觉语言模型分析用户行为
- **结果输出**：生成适合图数据库导入的结构化数据

## 核心功能

### 1. 多源数据收集

系统通过以下三个adb命令收集数据：

1. **logcat数据**：系统日志，包含应用启动、崩溃等信息
2. **uiautomator事件**：UI交互事件，如点击、滑动、文本输入等
3. **window状态**：当前焦点窗口信息，记录用户使用的应用

### 2. 智能截图管理

- **事件触发截图**：捕获用户交互关键时刻
- **定时截图**：记录应用静态状态
- **截图优化**：自动压缩大尺寸图片，确保高效传输和分析
- **文件管理**：按时间戳组织截图文件，便于后续分析

### 3. 行为链分析

VLM分析器能够：

- 识别用户使用的应用和主要行为
- 分析用户操作序列，推理行为意图
- 提取关键信息（如购物应用中的商品、金额等）
- 评估分析置信度，确保结果可靠性

### 4. 结构化数据输出

系统输出以下结构化数据：

```json
{
  "app_name": "应用名称",
  "main_action": "主要行为",
  "detailed_actions": ["详细行为列表"],
  "intent": "用户意图",
  "confidence": 0.95,
  "timestamp": "操作时间",
  "screenshot_references": ["相关截图文件路径"]
}
```

## 使用指南

### 初始化系统

```python
from behavior_analyzer import BehaviorAnalyzer

# 创建行为分析器实例
analyzer = BehaviorAnalyzer(output_dir="data")

# 设置全局变量控制学习状态
learning_active = True  # True为在线学习，False为离线分析
```

### 启动在线学习

```python
# 启动数据收集（学习模式）
analyzer.start_collection(duration_seconds=None)  # 持续收集直到全局变量改变

# 检查学习状态
while learning_active:
    time.sleep(1)
    # 可以在此处添加其他逻辑，如检查特定条件是否满足

# 停止数据收集
analyzer.stop_collection()
```

### 切换到离线分析

```python
# 设置全局变量为False，触发离线分析
learning_active = False

# 处理收集的数据
sessions = analyzer.process_collected_data()

# 使用VLM分析器分析最新会话
from vlm_analyzer import VLMAnalyzer

# 从配置文件加载API密钥
with open("config.json", "r") as f:
    config = json.load(f)
    api_key = config["api_key"]

vlm = VLMAnalyzer(api_key=api_key)
result = vlm.analyze_latest_session("data/processed")
```

### 命令行工具

系统提供统一的命令行工具：

1. **统一命令行工具 (unified_cli.py)**：
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

2. **演示脚本 (demo_system.py)**：
```bash
# 完整演示（数据收集 -> 分析）
python demo_system.py --duration 120

# 跳过数据收集
python demo_system.py --skip-collection

# 跳过VLM分析
python demo_system.py --skip-analysis
```

### 后台学习模式

系统支持后台学习模式，通过全局变量控制结束时机而非固定时间：

1. **启动后台学习模式**：
```bash
python unified_cli.py collect --background
```

2. **停止后台学习模式**：
```bash
python unified_cli.py collect --stop-background
```

3. **使用演示脚本**：
```bash
# 演示模式（完整工作流程）
python demo_system.py --duration 120
```

后台学习模式特点：
- 持续收集用户行为数据，不受固定时间限制
- 定期处理收集到的数据（默认每60秒）
- 通过全局变量`learning_active`控制结束时机
- 支持随时启动和停止，灵活性高

## 数据存储结构

```
data/
├── raw/                    # 原始数据
│   ├── logcat_*.log       # logcat日志
│   ├── uiautomator_*.log  # UI事件日志
│   └── window_*.log       # 窗口状态日志
├── screenshots/            # 截图文件
│   └── screenshot_*.png   # 时间戳命名的截图
├── sessions/              # 结构化会话数据
│   └── session_*.json     # 处理后的会话数据
└── processed/             # 分析结果
    ├── analysis/          # VLM分析结果
    └── screenshots/       # 处理后的截图
```

## 配置说明

系统配置存储在`config.json`文件中：

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

### 配置项说明

- `api_key`: 智谱AI API密钥，用于调用VLM模型
- `model`: 使用的视觉语言模型，默认为glm-4.1v-thinking-flash
- `output_dir`: 数据输出目录，默认为data
- `background_check_interval`: 后台模式检查间隔（秒），默认为60
- `analysis_interval`: 分析间隔（秒），默认为300
- `max_screenshots_per_analysis`: 每次分析的最大截图数量，默认为5
- `log_level`: 日志级别，默认为INFO

## 扩展与集成

### 自定义分析器

可以扩展VLM分析器，添加特定领域的分析逻辑：

```python
class CustomVLMAnalyzer(VLMAnalyzer):
    def custom_prompt_template(self, domain):
        if domain == "ecommerce":
            return """
            请分析以下电商应用的用户行为，特别关注：
            1. 浏览的商品类别
            2. 搜索的关键词
            3. 添加到购物车的商品
            4. 最终购买的商品和金额
            ...
            """
        # 其他领域的自定义提示词
```

### 自定义扩展

系统设计为模块化架构，支持以下扩展：

1. **自定义数据收集器**:
   - 继承`DataCollector`类
   - 实现特定应用或场景的数据收集逻辑

2. **自定义分析器**:
   - 继承`VLMAnalyzer`类
   - 实现特定领域的分析逻辑

3. **自定义数据处理器**:
   - 继承`DataProcessor`类
   - 实现特定格式的数据处理逻辑

## 性能优化

1. **数据收集优化**：
   - 调整截图间隔，平衡数据完整性和存储空间
   - 使用事件过滤，只记录关键交互事件
   - 实施数据压缩，减少存储需求

2. **VLM分析优化**：
   - 限制每次分析的截图数量，避免token超限
   - 实施截图预处理，提高分析准确性
   - 使用缓存机制，避免重复分析相似场景

## 注意事项

1. **权限要求**：
   - 需要Android设备开启USB调试
   - 确保adb命令可执行
   - 可能需要root权限获取完整日志

2. **隐私保护**：
   - 系统收集的数据可能包含敏感信息
   - 建议在分析前对数据进行脱敏处理
   - 确保符合相关隐私法规要求

3. **资源消耗**：
   - 长时间运行会消耗设备电量
   - 截图和数据收集会占用存储空间
   - VLM分析需要网络连接和API调用配额

## 未来扩展

1. **实时分析**：实现在线模式下的实时行为分析
2. **多设备支持**：扩展支持多个Android设备同时学习
3. **行为预测**：基于历史行为预测用户下一步操作
4. **个性化推荐**：结合分析结果提供个性化应用推荐
5. **异常检测**：识别异常用户行为，可能用于安全监控

## 总结

GUI Agent用户行为学习与分析系统提供了一个完整的解决方案，从数据收集到行为分析，最终生成结构化的用户行为数据。通过全局变量控制学习与分析的切换，系统能够灵活适应不同使用场景，为GUI Agent提供强大的用户行为理解能力。