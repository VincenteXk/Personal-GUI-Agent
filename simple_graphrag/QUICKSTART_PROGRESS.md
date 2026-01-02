# 进度追踪快速开始

## 最简单的例子

```python
import asyncio
from pathlib import Path
from simplegraph import SimpleGraph

async def main():
    # 初始化（无需额外配置，进度追踪自动工作）
    sg = SimpleGraph(config_path=Path("config/config.yaml"))
    await sg.start()
    
    # 提交任务
    task_id = await sg.submit_task("你的文本内容...")
    
    # 实时查看进度
    while True:
        progress = sg.get_task_progress(task_id)
        if not progress:
            break
        print(f"当前阶段: {progress['step']} - {progress['percentage']}%")
        
        status = sg.get_task_status(task_id)
        if status["status"] == "completed":
            break
        await asyncio.sleep(1)
    
    # 查看每个阶段的详细结果
    stage_results = sg.get_task_stage_results(task_id)
    print("System Update 结果:", stage_results["system_update"]["result"])
    print("Extraction 结果:", stage_results["extraction"]["result"])
    
    await sg.stop()

asyncio.run(main())
```

## 添加进度回调

```python
def progress_callback(task_id: str, step: str, data: dict):
    """实时接收进度更新"""
    print(f"[{step}] {data['message']} ({data.get('percentage', 0)}%)")
    
    # 阶段完成时会包含 result
    if "result" in data:
        print(f"  结果: {data['result']}")

sg = SimpleGraph(
    config_path=Path("config/config.yaml"),
    progress_callback=progress_callback  # 设置回调
)
```

## 查看阶段结果

### System Update 阶段

```python
system_result = stage_results["system_update"]["result"]
print("新增的类:", system_result["added_classes"])
print("增强的类:", system_result["enhanced_classes"])
```

### Extraction 阶段

```python
extraction_result = stage_results["extraction"]["result"]
print("提取的实体数:", extraction_result["entities_count"])
print("提取的关系数:", extraction_result["relationships_count"])

# 查看具体实体
for entity in extraction_result["entities"]:
    print(f"- {entity['name']}: {entity['classes']}")

# 查看具体关系
for rel in extraction_result["relationships"]:
    print(f"- {rel['source']} -> {rel['target']}: {rel['description']}")
```

## 阶段说明

| 阶段 | 说明 | 进度范围 |
|------|------|----------|
| `started` | 任务开始 | 0% |
| `system_update` | 分析文本并更新 System 类定义 | 10-30% |
| `extraction` | 提取实体和关系 | 50-80% |
| `completed` | 任务完成 | 100% |

## 完整示例

查看 `example_simplegraph.py` 获取更多示例：

```bash
# 运行基本示例
python example_simplegraph.py

# 查看详细进度追踪演示（取消注释相应行）
python example_simplegraph.py  # demo_progress_tracking()
```

## API 速查

```python
# 设置回调
sg.set_progress_callback(callback_function)

# 获取当前进度
progress = sg.get_task_progress(task_id)
# 返回: {"step": "extraction", "message": "...", "percentage": 50}

# 获取所有阶段结果
stage_results = sg.get_task_stage_results(task_id)
# 返回: {"system_update": {...}, "extraction": {...}}

# 获取单个阶段结果
task = sg.tasks[task_id]
system_result = task.get_stage_result("system_update")
extraction_result = task.get_stage_result("extraction")
```

## 注意事项

1. **回调函数应该快速返回**，避免阻塞任务执行
2. **阶段结果存储在内存中**，大量任务时注意内存使用
3. **回调是可选的**，不设置也能正常工作
4. **向后兼容**，所有旧代码无需修改

## 更多信息

- 详细文档：`PROGRESS_TRACKING.md`
- 架构变更：`REFACTOR_CHANGELOG.md`
- 完整示例：`example_simplegraph.py`
