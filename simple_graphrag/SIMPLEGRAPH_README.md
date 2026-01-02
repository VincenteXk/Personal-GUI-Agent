# SimpleGraph - 增量更新任务队列系统

## 概述

SimpleGraph 是一个基于异步任务队列的知识图谱增量更新系统，核心特性：

- ✅ **任务隔离**: 每个任务使用独立的 system 副本，任务间互不影响
- ✅ **真正并行**: 基于 asyncio 的异步任务处理，支持多任务并发
- ✅ **智能合并**: 使用 LLM 进行去重、对齐、冲突解决和优化
- ✅ **灵活控制**: 支持任务提交、取消、状态查询
- ✅ **面向对象**: 清晰的 API 接口，易于使用和集成

## 架构

```
用户
 │
 ├─► submit_task(text) ──► Task ──► AsyncPipeline ──► GraphDelta
 │                          │                            │
 │                          └─ system_snapshot          │
 │                            (任务隔离)                  │
 │                                                       │
 └─► SmartMerger ◄──────────────────────────────────────┘
      (智能合并)
       │
       ├─ 去重识别
       ├─ 命名对齐
       ├─ 冲突解决
       └─ 描述优化
       │
       ▼
    主 System/Graph
```

## 快速开始

### 安装依赖

确保已安装所需依赖：

```bash
# 如果使用 pip
pip install -r requirements.txt

# 如果使用 uv
uv sync
```

### 基本使用

```python
import asyncio
from pathlib import Path
from simplegraph import SimpleGraph

async def main():
    # 1. 初始化 SimpleGraph
    sg = SimpleGraph(
        config_path=Path("config/config.yaml"),
        max_concurrent_tasks=3,      # 最多3个并发任务
        enable_smart_merge=True,     # 启用智能合并
    )
    
    # 2. 启动任务处理器
    await sg.start()
    
    # 3. 提交任务（并行执行）
    task1 = await sg.submit_task("我在淘宝上购买了一本书。")
    task2 = await sg.submit_task("我在京东上买了一部手机。")
    task3 = await sg.submit_task("我在B站上看了一个视频。")
    
    # 4. 等待任务完成
    while True:
        statuses = [
            sg.get_task_status(tid)["status"] 
            for tid in [task1, task2, task3]
        ]
        if all(s in ["completed", "failed"] for s in statuses):
            break
        await asyncio.sleep(1)
    
    # 5. 查看结果
    stats = sg.get_statistics()
    print(f"实体: {stats['graph']['entities']}")
    print(f"关系: {stats['graph']['relationships']}")
    
    # 6. 保存和可视化
    sg.save(Path("output/graph.pkl"))
    sg.visualize(Path("output/graph.html"))
    
    # 7. 停止
    await sg.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

## API 文档

### SimpleGraph 类

#### 初始化

```python
sg = SimpleGraph(
    config_path: Path,              # 配置文件路径
    max_concurrent_tasks: int = 3,  # 最大并发任务数
    enable_smart_merge: bool = True # 是否启用智能合并
)
```

#### 方法

##### start() / stop()

```python
await sg.start()   # 启动任务处理器
await sg.stop()    # 停止任务处理器
```

##### submit_task()

```python
task_id = await sg.submit_task(input_text: str) -> str
```

提交一个任务，返回任务 ID。

##### cancel_task()

```python
success = await sg.cancel_task(task_id: str) -> bool
```

取消一个任务，返回是否成功。

##### get_task_status()

```python
status = sg.get_task_status(task_id: str) -> Optional[dict]
```

获取任务状态：

```python
{
    "task_id": "uuid",
    "input_text": "...",
    "status": "completed",  # pending, running, completed, failed, cancelled
    "created_at": "2025-01-01T00:00:00",
    "started_at": "2025-01-01T00:00:01",
    "completed_at": "2025-01-01T00:00:10",
    "error": None,
    "duration": 9.5,
    "progress": {
        "step": "completed",
        "message": "任务完成",
        "percentage": 100
    }
}
```

##### get_all_tasks()

```python
tasks = sg.get_all_tasks() -> List[dict]
```

获取所有任务列表。

##### get_statistics()

```python
stats = sg.get_statistics() -> dict
```

获取统计信息：

```python
{
    "system": {
        "classes": 10,
        "predefined_entities": 5
    },
    "graph": {
        "entities": 50,
        "relationships": 100
    },
    "tasks": {
        "total": 10,
        "by_status": {
            "pending": 0,
            "running": 2,
            "completed": 7,
            "failed": 1,
            "cancelled": 0
        }
    }
}
```

##### save() / visualize()

```python
sg.save(path: Path)                          # 保存图谱
sg.visualize(output_path: Path)              # 生成可视化
```

## 核心概念

### 1. 任务隔离

每个任务创建时会深拷贝当前的 `System`，作为任务的独立副本。任务在执行过程中只修改副本，不影响主 `System` 和其他任务。

```python
# 任务提交时
system_snapshot = copy.deepcopy(self.system)
task = Task(
    task_id=generate_task_id(),
    input_text=input_text,
    system_snapshot=system_snapshot,
)
```

### 2. 增量更新包 (GraphDelta)

任务执行完成后不直接修改 `Graph`，而是生成 `GraphDelta` 增量包：

```python
@dataclass
class GraphDelta:
    task_id: str
    classes: List[ClassDelta]           # 类的增量
    entities: List[EntityDelta]         # 实体的增量
    relationships: List[RelationshipDelta]  # 关系的增量
    metadata: Dict                      # 任务元信息
```

### 3. 智能合并 (SmartMerger)

使用 LLM 对增量包进行智能处理：

- **去重识别**: 识别相同实体/关系的不同表达
- **命名对齐**: 统一命名规范
- **冲突解决**: 处理属性值冲突
- **描述优化**: 合并重复信息，提炼精准描述

```python
merge_result = await merger.merge_delta(
    current_system=self.system,
    current_graph=self.graph,
    delta=task.result_delta,
)
```

### 4. 异步流水线 (AsyncPipeline)

基于 `pipeline_v2.py` 改造的异步版本：

```python
pipeline = AsyncPipeline(llm_client, config, config_dir)
delta = await pipeline.run_task(task)
```

改动：

- 所有 LLM 调用改为异步
- 输出改为 `GraphDelta`
- 支持任务取消检查

## 示例

### 示例 1: 基本使用

```bash
python example_simplegraph.py
```

演示完整的使用流程，包括任务提交、状态查询、保存和可视化。

### 示例 2: 任务取消

修改 `example_simplegraph.py` 中的主函数：

```python
if __name__ == "__main__":
    asyncio.run(demo_cancel_task())
```

### 示例 3: 并发任务

修改 `example_simplegraph.py` 中的主函数：

```python
if __name__ == "__main__":
    asyncio.run(demo_concurrent_tasks())
```

## 测试

运行测试套件：

```bash
python test_simplegraph.py
```

测试内容：

- ✅ 基本功能
- ✅ 并发任务
- ✅ 任务取消
- ✅ 智能合并
- ✅ 统计功能

## 配置

### 智能合并配置

在初始化时控制是否启用智能合并：

```python
# 启用智能合并（推荐）
sg = SimpleGraph(config_path, enable_smart_merge=True)

# 禁用智能合并（简单模式，速度更快）
sg = SimpleGraph(config_path, enable_smart_merge=False)
```

### 并发配置

调整最大并发任务数：

```python
sg = SimpleGraph(
    config_path,
    max_concurrent_tasks=5  # 同时运行最多5个任务
)
```

## 与 pipeline_v2 的比较

| 特性 | pipeline_v2 | SimpleGraph |
|------|-------------|-------------|
| 任务处理 | 顺序执行 | 并行执行 |
| 任务隔离 | 无 | 有（副本system） |
| 任务管理 | 无 | 提交/取消/查询 |
| 合并方式 | 程序化 | LLM智能合并 |
| 接口风格 | 函数式 | 面向对象 |
| 适用场景 | 单次批量处理 | 持续更新服务 |

## 性能优化建议

1. **调整并发数**: 根据 LLM API 的限流和机器性能调整 `max_concurrent_tasks`
2. **禁用智能合并**: 如果不需要去重和优化，可以禁用智能合并以提升速度
3. **批量提交**: 一次性提交多个任务，让系统自动调度
4. **任务优先级**: 未来可以扩展支持任务优先级队列

## 故障排查

### 问题 1: 任务一直处于 pending 状态

**原因**: 任务处理器未启动

**解决**: 确保调用了 `await sg.start()`

### 问题 2: 任务失败，错误信息为 LLM 调用失败

**原因**: API Key 未设置或无效

**解决**: 检查环境变量 `ARK_API_KEY` 或 `MIMO_API_KEY`

### 问题 3: 智能合并失败，降级到简单合并

**原因**: LLM 返回的 JSON 格式不正确

**解决**:

- 检查 `config/prompts/smart_merge.txt` 提示词
- 查看日志中的 LLM 响应内容
- 临时禁用智能合并：`enable_smart_merge=False`

## 扩展开发

### 自定义合并策略

继承 `SmartMerger` 类并重写 `merge_delta` 方法：

```python
class CustomMerger(SmartMerger):
    async def merge_delta(self, system, graph, delta):
        # 自定义合并逻辑
        pass
```

### 添加任务优先级

扩展 `Task` 类添加优先级字段：

```python
@dataclass
class PriorityTask(Task):
    priority: int = 0  # 优先级，数字越大越优先
```

## 未来计划

- [ ] 任务优先级队列
- [ ] 任务持久化（重启恢复）
- [ ] 分布式任务处理
- [ ] Web API 接口
- [ ] 实时进度回调
- [ ] 任务依赖管理

## 许可证

同项目根目录许可证。

## 贡献

欢迎提交 Issue 和 Pull Request！
