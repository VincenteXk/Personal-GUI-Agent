# TaskAgent 执行器能力感知优化总结

## 🎯 优化目标

1. **重构 TaskExecutorInterface**：消除 `can_handle` 和 `get_supported_task_types` 的冗余定义
2. **标准化能力定义**：支持详细的参数定义（名称、描述、类型、示例）
3. **增强 TaskAgent**：将执行器能力信息传递给大模型

## ✅ 完成的改进

### 1. 新增数据结构

#### TaskParameter - 参数定义

```python
@dataclass
class TaskParameter:
    name: str           # 参数名
    description: str    # 自然语言描述（告诉大模型这个参数是什么）
    required: bool      # 是否必需
    example: str        # 示例值
    value_type: str     # 类型提示（string/number/boolean等）
```

#### TaskCapability - 能力定义

```python
@dataclass
class TaskCapability:
    task_type: str                      # 任务类型标识符
    name: str                           # 任务名称
    description: str                    # 任务描述
    parameters: list[TaskParameter]     # 参数定义列表
    examples: list[dict]                # 使用示例
    limitations: list[str]              # 限制说明
```

### 2. 优化 TaskExecutorInterface

**改动前**：

```python
class TaskExecutorInterface(ABC):
    @abstractmethod
    def can_handle(self, task_type: str) -> bool:
        pass  # 需要每个子类实现
    
    @abstractmethod
    def get_supported_task_types(self) -> list[str]:
        pass  # 需要每个子类实现，功能重复！
    
    @abstractmethod
    def get_capabilities(self) -> dict[str, Any]:
        pass  # 返回非结构化字典
```

**改动后**：

```python
class TaskExecutorInterface(ABC):
    @abstractmethod
    def get_capabilities(self) -> list[TaskCapability]:
        """核心方法：返回结构化的能力列表。"""
        pass
    
    def can_handle(self, task_type: str) -> bool:
        """默认实现：自动从 capabilities 派生。"""
        return task_type in self.get_supported_task_types()
    
    def get_supported_task_types(self) -> list[str]:
        """默认实现：自动从 capabilities 派生。"""
        return [cap.task_type for cap in self.get_capabilities()]
    
    def get_capability_by_type(self, task_type: str) -> Optional[TaskCapability]:
        """辅助方法：根据类型获取能力定义。"""
        for cap in self.get_capabilities():
            if cap.task_type == task_type:
                return cap
        return None
```

**关键改进**：

- ✅ 单一数据源：所有信息从 `get_capabilities()` 派生
- ✅ 消除冗余：`can_handle` 和 `get_supported_task_types` 由父类提供默认实现
- ✅ 结构化返回：使用 `TaskCapability` 代替 `dict`

### 3. 更新执行器实现

#### PhoneTaskExecutor

```python
def get_capabilities(self) -> list[TaskCapability]:
    return [
        TaskCapability(
            task_type="phone_automation",
            name="手机自动化",
            description="执行手机上的通用自动化任务...",
            parameters=[
                TaskParameter(
                    name="instruction",
                    description="要执行的任务指令（自然语言描述你想让手机做什么）",
                    required=True,
                    example="打开微信，找到张三并发送消息'你好'",
                    value_type="string",
                ),
                TaskParameter(
                    name="max_steps",
                    description="最大执行步骤数限制",
                    required=False,
                    example="30",
                    value_type="number",
                ),
            ],
            examples=[...],
            limitations=[...],
        ),
        # ... 其他5种任务类型
    ]

# 不再需要实现 can_handle 和 get_supported_task_types！
```

#### GraphRAGQueryExecutor

类似更新，定义了 4 种任务类型，每个都有详细的参数说明。

### 4. 增强 TaskAgent

#### 系统提示词增强

新增方法：

```python
def _build_system_prompt(self) -> str:
    """构建系统提示词，包含执行器能力信息。"""
    base_prompt = get_scheduler_system_prompt(self.config.language)
    
    if not self.task_executors:
        return base_prompt
    
    # 添加执行器能力说明
    executors_section = self._build_executors_capability_section()
    
    return f"{base_prompt}\n\n{executors_section}"

def _build_executors_capability_section(self) -> str:
    """构建执行器能力说明部分。"""
    # 遍历所有执行器的所有能力
    # 生成详细的说明文档
    # 包括：task_type、参数、示例、限制
```

生成的系统提示词示例：

```
[基础提示词内容...]

===========================================================================
## 📦 可用的任务执行器及其能力
===========================================================================

### ✨ 手机自动化 (task_type: `phone_automation`)

**描述**: 执行手机上的通用自动化任务...

**参数**:
  - `instruction` 【必需】: 要执行的任务指令（自然语言描述...）
    示例: `打开微信，找到张三并发送消息'你好'`
  - `max_steps` 【可选】: 最大执行步骤数限制
    示例: `30`

**使用示例**:
  1. 打开应用
     ```
     schedule_do(action="DelegateTask", task_type="phone_automation",
         task_data={"instruction": "打开微信"})
     ```
  [...]

**限制**:
  - 需要设备通过ADB/HDC连接
  [...]
```

#### 感知阶段增强

新增/修改方法：

```python
def _perceive_current_state(self) -> str:
    """感知当前任务状态，包含执行器状态摘要。"""
    # ... 基本感知信息
    
    # 添加执行器状态摘要
    executors_status = self._get_executors_status_summary()
    
    perception = f"""** 当前状态感知 **
状态: {state}
{executors_status}  # ← 每步提醒大模型有哪些执行器
任务信息: ...
"""

def _get_executors_status_summary(self) -> str:
    """获取执行器状态摘要（简化版）。"""
    if not self.task_executors:
        return "⚠️ 可用执行器: 无"
    
    lines = ["✅ 可用执行器:"]
    for executor in self.task_executors:
        caps = executor.get_capabilities()
        # 显示执行器名称和支持的任务类型
        task_types = [cap.task_type for cap in caps[:3]]
        ...
    return "\n".join(lines)
```

## 📊 效果对比

### 改进前

- ❌ 大模型不知道有哪些执行器可用
- ❌ 大模型需要"记忆"或"猜测"每个执行器支持的任务类型
- ❌ 大模型不知道每个任务需要什么参数
- ❌ 代码有冗余：`can_handle` 和 `get_supported_task_types` 需要重复定义

### 改进后

- ✅ 系统提示词包含所有执行器的详细能力
- ✅ 大模型清楚知道每个 `task_type` 需要什么参数
- ✅ 参数有自然语言描述和示例，大模型容易理解
- ✅ 感知阶段每步提醒有哪些执行器可用
- ✅ 代码简洁：执行器只需实现 `get_capabilities()`

## 🎬 使用示例

### 定义新执行器

```python
class MyExecutor(TaskExecutorInterface):
    def get_capabilities(self) -> list[TaskCapability]:
        return [
            TaskCapability(
                task_type="my_task",
                name="我的任务",
                description="做某事",
                parameters=[
                    TaskParameter(
                        name="target",
                        description="目标对象",
                        required=True,
                        example="用户数据",
                    ),
                ],
                examples=[...],
                limitations=[...],
            ),
        ]
    
    def execute_task(self, task_type, task_data, config):
        # 实现逻辑
        pass
    
    # can_handle 自动继承，不需要实现！
```

### 使用 TaskAgent

```python
agent = TaskAgent(
    user_input=TerminalUserInput(),
    user_interaction=TerminalUserInteraction(),
    task_executors=[
        PhoneTaskExecutor(model_config),
        GraphRAGQueryExecutor(),
        MyExecutor(),  # ← 自动被识别和使用
    ],
    model_client=model_client,
)

# 大模型自动知道：
# - 有3个执行器
# - 每个执行器支持哪些 task_type
# - 每个 task_type 需要什么参数
# - 参数的含义和示例

agent.run()
```

## 📁 修改的文件

### 核心文件

1. `task_framework/interfaces/task_executor.py` - 重构接口定义
2. `task_framework/interfaces/__init__.py` - 导出新类型
3. `task_framework/agent.py` - 增强 Agent 能力感知
4. `task_framework/implementations/phone_task_executor.py` - 更新实现
5. `task_framework/implementations/graphrag_query_executor.py` - 更新实现

### 新增文件

1. `examples/executor_capability_demo.py` - 功能演示脚本
2. `task_framework/CAPABILITY_ENHANCEMENT.md` - 详细优化说明
3. `task_framework/OPTIMIZATION_SUMMARY.md` - 本文件（总结）

## 🧪 测试

运行演示查看效果：

```bash
# 查看执行器能力定义
python examples/executor_capability_demo.py capabilities

# 查看 Agent 的系统提示词
python examples/executor_capability_demo.py agent

# 查看感知阶段的执行器状态
python examples/executor_capability_demo.py perception
```

## 🎯 核心价值

### 1. 对开发者

- 消除冗余代码
- 类型安全，IDE 有提示
- 易于扩展新执行器

### 2. 对 AI 模型

- 完整感知执行器能力
- 知道何时使用哪个执行器
- 知道需要传递什么参数
- 有示例可以参考

### 3. 对用户

- 更准确的任务执行
- 更少的错误
- 更智能的决策

## 📚 相关文档

- `CAPABILITY_ENHANCEMENT.md` - 详细的优化说明和设计思路
- `README.md` - 框架总体说明
- `EXECUTORS_GUIDE.md` - 执行器使用指南

## ✨ 总结

这次优化实现了两个核心目标：

1. **接口层面**：通过标准化的 `TaskCapability` 定义，消除冗余，使代码更简洁
2. **Agent层面**：通过在系统提示词和感知阶段包含执行器信息，让大模型完全了解可用能力

现在，添加新执行器后，大模型会自动知道它的存在和能力，无需修改任何提示词或配置！
