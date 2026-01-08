# 任务调度 Agent 重构总结

## 重构目标

将任务调度框架从**预定义工作流节点模式**重构为**"感知-思考-行动"循环架构**，参照 `AutoGLM/phone_agent/agent.py` 的设计理念。

## 核心改动

### 1. 架构转变

#### 旧架构（已弃用）

```
用户输入 → 工作流引擎 → 执行预定义节点 → 硬编码的状态转移 → 下一个节点
```

特点：

- ❌ 固定的执行路径
- ❌ 硬编码的决策逻辑
- ❌ 难以动态调整

#### 新架构（当前）

```
while not finished:
    1. 感知阶段：收集当前状态、执行历史、交互历史
    2. 思考阶段：大模型分析状态，决定下一步操作
    3. 行动阶段：执行调度操作，更新上下文
```

特点：

- ✅ 大模型驱动的动态决策
- ✅ 灵活的路径规划
- ✅ 完整的历史记录

### 2. 与 PhoneAgent 的对应关系

| PhoneAgent (设备层)          | TaskAgent (调度层)                        |
| ---------------------------- | ----------------------------------------- |
| **感知**: 截屏 + 当前应用    | **感知**: 任务状态 + 执行历史             |
| **思考**: 决定设备操作       | **思考**: 决定调度操作                    |
| **行动**: Launch/Tap/Type... | **行动**: AskUser/DelegateTask/Confirm... |
| **目标**: 完成具体操作       | **目标**: 任务规划和调度                  |

### 3. 新增文件

```
task_framework/
├── actions/                          # 新增
│   ├── __init__.py
│   └── scheduler_actions.py         # 定义14种调度操作
├── prompts.py                       # 新增：系统提示词
├── README.md                        # 新增：完整文档
├── CHANGELOG.md                     # 新增：更新日志
└── REFACTORING_SUMMARY.md          # 本文件
```

### 4. 重写文件

#### `agent.py`

- 完全重写，采用感知-思考-行动循环
- 移除 `WorkflowEngine` 依赖
- 新增 `_execute_step()` 核心循环方法
- 新增 `_perceive_current_state()` 状态感知
- 新增 `_request_model_decision()` 模型决策
- 支持可选的 `model_client` 或 fallback 决策

#### `context.py`

- 新增 `conversation_history` - 对话上下文
- 新增 `get_context_summary()` - 上下文摘要
- 新增 `get_recent_execution_summary()` - 执行历史摘要
- 增强 `add_execution_record()` - 记录时间戳和状态
- 新增 `reset_for_new_task()` - 完整重置

#### `config.py`

- 新增 `model_base_url` - 模型 API 地址
- 新增 `model_api_key` - 模型密钥
- 新增 `model_name` - 模型名称
- 新增 `system_prompt` - 自定义提示词

#### `__init__.py`

- 更新导出 API
- 导出新的操作和提示词相关函数

## 详细设计

### 调度操作系统

定义了 14 种高层次操作，分为 4 类：

#### 1. 用户交互类（6 个）

- `AskUser`: 询问开放式问题
- `Confirm`: 请求确认，支持风险等级（low/medium/high）
- `ShowInfo`: 显示信息（info/success/warning/error）
- `ShowPreview`: 显示计划预览
- `GetChoice`: 获取用户选择（多选一）
- `RequestInfo`: 请求补充缺失字段

#### 2. 任务分析和规划类（2 个）

- `AnalyzeTask`: 记录任务分析结果（类型、关键信息、约束）
- `GeneratePlan`: 生成执行计划

#### 3. 任务执行类（2 个）

- `DelegateTask`: 委托任务给底层执行器（如 PhoneAgent）
- `CheckDevice`: 检查设备状态

#### 4. 状态管理类（4 个）

- `UpdateState`: 更新任务状态
- `RecordExecution`: 记录执行步骤
- `RequestTakeover`: 请求人工接管
- `UpdateProfile`: 更新用户画像

### 上下文管理增强

```python
@dataclass
class TaskContext:
    # 基本状态
    state: TaskState
    task_info: TaskInfo
    execution_plan: ExecutionPlan

    # 三种历史记录
    execution_history: list[dict]      # 操作+结果+时间+状态
    interaction_history: list[dict]    # 用户交互记录
    conversation_history: list[dict]   # 给大模型的对话历史

    # 辅助信息
    task_start_time: datetime
    last_action_result: Any
```

### 系统提示词设计

完整的中英文提示词，包含：

1. **角色定义**：任务调度专家
2. **职责说明**：5 大职责
3. **输出格式**：`<think>...</think><answer>...</answer>`
4. **操作说明**：每个操作的详细用法和参数
5. **执行流程**：8 步标准流程
6. **重要规则**：6 条关键规则
7. **上下文信息**：可访问的状态和历史

### 核心循环伪代码

```python
def _execute_step(self, user_prompt=None, is_first=False):
    # === 感知阶段 ===
    perception = self._perceive_current_state()
    # 包含：当前状态、步骤数、任务信息、执行历史等

    # === 思考阶段 ===
    if is_first:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{user_prompt}\n\n{perception}"}
        ]
    else:
        messages.append({"role": "user", "content": perception})

    response = model_client.request(messages)
    # 返回：{"thinking": "...", "action": "schedule_do(...)"}

    action = parse_scheduler_action(response["action"])

    # === 行动阶段 ===
    result = action_handler.execute(action)

    # 更新上下文
    context.add_conversation_message("assistant", response)
    if result.next_state:
        context.state = result.next_state

    return StepResult(
        success=result.success,
        finished=result.should_finish or is_completed,
        action=action,
        thinking=response["thinking"],
        message=result.message
    )
```

## 使用方式变化

### 旧用法（已弃用）

```python
# 创建工作流引擎
workflow_engine = WorkflowEngine()

# 添加节点
for node in create_main_flow_nodes():
    workflow_engine.add_node(node)

# 手动执行节点
next_node_id, result = workflow_engine.execute_node("A", context)
```

### 新用法（推荐）

```python
# 创建Agent
agent = TaskAgent(
    user_input=TerminalUserInput(),
    user_interaction=TerminalUserInteraction(),
    model_client=your_model_client,  # 可选
    config=TaskAgentConfig(verbose=True)
)

# 直接运行（自动循环）
agent.run()
```

## 兼容性说明

### 保留的组件

- `interfaces/` - 接口定义保持不变
- `implementations/` - 实现保持不变
- `context.py` 的基本数据结构（扩展了功能）
- `config.py` 的基本配置项（新增了模型相关）

### 弃用的组件

- `workflow/engine.py` - WorkflowEngine
- `workflow/nodes.py` - WorkflowNode 相关

这些文件保留以便兼容，但不再使用。

## 扩展性

### 添加新操作

1. 在 `scheduler_actions.py` 中添加处理函数：

```python
def _handle_my_action(self, action: dict) -> SchedulerActionResult:
    # 实现逻辑
    pass
```

2. 在 `_get_handler` 中注册
3. 在 `prompts.py` 中添加操作说明

### 自定义决策

两种方式：

1. **提供 model_client**：

```python
agent = TaskAgent(model_client=YourModelClient(), ...)
```

2. **重写 fallback_decision**：

```python
class CustomTaskAgent(TaskAgent):
    def _fallback_decision(self) -> dict[str, str]:
        # 自定义决策逻辑
        pass
```

## 测试建议

1. **单元测试**：

   - 测试每个操作处理器
   - 测试上下文管理功能
   - 测试动作解析

2. **集成测试**：

   - 测试完整的任务执行流程
   - 测试不同状态的转移
   - 测试历史记录功能

3. **端到端测试**：
   - 使用 mock model_client 测试完整循环
   - 测试实际任务场景

## 文档

- `README.md` - 完整的架构说明和使用指南
- `CHANGELOG.md` - 版本更新日志
- `examples/task_scheduler_demo.py` - 使用示例

## 总结

本次重构实现了从静态工作流到动态决策循环的转变：

**关键优势**：

1. ✅ **灵活性**：大模型可根据实际情况动态调整路径
2. ✅ **可扩展性**：轻松添加新的调度操作
3. ✅ **可追溯性**：完整的执行历史和交互历史
4. ✅ **智能化**：AI 驱动的决策，而非硬编码规则
5. ✅ **用户友好**：智能的交互决策和风险控制

**适用场景**：

- 复杂的多步骤任务
- 需要动态规划的任务
- 需要频繁用户交互的任务
- 需要调度多个执行器的任务

**下一步**：

- 集成真实的大模型客户端
- 添加更多的调度操作
- 完善错误处理和重试机制
- 添加任务执行的可视化
