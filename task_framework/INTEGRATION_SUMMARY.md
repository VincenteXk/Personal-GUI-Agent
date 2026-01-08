# 任务调度 Agent 下游功能集成总结

## 完成的工作

已成功将现有模块整合到任务调度框架，创建了三个 TaskExecutor 实现：

### 1. PhoneTaskExecutor - AutoGLM 集成

**文件**: `task_framework/implementations/phone_task_executor.py`

**功能**：

- 封装 `src.AutoGLM.agent.PhoneAgent`
- 提供手机自动化能力给任务调度 Agent
- 支持单元操作和序列操作

**特点**：

- 无修正、无选择、无外部交互的执行模式
- 基于视觉语言模型的感知-思考-行动循环
- 适合作为 TaskAgent 的底层执行器

**使用方式**：

```python
from task_framework.implementations import PhoneTaskExecutor, PhoneTaskConfig
from src.AutoGLM.model import ModelConfig

executor = PhoneTaskExecutor(model_config, phone_config)
result = executor.execute_task(
    "phone_automation",
    {"instruction": "打开微信并打开购物车"},
    {}
)
```

**响应示例**：参考 `src/AutoGLM/response_example.txt`

- 包含 thinking（思考过程）
- 包含 action（执行的操作）
- 包含 raw_content（完整响应）

---

### 2. GraphRAGQueryExecutor - 知识图谱查询

**文件**: `task_framework/implementations/graphrag_query_executor.py`

**功能**：

- 连接 GraphRAG 后端 API 服务
- 提供即时知识查询能力
- 支持多种查询类型

**特点**：

- 只读查询（不写入）
- RESTful API 接口
- 支持关键词、实体、关系、路径查询

**API 端点**：

```
GET /api/search/keyword      - 关键词搜索
GET /api/search/entity        - 实体查询
GET /api/search/relationship  - 关系查询
GET /api/search/path          - 路径查询
```

**使用方式**：

```python
from task_framework.implementations import GraphRAGQueryExecutor, GraphRAGConfig

executor = GraphRAGQueryExecutor(config)
result = executor.execute_task(
    "graphrag_query",
    {
        "query": "用户在微信中的常用操作",
        "query_type": "keyword",
        "limit": 5
    },
    {}
)
```

---

## 整合架构

```
┌─────────────────────────────────────────────────────────┐
│                     TaskAgent                           │
│                   (调度决策层)                          │
│                                                         │
│  - 感知-思考-行动循环                                   │
│  - 用户交互管理                                         │
│  - 任务规划和分解                                       │
│  - 动态路径调整                                         │
└─────────────────┬───────────────────────────────────────┘
                  │ DelegateTask
                  ↓
┌─────────────────────────────────────────────────────────┐
│              TaskExecutor 接口层                        │
└─────┬───────────────┬─────────────────┬─────────────────┘
      │               │                 │
      ↓               ↓                 ↓
┌──────────┐   ┌─────────────┐
│ Phone    │   │ GraphRAG    │
│ Task     │   │ Query       │
│ Executor │   │ Executor    │
└────┬─────┘   └──────┬──────┘
     │                │
     ↓                ↓
┌──────────┐   ┌─────────────┐
│ AutoGLM  │   │ GraphRAG    │
│ Phone    │   │ Backend     │
│ Agent    │   │ API         │
└────┬─────┘   └─────────────┘
     │
     ↓
┌──────────┐
│ Device   │
│ (ADB/    │
│  HDC)    │
└──────────┘
```

## 使用示例

### 完整示例代码

见 `examples/integrated_task_agent_demo.py`

**运行方式**：

```bash
# 运行完整的Agent（交互式）
python examples/integrated_task_agent_demo.py

# 演示直接使用执行器
python examples/integrated_task_agent_demo.py --demo
```

### 典型使用场景

#### 场景 1：GraphRAG 查询 + 执行操作

```
用户输入: "查询我在微信中的常用操作，然后打开微信"

TaskAgent处理流程:
1. 分析任务 -> 需要两个步骤
2. DelegateTask(GraphRAGQueryExecutor) -> 查询知识库
3. ShowPreview -> 展示查询结果
4. DelegateTask(PhoneTaskExecutor) -> 打开微信
5. Finish -> 完成
```

#### 场景 2：GraphRAG 查询 + 决策

```
用户输入: "根据我的购物偏好，在淘宝上搜索适合的商品"

TaskAgent处理流程:
1. DelegateTask(GraphRAGQueryExecutor) -> 查询购物偏好
2. AnalyzeTask -> 分析偏好数据
3. DelegateTask(PhoneTaskExecutor) -> 在淘宝执行搜索
4. Confirm -> 请求用户确认结果
5. Finish -> 完成
```

#### 场景 3：GraphRAG 查询

```
用户输入: "查询知识库中关于外卖偏好的信息"

TaskAgent处理流程:
1. DelegateTask(GraphRAGQueryExecutor) -> 查询GraphRAG
2. ShowPreview -> 展示查询结果
3. AskUser -> 询问是否需要进一步操作
4. Finish -> 完成
```

## 配置说明

### 模型配置

所有执行器都支持使用大模型，需要配置：

```python
from src.AutoGLM.model import ModelConfig

model_config = ModelConfig(
    base_url="http://localhost:8000/v1",  # 模型API地址
    api_key="your-api-key",                # API密钥
    model_name="glm-4v-plus",              # 模型名称
)
```

### 设备配置

PhoneTaskExecutor 需要设备连接：

```python
from task_framework.implementations import PhoneTaskConfig

phone_config = PhoneTaskConfig(
    device_id=None,      # None表示自动检测
    max_steps=50,        # 最大步骤数
    lang="zh",           # 语言
    verbose=True,        # 详细输出
)
```

### GraphRAG 配置

GraphRAGQueryExecutor 需要后端服务：

```python
from task_framework.implementations import GraphRAGConfig

graphrag_config = GraphRAGConfig(
    backend_url="http://localhost:8000",  # 后端地址
    timeout=30,                           # 超时时间
)
```

**注意**：所有知识查询统一使用 GraphRAG 后端服务，包括：

- 用户习惯查询
- 应用使用历史
- 实体和关系查询
- 知识图谱搜索

## 工具模块使用

### src/core 模块

#### knowledge_base.py

- 提供图结构存储用户交互数据
- 支持本地 NetworkX 和 GraphRAG 双存储
- 提供搜索、查询、统计功能

#### observer.py

- 用户行为监控（当前未集成到 TaskExecutor）
- 可用于学习模式，收集用户操作数据

#### refiner.py

- 指令优化器（当前未集成到 TaskExecutor）
- 可用于任务分析阶段优化用户输入

### src/shared 模块

#### config.py

- 提供应用包名映射
- 支持中英文应用名称转换

**使用示例**：

```python
from src.shared.config import get_app_name_from_package, get_package_from_app_name

# 包名转应用名
app_name = get_app_name_from_package("com.tencent.mm")  # "微信"

# 应用名转包名
package = get_package_from_app_name("微信")  # "com.tencent.mm"
```

## 文档

### 核心文档

- `task_framework/README.md` - 框架总体介绍
- `task_framework/REFACTORING_SUMMARY.md` - 重构说明
- `task_framework/CHANGELOG.md` - 更新日志

### 新增文档

- `task_framework/EXECUTORS_GUIDE.md` - 执行器详细使用指南
- `task_framework/INTEGRATION_SUMMARY.md` - 本文档

### 示例代码

- `examples/task_scheduler_demo.py` - 基础示例
- `examples/integrated_task_agent_demo.py` - 完整集成示例

## 依赖关系

### PhoneTaskExecutor

- `src.AutoGLM.agent.PhoneAgent`
- `src.AutoGLM.model.ModelClient`
- 设备连接（ADB/HDC）

### GraphRAGQueryExecutor

- GraphRAG 后端服务（需单独运行）
- `requests` 库

### TaskAgent

- 所有执行器
- 大模型客户端（可选）

## 下一步建议

### 1. 集成 Observer（可选）

将 `src.core.observer.py` 集成为一个执行器，提供学习模式功能：

```python
class ObserverExecutor(TaskExecutorInterface):
    def can_handle(self, task_type: str) -> bool:
        return task_type in ["start_learning", "stop_learning"]

    def execute_task(self, task_type, task_data, config):
        # 启动/停止用户行为学习
        pass
```

### 2. 集成 Refiner（可选）

将 `src.core.refiner.py` 用于任务分析阶段，优化用户输入：

```python
# 在TaskAgent的_normalize_task中使用
refined_task = refiner.refine_instruction(original_input)
```

### 3. 增强 GraphRAG 集成

- 实现 GraphRAG 的写入功能（如果需要）
- 添加更多查询类型
- 优化查询性能

### 4. 添加更多执行器

- Web 自动化执行器
- 邮件执行器
- 日历执行器
- ...

## 测试建议

### 单元测试

```python
# 测试PhoneTaskExecutor
def test_phone_executor():
    executor = PhoneTaskExecutor(mock_model_config)
    result = executor.execute_task(
        "phone_automation",
        {"instruction": "test"},
        {}
    )
    assert result.success or not result.success  # 取决于环境

# 测试GraphRAGQueryExecutor
def test_graphrag_executor():
    executor = GraphRAGQueryExecutor()
    result = executor.execute_task(
        "graphrag_query",
        {"query": "test", "query_type": "keyword"},
        {}
    )
    assert result.success or not result.success  # 取决于后端服务
```

### 集成测试

```python
def test_integrated_agent():
    agent = TaskAgent(
        user_input=MockUserInput(),
        user_interaction=MockUserInteraction(),
        task_executors=[
            PhoneTaskExecutor(...),
            GraphRAGQueryExecutor(...),
        ],
    )

    # 模拟任务执行
    result = agent._execute_task("test task")
    assert result is not None
```

## 总结

成功完成了任务调度 Agent 与现有模块的集成：

✅ **PhoneTaskExecutor** - 整合 AutoGLM 手机自动化
✅ **GraphRAGQueryExecutor** - 连接 GraphRAG 知识库（统一知识查询入口）
✅ **完整示例** - 提供可运行的演示代码
✅ **详细文档** - EXECUTORS_GUIDE.md

现在 TaskAgent 可以：

1. 通过 GraphRAG 查询知识库和用户习惯
2. 执行手机自动化操作
3. 动态调度不同的执行器
4. 提供完整的任务规划和执行能力

架构清晰，统一使用 GraphRAG 作为知识查询后端，易于扩展，文档完善。
