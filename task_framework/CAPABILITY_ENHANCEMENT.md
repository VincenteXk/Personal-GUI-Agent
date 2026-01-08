# 执行器能力感知增强

## 🎯 优化目标

1. **重构 TaskExecutorInterface**：消除冗余方法，使用标准化的能力定义
2. **增强 TaskAgent**：让大模型能够感知可用执行器及其详细能力

## 📊 改进前后对比

### 旧设计的问题

```python
class TaskExecutorInterface:
    # 问题1: can_handle 和 get_supported_task_types 功能重复
    def can_handle(self, task_type: str) -> bool:
        pass
    
    def get_supported_task_types(self) -> list[str]:
        pass
    
    # 问题2: get_capabilities 返回的是非结构化字典
    def get_capabilities(self) -> dict[str, Any]:
        return {
            "name": "...",
            "supported_task_types": [...],  # 又一次重复定义！
            "features": [...],
            "limitations": [...],
        }
```

**主要问题**：

- ❌ 方法功能重复，维护困难
- ❌ 能力描述不够详细（缺少参数定义）
- ❌ 大模型不知道有哪些执行器可用
- ❌ 大模型不知道每个执行器需要什么参数

### 新设计的优势

```python
@dataclass
class TaskParameter:
    """任务参数定义 - 告诉大模型需要什么参数。"""
    name: str                    # 参数名
    description: str             # 参数描述（自然语言）
    required: bool = True        # 是否必需
    example: Optional[str] = None  # 示例值
    value_type: str = "string"   # 类型提示

@dataclass
class TaskCapability:
    """任务能力定义 - 描述一种可执行的任务类型。"""
    task_type: str               # 任务类型标识符
    name: str                    # 任务名称
    description: str             # 任务描述
    parameters: list[TaskParameter]  # 参数定义 ✨ 新增
    examples: list[dict]         # 使用示例
    limitations: list[str]       # 限制说明

class TaskExecutorInterface:
    # 核心方法：返回结构化的能力列表
    @abstractmethod
    def get_capabilities(self) -> list[TaskCapability]:
        pass
    
    # 默认实现：从 capabilities 自动派生
    def can_handle(self, task_type: str) -> bool:
        return task_type in self.get_supported_task_types()
    
    def get_supported_task_types(self) -> list[str]:
        return [cap.task_type for cap in self.get_capabilities()]
```

**改进点**：

- ✅ 单一数据源：所有信息从 `get_capabilities()` 派生
- ✅ 结构化定义：使用 dataclass，类型安全
- ✅ 参数详细说明：大模型知道需要传什么参数
- ✅ 自然语言描述：参数描述是"期望的自然语言描述是什么"

## 🔧 实现细节

### 1. TaskParameter - 参数定义

```python
TaskParameter(
    name="instruction",
    description="要执行的任务指令（自然语言描述你想让手机做什么）",
    required=True,
    example="打开微信，找到张三并发送消息'你好'",
    value_type="string",
)
```

**关键点**：

- `description` 是给大模型看的，说明这个参数应该填什么
- `example` 提供具体示例，帮助大模型理解
- `value_type` 只是提示，实际传递时统一为字符串

### 2. TaskCapability - 能力定义

```python
TaskCapability(
    task_type="phone_automation",
    name="手机自动化",
    description="执行手机上的通用自动化任务，如打开应用、操作界面、发送消息等",
    parameters=[
        TaskParameter(...),  # 定义所有参数
    ],
    examples=[
        {
            "description": "打开应用",
            "task_data": {"instruction": "打开微信"},
        },
    ],
    limitations=[
        "需要设备通过ADB/HDC连接",
        "执行过程不支持人工干预",
    ],
)
```

### 3. TaskAgent 增强 - 能力传递

#### 系统提示词增强

```python
def _build_system_prompt(self) -> str:
    """构建系统提示词，包含执行器能力信息。"""
    base_prompt = get_scheduler_system_prompt(self.config.language)
    
    if not self.task_executors:
        return base_prompt
    
    # 添加执行器能力说明
    executors_section = self._build_executors_capability_section()
    
    return f"""{base_prompt}

{executors_section}
"""
```

生成的执行器能力部分示例：

```
===========================================================================
## 📦 可用的任务执行器及其能力
===========================================================================

以下是当前可用的任务执行器及其详细能力。
在使用 DelegateTask 操作委托任务时，请根据任务需求选择合适的 task_type。

### ✨ 手机自动化 (task_type: `phone_automation`)

**描述**: 执行手机上的通用自动化任务，如打开应用、操作界面、发送消息等

**参数**:
  - `instruction` 【必需】: 要执行的任务指令（自然语言描述你想让手机做什么）
    示例: `打开微信，找到张三并发送消息'你好'`
  - `max_steps` 【可选】: 最大执行步骤数限制
    示例: `30`

**使用示例**:
  1. 打开应用
     ```
     schedule_do(action="DelegateTask", task_type="phone_automation",
         task_data={"instruction": "打开微信"})
     ```
  2. 发送消息
     ```
     schedule_do(action="DelegateTask", task_type="phone_automation",
         task_data={"instruction": "打开微信，找到张三，发送消息'你好'"})
     ```

**限制**:
  - 需要设备通过ADB/HDC连接
  - 执行过程不支持人工干预
  - 每次执行需要完整的自然语言指令
  - 无法处理需要人脸识别、指纹等生物认证的操作

------------------------------------------------------------------------
```

#### 感知阶段增强

```python
def _perceive_current_state(self) -> str:
    """感知当前任务状态，包含执行器状态摘要。"""
    # ... 其他感知信息
    
    executors_status = self._get_executors_status_summary()
    
    perception = f"""** 当前状态感知 **

状态: {state}
步骤: {step}

{executors_status}  # ← 每步都提醒大模型有哪些执行器可用

任务信息:
...
"""
```

输出示例：

```
✅ 可用执行器:
  - 手机自动化: `phone_automation`, `app_launch`, `send_message` 等5种
  - GraphRAG知识库查询: `graphrag_query`, `knowledge_search`, `entity_query` 等4种
```

## 📝 使用示例

### 定义新的执行器

```python
from task_framework.interfaces import (
    TaskExecutorInterface,
    ExecutionResult,
    TaskCapability,
    TaskParameter,
)

class MyCustomExecutor(TaskExecutorInterface):
    def get_capabilities(self) -> list[TaskCapability]:
        return [
            TaskCapability(
                task_type="my_task",
                name="我的自定义任务",
                description="执行自定义操作",
                parameters=[
                    TaskParameter(
                        name="target",
                        description="目标对象或资源",
                        required=True,
                        example="用户数据",
                    ),
                    TaskParameter(
                        name="action",
                        description="要执行的操作",
                        required=True,
                        example="分析",
                    ),
                ],
                examples=[
                    {
                        "description": "分析用户数据",
                        "task_data": {
                            "target": "用户数据",
                            "action": "分析"
                        },
                    },
                ],
                limitations=["需要数据库访问权限"],
            ),
        ]
    
    def execute_task(self, task_type, task_data, config):
        # 实现执行逻辑
        pass
    
    # can_handle 和 get_supported_task_types 不需要实现！
    # 父类会自动从 get_capabilities() 派生
```

### 使用 TaskAgent

```python
from task_framework import TaskAgent, TaskAgentConfig
from task_framework.implementations import (
    TerminalUserInput,
    TerminalUserInteraction,
    PhoneTaskExecutor,
    GraphRAGQueryExecutor,
)

# 创建执行器
phone_executor = PhoneTaskExecutor(model_config)
graphrag_executor = GraphRAGQueryExecutor()
custom_executor = MyCustomExecutor()

# 创建 Agent（自动感知所有执行器能力）
agent = TaskAgent(
    user_input=TerminalUserInput(),
    user_interaction=TerminalUserInteraction(),
    task_executors=[
        phone_executor,
        graphrag_executor,
        custom_executor,  # ← 新执行器自动被识别
    ],
    model_client=your_model_client,
    config=TaskAgentConfig(verbose=True),
)

# 大模型现在知道：
# 1. 有哪些执行器可用
# 2. 每个执行器支持哪些 task_type
# 3. 每个 task_type 需要什么参数
# 4. 参数的示例和描述

agent.run()
```

## 🎬 大模型如何使用

当用户说："查询我的购物偏好，然后打开淘宝"

**步骤1**：大模型看到系统提示词中有：

- GraphRAGQueryExecutor 支持 `graphrag_query`
- PhoneTaskExecutor 支持 `phone_automation`

**步骤2**：大模型决策查询知识库：

```python
schedule_do(
    action="DelegateTask",
    task_type="graphrag_query",  # 知道有这个类型
    task_data={
        "query": "用户的购物偏好",  # 知道需要 query 参数
        "query_type": "keyword",   # 知道可以指定查询类型
        "limit": 5
    }
)
```

**步骤3**：查询完成后，大模型决策打开应用：

```python
schedule_do(
    action="DelegateTask",
    task_type="phone_automation",  # 知道有这个类型
    task_data={
        "instruction": "打开淘宝"  # 知道需要 instruction 参数
    }
)
```

## ✨ 关键优势

### 1. 单一数据源

所有能力信息从 `get_capabilities()` 派生，避免不一致

### 2. 类型安全

使用 dataclass，编辑器有代码提示和类型检查

### 3. 自动发现

添加新执行器后，大模型自动知道其能力，无需修改提示词

### 4. 详细指导

参数描述告诉大模型"应该传什么样的自然语言描述"

### 5. 易于扩展

```python
# 添加新能力只需实现一个方法
def get_capabilities(self) -> list[TaskCapability]:
    return [...]  # 定义你的能力
```

## 🧪 测试

运行演示查看效果：

```bash
# 查看执行器能力定义
python examples/executor_capability_demo.py capabilities

# 查看 Agent 如何感知执行器
python examples/executor_capability_demo.py agent

# 查看感知阶段的执行器状态
python examples/executor_capability_demo.py perception

# 运行所有演示
python examples/executor_capability_demo.py
```

## 📚 相关文件

- `task_framework/interfaces/task_executor.py` - 接口定义
- `task_framework/agent.py` - Agent 增强实现
- `task_framework/implementations/phone_task_executor.py` - PhoneTaskExecutor 实现
- `task_framework/implementations/graphrag_query_executor.py` - GraphRAGQueryExecutor 实现
- `examples/executor_capability_demo.py` - 功能演示

## 🎯 总结

这次优化解决了两个核心问题：

1. **接口层面**：消除冗余，使用标准化的能力定义
2. **Agent层面**：让大模型完全感知执行器能力，做出正确决策

现在大模型不再需要"猜测"有哪些执行器可用，也不需要"记忆"每个执行器需要什么参数——所有信息都在系统提示词中清晰地呈现！
