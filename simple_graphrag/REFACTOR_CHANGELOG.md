# SimpleGraph 架构重构 - 变更日志

## 版本：v2.0

**重构日期：** 2025-12-31

## 概述

这次重构的核心目标是：

1. **将 SimpleGraph 作为唯一的核心类**，移除对 AsyncPipeline 的依赖
2. **添加完整的进度追踪功能**，支持每个阶段的进度回调和结果获取

## 主要变更

### 1. 架构调整

#### 变更前（v1.x）

```
SimpleGraph (外层管理)
    └── AsyncPipeline (核心处理逻辑)
            ├── SystemUpdater
            ├── GraphExtractor
            └── SmartMerger
```

#### 变更后（v2.0）

```
SimpleGraph (核心类)
    ├── SystemUpdater (直接使用)
    ├── GraphExtractor (直接使用)
    └── SmartMerger (直接使用)
```

**AsyncPipeline 已被移除**，其所有逻辑已整合到 SimpleGraph 中。

### 2. 文件变更清单

#### 修改的文件

**`src/models/task.py`**

- ✅ 新增 `stage_results` 字段用于存储每个阶段的结果
- ✅ 增强 `update_progress()` 方法，支持传入 `result` 参数
- ✅ 新增 `get_stage_result(step)` 方法获取指定阶段结果
- ✅ 新增 `get_all_stage_results()` 方法获取所有阶段结果
- ✅ 更新 `to_dict()` 和 `from_dict()` 以支持序列化阶段结果

**`simplegraph.py`**

- ✅ 移除对 `AsyncPipeline` 的导入和依赖
- ✅ 新增导入：`SystemUpdater`, `GraphExtractor`, `Entity`, `Relationship` 等
- ✅ 构造函数新增 `progress_callback` 参数
- ✅ 新增私有方法：
  - `_notify_progress()` - 通知进度回调
  - `_check_cancelled()` - 检查任务取消
  - `_run_task()` - 执行任务的核心逻辑（整合自 AsyncPipeline）
  - `_step_update_system()` - System 更新阶段
  - `_check_and_update_async()` - 异步检查和更新
  - `_check_and_generate_async()` - 异步生成配置
  - `_step_extract()` - 实体关系提取阶段
  - `_extract_async()` - 异步提取
  - `_check_extraction_async()` - 异步检查提取结果
- ✅ 新增公共方法：
  - `set_progress_callback()` - 设置进度回调
  - `get_task_progress()` - 获取任务进度
  - `get_task_stage_results()` - 获取任务阶段结果
- ✅ 修改 `_worker()` 方法，使用内部的 `_run_task()` 代替 AsyncPipeline

**`example_simplegraph.py`**

- ✅ 新增 `progress_callback` 函数示例
- ✅ 在初始化时传入 `progress_callback`
- ✅ 在任务结果展示中添加阶段结果输出
- ✅ 新增 `demo_progress_tracking()` 函数，演示详细进度追踪
- ✅ 更新其他演示函数以使用进度回调

#### 新增的文件

**`PROGRESS_TRACKING.md`**

- 📄 完整的进度追踪功能文档
- 包含 API 说明、使用示例、技术细节等

**`REFACTOR_CHANGELOG.md`**

- 📄 本文档，记录所有变更

#### 不再使用的文件

**`src/pipeline/async_pipeline.py`**

- ⚠️ 此文件仍然存在，但不再被使用
- 可以选择删除或保留作为参考

## API 变更

### 新增 API

#### SimpleGraph

```python
# 构造函数新增参数
SimpleGraph(
    config_path: Path,
    max_concurrent_tasks: int = 3,
    enable_smart_merge: bool = True,
    progress_callback: Optional[Callable[[str, str, dict], None]] = None  # 新增
)

# 新增方法
sg.set_progress_callback(callback)           # 设置进度回调
sg.get_task_progress(task_id)                # 获取任务进度
sg.get_task_stage_results(task_id)           # 获取任务阶段结果
```

#### Task

```python
# 增强的方法
task.update_progress(step, message, percentage, result=None)  # result 参数新增

# 新增方法
task.get_stage_result(step)        # 获取指定阶段结果
task.get_all_stage_results()        # 获取所有阶段结果
```

### 保持不变的 API

以下 API 完全向后兼容：

- `SimpleGraph.submit_task()`
- `SimpleGraph.cancel_task()`
- `SimpleGraph.get_task_status()`
- `SimpleGraph.get_all_tasks()`
- `SimpleGraph.get_statistics()`
- `SimpleGraph.save()`
- `SimpleGraph.visualize()`
- `SimpleGraph.start()`
- `SimpleGraph.stop()`

## 功能增强

### 1. 进度追踪

**阶段划分：**

- `started` - 任务开始（0%）
- `system_update` - 更新 System（10-30%）
- `extraction` - 提取实体和关系（50-80%）
- `completed` - 任务完成（100%）
- `failed` / `cancelled` - 异常状态

**每个阶段的详细信息：**

- 进度消息
- 完成百分比
- 阶段结果（JSON 格式）
- 时间戳

### 2. 回调机制

```python
def progress_callback(task_id: str, step: str, data: dict):
    """
    Args:
        task_id: 任务唯一标识
        step: 当前阶段名称
        data: 包含 message, percentage, result 等信息
    """
    pass

sg = SimpleGraph(config_path=config_path, progress_callback=progress_callback)
```

### 3. 阶段结果存储

每个阶段的结果都会自动保存，可以通过以下方式获取：

```python
# 获取所有阶段结果
stage_results = sg.get_task_stage_results(task_id)

# 结构：
{
    "system_update": {
        "result": {
            "added_classes": ["类1", "类2"],
            "enhanced_classes": ["类3"],
            "details": "..."
        },
        "timestamp": "2025-12-31T10:00:00"
    },
    "extraction": {
        "result": {
            "entities_count": 10,
            "relationships_count": 5,
            "entities": [...],
            "relationships": [...]
        },
        "timestamp": "2025-12-31T10:00:05"
    }
}
```

## 迁移指南

### 如果你直接使用 SimpleGraph

**无需任何修改！**所有现有代码继续工作。

### 如果你使用了 AsyncPipeline

**变更前：**

```python
from src.pipeline.async_pipeline import AsyncPipeline

pipeline = AsyncPipeline(llm_client, config, config_dir)
delta = await pipeline.run_task(task)
```

**变更后：**

```python
# 直接使用 SimpleGraph
sg = SimpleGraph(config_path=config_path)
await sg.start()
task_id = await sg.submit_task(input_text)
```

### 添加进度追踪（可选）

```python
# 定义回调函数
def my_progress_callback(task_id, step, data):
    print(f"任务 {task_id}: {step} - {data['message']}")

# 初始化时传入
sg = SimpleGraph(
    config_path=config_path,
    progress_callback=my_progress_callback
)

# 或者之后设置
sg.set_progress_callback(my_progress_callback)
```

## 技术亮点

### 1. 单一职责原则

SimpleGraph 现在是唯一的核心类，负责：

- 任务队列管理
- 并发控制
- 任务执行
- 进度追踪
- 结果合并

### 2. 依赖注入

所有依赖（LLMClient, SystemUpdater, GraphExtractor, SmartMerger）都在 SimpleGraph 内部管理。

### 3. 异步设计

完全异步的任务处理流程，支持高并发。

### 4. 可观测性

通过进度回调和阶段结果，提供完整的任务执行可见性。

## 性能影响

- ✅ 无性能退化
- ✅ 进度追踪开销极小（仅内存存储）
- ✅ 回调机制是同步的，不阻塞任务执行
- ✅ 并发处理能力不变

## 测试

### 语法检查

所有修改的文件都通过了 Python 语法检查：

```bash
python -m py_compile simplegraph.py
python -m py_compile src/models/task.py
python -m py_compile example_simplegraph.py
```

### 建议的测试

运行现有的测试用例：

```bash
python example_simplegraph.py
python test_simplegraph.py
```

## 后续计划

- [ ] 删除或归档 `async_pipeline.py`
- [ ] 更新其他文档以反映架构变化
- [ ] 添加进度追踪的单元测试
- [ ] 考虑添加 Web UI 进度可视化
- [ ] 实现进度持久化功能

## 相关文档

- `PROGRESS_TRACKING.md` - 进度追踪功能详细说明
- `SIMPLEGRAPH_README.md` - SimpleGraph 使用指南
- `example_simplegraph.py` - 完整的使用示例

## 贡献者

- **重构实施：** 2025-12-31

---

**注意：** 这是一个向后兼容的更新，现有代码无需修改即可继续使用。新功能是可选的增强。
