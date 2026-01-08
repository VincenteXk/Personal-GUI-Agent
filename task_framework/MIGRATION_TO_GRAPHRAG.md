# 迁移到统一 GraphRAG 后端

## 变更说明

为了简化架构并统一知识查询入口，我们已移除 `KnowledgeExecutor`，统一使用 `GraphRAGQueryExecutor` 作为知识查询后端。

## 主要变更

### 1. 移除的组件

- ❌ `task_framework/implementations/knowledge_executor.py` - 已删除
- ❌ `KnowledgeExecutor` 类
- ❌ `KnowledgeExecutorConfig` 类

### 2. 保留的组件

- ✅ `task_framework/implementations/phone_task_executor.py` - PhoneTaskExecutor
- ✅ `task_framework/implementations/graphrag_query_executor.py` - GraphRAGQueryExecutor
- ✅ 所有示例和文档已更新

### 3. 架构简化

**之前**：

```
├─ PhoneTaskExecutor → AutoGLM
├─ GraphRAGQueryExecutor → GraphRAG Backend
└─ KnowledgeExecutor → Local NetworkX + Optional GraphRAG
```

**现在**：

```
├─ PhoneTaskExecutor → AutoGLM
└─ GraphRAGQueryExecutor → GraphRAG Backend (统一知识查询)
```

## 迁移指南

### 代码更新

#### 旧代码（使用 KnowledgeExecutor）

```python
from task_framework.implementations import KnowledgeExecutor, KnowledgeExecutorConfig

# 配置本地知识库
config = KnowledgeExecutorConfig(
    storage_path="knowledge_base.json",
    enable_graphrag=True,
)

executor = KnowledgeExecutor(config)

# 搜索习惯
result = executor.execute_task(
    "search_habits",
    {"query": "微信", "limit": 5},
    {}
)

# 获取应用习惯
result = executor.execute_task(
    "get_app_habits",
    {"app_name": "微信"},
    {}
)

# 获取统计
result = executor.execute_task(
    "get_statistics",
    {},
    {}
)
```

#### 新代码（使用 GraphRAGQueryExecutor）

```python
from task_framework.implementations import GraphRAGQueryExecutor, GraphRAGConfig

# 配置GraphRAG
config = GraphRAGConfig(
    backend_url="http://localhost:8000",
    timeout=30,
)

executor = GraphRAGQueryExecutor(config)

# 搜索习惯（使用keyword查询）
result = executor.execute_task(
    "graphrag_query",
    {"query": "用户在微信中的习惯", "query_type": "keyword", "limit": 5},
    {}
)

# 获取应用相关信息（使用entity查询）
result = executor.execute_task(
    "entity_query",
    {"query": "微信", "query_type": "entity", "limit": 5},
    {}
)

# 查询关系（如果需要）
result = executor.execute_task(
    "relationship_query",
    {"query": "用户与微信的关系", "query_type": "relationship", "limit": 5},
    {}
)
```

### 任务类型映射

| 旧任务类型（KnowledgeExecutor） | 新任务类型（GraphRAGQueryExecutor） | query_type |
| ------------------------------- | ----------------------------------- | ---------- |
| `search_habits`                 | `graphrag_query`                    | `keyword`  |
| `get_app_habits`                | `entity_query`                      | `entity`   |
| `get_statistics`                | ❌ 不再支持                         | -          |

### TaskAgent 配置更新

#### 旧配置

```python
executors = [
    PhoneTaskExecutor(model_config, phone_config),
    GraphRAGQueryExecutor(graphrag_config),
    KnowledgeExecutor(knowledge_config),  # ❌ 已移除
]

agent = TaskAgent(
    user_input=TerminalUserInput(),
    user_interaction=TerminalUserInteraction(),
    task_executors=executors,
    config=config,
)
```

#### 新配置

```python
executors = [
    PhoneTaskExecutor(model_config, phone_config),
    GraphRAGQueryExecutor(graphrag_config),  # ✅ 统一知识查询
]

agent = TaskAgent(
    user_input=TerminalUserInput(),
    user_interaction=TerminalUserInteraction(),
    task_executors=executors,
    config=config,
)
```

## GraphRAG 后端要求

### 必需的 API 端点

GraphRAG 后端服务需要提供以下 API 端点：

- `GET /api/search/keyword` - 关键词搜索
- `GET /api/search/entity` - 实体查询
- `GET /api/search/relationship` - 关系查询
- `GET /api/search/path` - 路径查询

### 请求参数

```python
{
    "query": str,    # 查询字符串
    "limit": int,    # 返回结果数量限制
}
```

### 响应格式

```python
{
    "success": bool,
    "results": [
        {
            "text": str,           # 结果文本
            "metadata": dict,      # 元数据
            # ... 其他字段
        }
    ],
    "count": int,  # 结果数量
}
```

## 数据迁移

### 如果你有本地 knowledge_base.json

本地知识库数据（`knowledge_base.json`）不会被自动迁移到 GraphRAG。

**迁移选项**：

1. **保留本地数据**（推荐）：

   - 保留 `src.core.knowledge_base` 模块用于数据存储
   - 数据会通过 `KnowledgeBase` 内部的 GraphRAG 集成自动同步
   - 不需要手动迁移

2. **手动迁移到 GraphRAG**：

   ```python
   from src.core.knowledge_base import KnowledgeBase

   # 加载本地知识库
   kb = KnowledgeBase("knowledge_base.json")

   # 数据会自动同步到GraphRAG（如果启用）
   # 或者手动遍历并导入数据
   ```

3. **仅使用 GraphRAG**：
   - 不再使用本地 NetworkX 存储
   - 所有数据直接存储到 GraphRAG 后端
   - 需要确保 GraphRAG 后端有写入 API（当前仅支持查询）

## 优势

### 1. 架构简化

- 单一知识查询入口
- 减少代码维护负担
- 统一的数据访问接口

### 2. 性能优化

- GraphRAG 后端可以提供更强大的查询能力
- 支持分布式部署
- 更好的扩展性

### 3. 功能增强

- 支持更丰富的查询类型（实体、关系、路径）
- 更好的语义搜索能力
- 统一的知识图谱管理

## 常见问题

### Q: 本地知识库数据会丢失吗？

A: 不会。`knowledge_base.json` 文件仍然存在，可以通过 `src.core.knowledge_base` 模块访问。只是不再通过 TaskExecutor 接口访问。

### Q: 如何查询本地知识库？

A: 有两种方式：

1. 直接使用 `src.core.knowledge_base.KnowledgeBase` 类
2. 确保本地数据已同步到 GraphRAG，然后通过 `GraphRAGQueryExecutor` 查询

### Q: GraphRAG 后端服务必须运行吗？

A: 是的。现在所有知识查询都依赖 GraphRAG 后端服务。如果服务未运行，查询会返回错误。

### Q: 可以恢复 KnowledgeExecutor 吗？

A: 可以。`knowledge_executor.py` 的代码已在 git 历史中，可以通过 git 恢复。但不建议这样做，建议统一使用 GraphRAG。

### Q: get_statistics 功能去哪了？

A: 统计功能需要由 GraphRAG 后端提供。可以添加相应的 API 端点，或者直接使用 `src.core.knowledge_base.KnowledgeBase.get_statistics()`。

## 回滚指南

如果需要回滚到使用 KnowledgeExecutor：

```bash
# 恢复文件
git checkout HEAD~1 task_framework/implementations/knowledge_executor.py

# 恢复导入
git checkout HEAD~1 task_framework/implementations/__init__.py

# 恢复示例
git checkout HEAD~1 examples/integrated_task_agent_demo.py
```

## 未来计划

1. **GraphRAG 写入支持**：添加数据写入功能
2. **统计 API**：在 GraphRAG 后端添加统计接口
3. **批量导入工具**：提供从本地知识库迁移到 GraphRAG 的工具

## 相关文档

- [任务执行器使用指南](./EXECUTORS_GUIDE.md)
- [集成总结](./INTEGRATION_SUMMARY.md)
- [框架 README](./README.md)
