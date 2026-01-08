# 任务调度框架 - 感知-思考-行动循环架构

## 概述

任务调度框架已从预定义工作流节点模式重构为**"感知-思考-行动"循环**架构，参照 `AutoGLM/phone_agent` 的设计理念，但专注于更高层次的任务调度。

## 架构对比

### 旧架构（已弃用）

- ❌ 预定义的工作流节点（WorkflowNode）
- ❌ 硬编码的状态转移逻辑
- ❌ 固定的决策路径

### 新架构（当前）

- ✅ 大模型驱动的决策循环
- ✅ 动态状态感知和路径规划
- ✅ 灵活的操作执行
- ✅ 丰富的历史记录

## 核心组件

### 1. TaskAgent（核心循环）

```python
from task_framework import TaskAgent, TaskAgentConfig
from task_framework.implementations import TerminalUserInput, TerminalUserInteraction

# 配置
config = TaskAgentConfig(
    max_steps=50,
    max_retries=3,
    verbose=True,
    language="zh",
)

# 创建Agent
agent = TaskAgent(
    user_input=TerminalUserInput(),
    user_interaction=TerminalUserInteraction(),
    model_client=your_model_client,  # 可选
    config=config,
)

# 运行
agent.run()
```

**核心循环**：

```
while not finished:
    # 感知：收集当前状态
    perception = perceive_current_state()

    # 思考：大模型决策
    decision = model.think(perception)

    # 行动：执行调度操作
    result = execute_action(decision)

    # 更新状态
    update_context(result)
```

### 2. 调度操作（Scheduler Actions）

任务调度 Agent 处理的是高层次操作，而非具体设备操作：

#### 用户交互类

- `AskUser`: 询问用户开放式问题
- `Confirm`: 请求确认（支持风险等级）
- `ShowInfo`: 显示信息
- `ShowPreview`: 显示计划预览
- `GetChoice`: 获取用户选择
- `RequestInfo`: 请求补充信息

#### 任务分析和规划类

- `AnalyzeTask`: 分析任务类型和关键信息
- `GeneratePlan`: 生成执行计划

#### 任务执行类

- `DelegateTask`: 委托任务给底层执行器（如 PhoneAgent）
- `CheckDevice`: 检查设备状态

#### 状态管理类

- `UpdateState`: 更新任务状态
- `RecordExecution`: 记录执行步骤
- `RequestTakeover`: 请求人工接管
- `UpdateProfile`: 更新用户画像

### 3. 上下文管理（TaskContext）

新的上下文结构支持完整的历史追踪：

```python
class TaskContext:
    # 状态信息
    state: TaskState
    task_info: TaskInfo
    execution_plan: ExecutionPlan

    # 历史记录
    execution_history: list[dict]      # 已执行的操作
    interaction_history: list[dict]    # 用户交互历史
    conversation_history: list[dict]   # 对话上下文（给大模型）

    # 辅助方法
    def get_context_summary() -> dict
    def get_recent_execution_summary() -> str
```

### 4. 系统提示词（Prompts）

完整的任务调度提示词，包括：

- 角色定义和职责
- 所有可用的调度操作说明
- 执行流程指导
- 重要规则

## 与 PhoneAgent 的对比

| 特性     | PhoneAgent                  | TaskAgent                         |
| -------- | --------------------------- | --------------------------------- |
| **层次** | 设备操作层                  | 任务调度层                        |
| **感知** | 屏幕截图 + 当前应用         | 任务状态 + 执行历史               |
| **操作** | Launch, Tap, Type, Swipe... | AskUser, DelegateTask, Confirm... |
| **目标** | 完成具体设备操作            | 任务规划和调度                    |
| **状态** | 通过对话历史维护            | 显式状态机 + 历史记录             |

## 典型任务流程

1. **接收任务** (RECEIVING_INPUT)

   - 用户输入任务描述

2. **分析任务** (NORMALIZING)

   - 使用 `AnalyzeTask` 识别任务类型
   - 提取关键信息和约束

3. **补充信息** (REQUESTING_INFO)

   - 如果缺少关键信息，使用 `RequestInfo` 或 `AskUser`

4. **检查设备** (CHECKING_DEVICE)

   - 使用 `CheckDevice` 检查设备状态

5. **生成计划** (PLANNING)

   - 使用 `GeneratePlan` 生成详细执行计划

6. **预览确认** (PREVIEWING)

   - 使用 `ShowPreview` 展示计划
   - 使用 `GetChoice` 让用户选择

7. **执行任务** (EXECUTING)

   - 使用 `DelegateTask` 委托给底层执行器
   - 使用 `RecordExecution` 记录关键步骤

8. **完成任务** (COMPLETED)
   - 显示结果
   - 可选：更新用户画像

## 状态机设计

采用**状态机代码模式**，而非预定义转移：

```python
class TaskState(Enum):
    IDLE = "idle"
    RECEIVING_INPUT = "receiving_input"
    NORMALIZING = "normalizing"
    REQUESTING_INFO = "requesting_info"
    CHECKING_DEVICE = "checking_device"
    PLANNING = "planning"
    PREVIEWING = "previewing"
    EXECUTING = "executing"
    CONFIRMING = "confirming"
    RETRY = "retry"
    TAKEOVER = "takeover"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

状态转移由大模型决策，而非硬编码规则。

## 使用模型客户端

如果要使用大模型进行决策：

```python
from phone_agent.model import ModelClient, ModelConfig

# 配置模型
model_config = ModelConfig(
    base_url="http://localhost:8000/v1",
    api_key="your-api-key",
    model_name="your-model",
)

model_client = ModelClient(model_config)

# 创建Agent时传入
agent = TaskAgent(
    user_input=...,
    user_interaction=...,
    model_client=model_client,  # 使用大模型决策
    config=config,
)
```

如果不提供 `model_client`，Agent 会使用简化的决策逻辑（基于状态机）。

## 扩展和定制

### 添加新的调度操作

1. 在 `actions/scheduler_actions.py` 中添加处理器：

```python
def _handle_your_action(self, action: dict) -> SchedulerActionResult:
    # 实现你的操作
    return SchedulerActionResult(
        success=True,
        should_finish=False,
        message="操作完成"
    )
```

2. 在 `_get_handler` 中注册：

```python
handlers = {
    ...
    "YourAction": self._handle_your_action,
}
```

3. 在 `prompts.py` 的系统提示词中添加操作说明。

### 自定义决策逻辑

可以继承 `TaskAgent` 并重写 `_request_model_decision` 或 `_fallback_decision`。

## 迁移指南

如果你有使用旧版工作流节点的代码：

1. **不再需要定义节点**：删除 `WorkflowNode` 和 `WorkflowEngine` 的使用

2. **改用操作**：将节点逻辑转换为调度操作

3. **利用大模型**：让模型决定流程，而非预定义转移

4. **丰富提示词**：通过系统提示词引导模型行为

## 示例代码

查看 `examples/task_scheduler_demo.py` 获取完整示例。

## 文件结构

```
task_framework/
├── __init__.py                 # 导出API
├── agent.py                    # TaskAgent核心实现
├── config.py                   # 配置
├── context.py                  # 上下文和状态管理
├── prompts.py                  # 系统提示词
├── actions/
│   ├── __init__.py
│   └── scheduler_actions.py   # 调度操作定义
├── interfaces/                 # 接口定义
│   ├── user_input.py
│   ├── user_interaction.py
│   ├── device_capability.py
│   ├── profile_manager.py
│   └── task_executor.py
├── implementations/            # 接口实现
│   ├── terminal_input.py
│   └── terminal_interaction.py
└── workflow/                   # 已弃用（保留兼容）
    ├── engine.py
    └── nodes.py
```

## 总结

新架构的优势：

- ✅ **灵活性**：大模型可以动态调整执行路径
- ✅ **可扩展**：轻松添加新操作
- ✅ **可追溯**：完整的历史记录
- ✅ **用户友好**：智能的交互决策
- ✅ **风险控制**：多层次的确认机制

适用场景：

- 复杂的多步骤任务
- 需要用户交互的任务
- 需要动态规划的任务
- 需要调度多个执行器的任务
