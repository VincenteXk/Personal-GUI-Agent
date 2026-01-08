## 任务执行器使用指南

## 概述

任务执行器（TaskExecutor）是任务调度框架的核心组件之一，负责执行具体的任务操作。本文档介绍三个主要的执行器实现。

## 执行器架构

```
TaskAgent (调度层)
    ↓ 委托任务
TaskExecutor (执行层)
    ↓ 调用
具体服务 (AutoGLM / GraphRAG / KnowledgeBase)
```

## 可用的执行器

本框架提供两个主要的执行器实现：

### 1. PhoneTaskExecutor - 手机自动化执行器

**功能**：执行手机设备上的自动化任务

**基于**：`src.AutoGLM.agent.PhoneAgent`

**特点**：

- 视觉语言模型驱动
- 感知-思考-行动循环
- 无需人工干预的序列操作
- 支持多种应用场景

**支持的任务类型**：

- `phone_automation` - 通用手机自动化
- `app_launch` - 启动应用
- `send_message` - 发送消息
- `shopping` - 购物相关
- `food_delivery` - 外卖相关
- `general` - 通用任务

**使用示例**：

```python
from task_framework.implementations import PhoneTaskExecutor, PhoneTaskConfig
from src.AutoGLM.model import ModelConfig

# 配置模型
model_config = ModelConfig(
    base_url="http://localhost:8000/v1",
    api_key="your-api-key",
    model_name="glm-4v-plus",
)

# 配置手机任务
phone_config = PhoneTaskConfig(
    device_id=None,  # 自动检测
    max_steps=50,
    lang="zh",
    verbose=True,
)

# 创建执行器
executor = PhoneTaskExecutor(model_config, phone_config)

# 执行任务
result = executor.execute_task(
    task_type="phone_automation",
    task_data={
        "instruction": "打开微信，找到测试联系人1",
        "max_steps": 30,  # 可选
    },
    config={"device_id": "your-device-id"}  # 可选
)

print(f"成功: {result.success}")
print(f"消息: {result.message}")
print(f"步骤数: {result.data.get('step_count')}")
```

**任务数据格式**：

```python
{
    "instruction": "自然语言指令",  # 必需
    "max_steps": 30,  # 可选，覆盖默认配置
}
```

**使用场景**：

1. **单元操作**：简单的单步任务

   ```python
   {"instruction": "打开微信"}
   ```

2. **序列操作**：多步骤任务

   ```python
   {"instruction": "打开微信并打开购物车"}
   ```

3. **复杂任务**：完整的业务流程
   ```python
   {"instruction": "在美团上搜索附近的咖啡店，选择评分最高的"}
   ```

**限制**：

- 需要设备通过 ADB/HDC 连接
- 执行过程不支持人工干预
- 每次需要完整的自然语言指令

---

### 2. GraphRAGQueryExecutor - 知识图谱查询执行器

**功能**：查询 GraphRAG 知识库

**基于**：GraphRAG 后端 API 服务

**特点**：

- 只读查询（不支持写入）
- 支持多种查询类型
- RESTful API 接口
- 即时返回查询结果

**支持的任务类型**：

- `graphrag_query` - 通用查询
- `knowledge_search` - 知识搜索
- `entity_query` - 实体查询
- `relationship_query` - 关系查询

**查询类型**：

- `keyword` - 关键词全文搜索
- `entity` - 查询特定实体
- `relationship` - 查询实体关系
- `path` - 查询实体路径

**使用示例**：

```python
from task_framework.implementations import GraphRAGQueryExecutor, GraphRAGConfig

# 配置GraphRAG
config = GraphRAGConfig(
    backend_url="http://localhost:8000",
    timeout=30,
)

# 创建执行器
executor = GraphRAGQueryExecutor(config)

# 关键词查询
result = executor.execute_task(
    task_type="graphrag_query",
    task_data={
        "query": "用户在微信中的常用操作",
        "query_type": "keyword",
        "limit": 5,
    },
    config={}
)

print(f"找到 {result.data.get('count')} 条结果")
for item in result.data.get('results', []):
    print(f"- {item}")
```

**任务数据格式**：

```python
{
    "query": "查询字符串",  # 必需
    "query_type": "keyword",  # 可选: keyword/entity/relationship/path
    "limit": 5,  # 可选，结果数量限制
}
```

**API 端点映射**：

| query_type   | API 端点                   | 说明       |
| ------------ | -------------------------- | ---------- |
| keyword      | `/api/search/keyword`      | 关键词搜索 |
| entity       | `/api/search/entity`       | 实体查询   |
| relationship | `/api/search/relationship` | 关系查询   |
| path         | `/api/search/path`         | 路径查询   |

**使用场景**：

1. **查找相关知识**：

   ```python
   {"query": "外卖偏好", "query_type": "keyword"}
   ```

2. **查询特定实体**：

   ```python
   {"query": "微信", "query_type": "entity"}
   ```

3. **分析关系**：
   ```python
   {"query": "用户与应用的关系", "query_type": "relationship"}
   ```

**限制**：

- 需要 GraphRAG 后端服务运行
- 只支持查询，不支持写入
- 依赖后端服务的性能

---

## 在 TaskAgent 中使用执行器

### 完整示例

```python
from task_framework import TaskAgent, TaskAgentConfig
from task_framework.implementations import (
    TerminalUserInput,
    TerminalUserInteraction,
    PhoneTaskExecutor,
    GraphRAGQueryExecutor,
    KnowledgeExecutor,
)

# 创建所有执行器
executors = [
    PhoneTaskExecutor(model_config, phone_config),
    GraphRAGQueryExecutor(graphrag_config),
]

# 创建TaskAgent
agent = TaskAgent(
    user_input=TerminalUserInput(),
    user_interaction=TerminalUserInteraction(),
    task_executors=executors,
    config=TaskAgentConfig(verbose=True),
)

# 运行Agent
agent.run()
```

### 调度流程

```
用户输入: "查询我在微信中的常用操作，然后打开微信"

↓ TaskAgent分析

步骤1: 查询GraphRAG知识库
  ↓ 委托给GraphRAGQueryExecutor
  ↓ 执行 graphrag_query
  ↓ 返回结果

步骤2: 展示结果给用户
  ↓ ShowPreview

步骤3: 请求确认
  ↓ Confirm

步骤4: 执行手机操作
  ↓ 委托给PhoneTaskExecutor
  ↓ 执行 phone_automation
  ↓ 返回结果

步骤5: 完成
  ↓ Finish
```

## 扩展：添加新的执行器

### 1. 实现 TaskExecutorInterface

```python
from task_framework.interfaces import TaskExecutorInterface, ExecutionResult

class MyCustomExecutor(TaskExecutorInterface):
    def can_handle(self, task_type: str) -> bool:
        return task_type in ["my_task_type"]

    def execute_task(
        self,
        task_type: str,
        task_data: dict,
        config: dict,
    ) -> ExecutionResult:
        # 实现你的逻辑
        return ExecutionResult(
            success=True,
            message="执行成功",
            data={},
        )

    def get_capabilities(self) -> dict:
        return {
            "name": "MyCustomExecutor",
            "description": "自定义执行器",
            "supported_task_types": ["my_task_type"],
        }
```

### 2. 注册到 TaskAgent

```python
executors = [
    PhoneTaskExecutor(...),
    GraphRAGQueryExecutor(...),
    MyCustomExecutor(...),  # 添加你的执行器
]

agent = TaskAgent(..., task_executors=executors)
```

## 最佳实践

1. **执行器选择**：让 TaskAgent 根据任务类型自动选择执行器
2. **错误处理**：所有执行器都返回 ExecutionResult，包含成功状态和错误信息
3. **配置管理**：使用专门的 Config 类管理执行器配置
4. **能力描述**：实现 get_capabilities()方法，便于调试和文档生成

## 故障排查

### PhoneTaskExecutor

**问题**: 无法连接设备

- 检查设备是否通过 ADB/HDC 连接
- 运行 `adb devices` 或 `hdc list targets`
- 检查 USB 调试是否开启

**问题**: 模型请求失败

- 检查 model_config 中的 base_url 和 api_key
- 确保模型服务正在运行
- 查看详细错误日志

### GraphRAGQueryExecutor

**问题**: 连接后端失败

- 检查 backend_url 是否正确
- 确保 GraphRAG 后端服务正在运行
- 测试 API 端点: `curl http://localhost:8000/api/health`

**问题**: 查询超时

- 增加 timeout 配置
- 检查后端服务性能
- 减少查询复杂度

## 参考资料

- [任务调度框架 README](./README.md)
- [TaskAgent 使用指南](./REFACTORING_SUMMARY.md)
- [AutoGLM 文档](../src/AutoGLM/README.md)
- [完整示例](../examples/integrated_task_agent_demo.py)
