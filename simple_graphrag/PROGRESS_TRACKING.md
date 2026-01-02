# 进度追踪功能说明

## 概述

SimpleGraph 现在支持完整的进度追踪功能，可以实时监控任务执行的每个阶段，并获取每个阶段的详细结果。

## 核心改进

### 1. 架构重构

**SimpleGraph 现在是核心类**

- 移除了对 `AsyncPipeline` 的依赖
- 将所有处理逻辑直接整合到 `SimpleGraph` 中
- `SimpleGraph` 成为唯一的入口类和核心管理器

**优势：**

- 更简洁的依赖关系
- 更好的代码组织
- 更容易扩展和维护

### 2. 任务进度追踪

#### 阶段划分

每个任务的执行分为以下阶段：

1. **started** - 任务开始
2. **system_update** - 更新 System（提取和添加新的类定义）
3. **extraction** - 提取实体和关系
4. **completed** - 任务完成
5. **failed** - 任务失败（如果发生错误）
6. **cancelled** - 任务取消（如果被取消）

#### 阶段结果存储

每个阶段的结果都会被保存，包括：

**system_update 阶段：**

```python
{
    "added_classes": ["类名1", "类名2"],
    "enhanced_classes": ["类名3"],
    "details": "新增 2 个类, 增强 1 个类"
}
```

**extraction 阶段：**

```python
{
    "entities_count": 5,
    "relationships_count": 3,
    "entities": [
        {
            "name": "实体名",
            "description": "实体描述",
            "classes": ["类1", "类2"]
        },
        ...
    ],
    "relationships": [
        {
            "source": "源实体",
            "target": "目标实体",
            "description": "关系描述"
        },
        ...
    ]
}
```

### 3. 进度回调机制

#### 设置回调函数

```python
def progress_callback(task_id: str, step: str, data: dict):
    """
    进度回调函数
    
    Args:
        task_id: 任务ID
        step: 当前步骤名称
        data: 进度数据，包含 message, percentage, result 等
    """
    print(f"任务 {task_id}: {step} - {data['message']} ({data['percentage']}%)")
    
    # 获取阶段结果（如果有）
    if "result" in data:
        print(f"阶段结果: {data['result']}")

# 初始化时设置回调
sg = SimpleGraph(
    config_path=config_path,
    progress_callback=progress_callback
)

# 或者之后设置
sg.set_progress_callback(progress_callback)
```

#### 回调数据格式

```python
{
    "message": "进度消息",
    "percentage": 50,  # 0-100
    "result": {  # 可选，只在阶段完成时存在
        # 阶段特定的结果数据
    }
}
```

### 4. API 增强

#### 新增方法

**获取任务进度：**

```python
progress = sg.get_task_progress(task_id)
# 返回: {"step": "extraction", "message": "正在提取...", "percentage": 50, ...}
```

**获取阶段结果：**

```python
# 获取所有阶段的结果
stage_results = sg.get_task_stage_results(task_id)
# 返回: {
#   "system_update": {"result": {...}, "timestamp": "2025-01-01T10:00:00"},
#   "extraction": {"result": {...}, "timestamp": "2025-01-01T10:00:05"}
# }
```

**设置进度回调：**

```python
sg.set_progress_callback(callback_function)
```

#### Task 模型增强

新增方法：

- `get_stage_result(step: str)` - 获取指定阶段的结果
- `get_all_stage_results()` - 获取所有阶段的结果

更新的 `update_progress` 方法：

```python
task.update_progress(
    step="extraction",
    message="正在提取实体...",
    percentage=50,
    result={"entities_count": 10}  # 新增：可选的阶段结果
)
```

## 使用示例

### 基本用法

```python
import asyncio
from pathlib import Path
from simplegraph import SimpleGraph

def progress_callback(task_id: str, step: str, data: dict):
    print(f"[{step}] {data['message']} - {data.get('percentage', 0)}%")

async def main():
    # 初始化（带回调）
    sg = SimpleGraph(
        config_path=Path("config/config.yaml"),
        progress_callback=progress_callback
    )
    
    await sg.start()
    
    # 提交任务
    task_id = await sg.submit_task("你的文本内容...")
    
    # 等待完成
    while True:
        status = sg.get_task_status(task_id)
        if status["status"] in ["completed", "failed"]:
            break
        await asyncio.sleep(0.5)
    
    # 获取阶段结果
    stage_results = sg.get_task_stage_results(task_id)
    print("System Update 结果:", stage_results["system_update"]["result"])
    print("Extraction 结果:", stage_results["extraction"]["result"])
    
    await sg.stop()

asyncio.run(main())
```

### 详细进度监控

```python
def detailed_progress_callback(task_id: str, step: str, data: dict):
    timestamp = datetime.now().strftime("%H:%M:%S")
    message = data.get("message", "")
    percentage = data.get("percentage", 0)
    
    print(f"[{timestamp}] 任务 {task_id[:8]} | {step}: {message} ({percentage}%)")
    
    # 详细显示阶段结果
    if "result" in data:
        result = data["result"]
        if step == "system_update":
            added = result.get("added_classes", [])
            enhanced = result.get("enhanced_classes", [])
            print(f"  ├─ 新增类: {', '.join(added)}")
            print(f"  └─ 增强类: {', '.join(enhanced)}")
        elif step == "extraction":
            entities = result.get("entities", [])
            relationships = result.get("relationships", [])
            print(f"  ├─ 实体: {len(entities)} 个")
            for entity in entities[:3]:
                print(f"  │   • {entity['name']} ({', '.join(entity['classes'])})")
            print(f"  └─ 关系: {len(relationships)} 个")

sg = SimpleGraph(
    config_path=config_path,
    progress_callback=detailed_progress_callback
)
```

### 实时进度查询

```python
async def monitor_task(sg: SimpleGraph, task_id: str):
    """实时监控任务进度"""
    while True:
        # 获取当前进度
        progress = sg.get_task_progress(task_id)
        if not progress:
            break
            
        print(f"当前阶段: {progress['step']}")
        print(f"进度: {progress.get('percentage', 0)}%")
        
        # 获取已完成的阶段结果
        stage_results = sg.get_task_stage_results(task_id)
        print(f"已完成阶段: {list(stage_results.keys())}")
        
        # 检查任务是否完成
        status = sg.get_task_status(task_id)
        if status["status"] in ["completed", "failed", "cancelled"]:
            break
            
        await asyncio.sleep(1)
```

## 完整示例

查看 `example_simplegraph.py` 获取完整的使用示例，包括：

- 基本任务处理
- 进度回调使用
- 阶段结果获取
- 任务取消
- 并发处理

运行示例：

```bash
python example_simplegraph.py
```

## 技术细节

### 线程安全

- 所有进度更新都在异步上下文中执行
- 回调函数应该是非阻塞的
- 如果回调函数执行失败，会被捕获并记录日志，不会影响任务执行

### 性能考虑

- 阶段结果存储在内存中，对于大量任务请注意内存使用
- 回调函数会在每个阶段完成时同步调用，避免在回调中执行耗时操作
- 建议在回调中只做简单的日志记录或状态更新

### 数据持久化

- 任务的进度和阶段结果可以通过 `to_dict()` 方法序列化
- 可以保存到文件或数据库进行持久化
- 使用 `Task.from_dict()` 可以恢复任务状态

## 迁移指南

### 从旧版本迁移

如果你的代码使用了 `AsyncPipeline`：

**旧代码：**

```python
from src.pipeline.async_pipeline import AsyncPipeline

pipeline = AsyncPipeline(llm_client, config, config_dir)
delta = await pipeline.run_task(task)
```

**新代码：**

```python
# 不再需要直接使用 AsyncPipeline
# SimpleGraph 内部已经集成了所有处理逻辑

sg = SimpleGraph(config_path=config_path)
await sg.start()
task_id = await sg.submit_task(text)
```

### 现有代码兼容性

- `SimpleGraph` 的所有原有 API 保持不变
- `progress_callback` 参数是可选的，不设置也可以正常工作
- 阶段结果功能是自动的，不需要额外配置

## 未来计划

- [ ] 支持自定义阶段
- [ ] 支持进度暂停/恢复
- [ ] 添加进度持久化选项
- [ ] Web UI 进度可视化
- [ ] 实时流式进度更新（WebSocket）
