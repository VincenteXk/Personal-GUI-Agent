# 功能增强总结 - 详细输出

## 更新日期: 2025-12-31

## ✅ 完成的功能

### 1. 📊 为 Graph 添加 print_graph() 方法

**位置**: `src/models/graph.py`

**功能**: 详细打印图谱的所有数据，包括：

- 统计信息（实体、类节点、关系数量）
- 所有类定义及其属性
- 所有实体及其类别和属性值
- 所有关系及其描述

**使用方法**:

```python
sg.graph.print_graph()  # 显示所有信息
sg.graph.print_graph(show_properties=False)  # 不显示属性
sg.graph.print_graph(show_relationships=False)  # 不显示关系
```

**输出示例**:

```
================================================================================
📊 Graph 数据概览
================================================================================

📈 统计信息:
  • 实体数量: 10
  • 类节点数量: 15
  • 类定义数量: 5
  • 关系数量: 8

📚 类定义 (5 个):
  • 应用
    描述: 软件应用程序
    属性: 名称, 类型, 开发商

👥 实体 (10 个):
  🔹 抖音
    描述: 短视频社交平台
    类别: 应用
    [应用] 属性:
      - 名称: 抖音
      - 类型: 短视频

🔗 关系 (8 个):
  • 小明 → 抖音
    使用
```

### 2. 🔍 增强任务阶段的详细输出

**位置**: `simplegraph.py` 的 `_run_task()` 方法

**改进内容**:

#### System Update 阶段

- ✅ 输出任务ID和输入文本摘要
- ✅ 显示是否需要更新System
- ✅ 详细列出新增的类及其描述和属性
- ✅ 详细列出增强的类及其描述和属性
- ✅ 保存完整的类详情到阶段结果

**日志输出示例**:

```
[任务 a1b2c3d4] 🔧 开始System更新阶段
[任务 a1b2c3d4] 输入文本: 我在抖音上刷到一家网红餐厅...
[任务 a1b2c3d4] ✅ System更新完成:
  ✨ 新增类: 应用
     描述: 软件应用程序
     属性: 名称, 类型, 开发商
  🔧 增强类: 用户
     描述: 使用应用的用户
     属性: 姓名, 年龄, 偏好
```

#### Extraction 阶段

- ✅ 详细列出每个提取的实体
- ✅ 显示实体的类别和描述
- ✅ 显示实体的属性值
- ✅ 详细列出每个提取的关系
- ✅ 保存完整的实体和关系详情到阶段结果

**日志输出示例**:

```
[任务 a1b2c3d4] 🔍 开始实体和关系提取阶段
[任务 a1b2c3d4] ✅ 提取完成:
  📦 提取到 3 个实体:
     • 抖音 [应用]
       描述: 短视频社交平台
       属性: 名称=抖音, 类型=短视频
     • 小明 [用户]
       描述: 用户
       属性: 姓名=小明
     • 张三的店 [商家]
       描述: 网红餐厅
  🔗 提取到 2 个关系:
     • 小明 → 抖音
       使用
     • 小明 → 张三的店
       订购
```

### 3. 📞 增强进度回调的输出

**位置**: `example_simplegraph.py`

**改进内容**:

- ✅ 添加图标表示不同阶段
- ✅ 显示新增类的详细信息（包括属性）
- ✅ 显示提取的实体列表（前几个）
- ✅ 显示提取的关系列表（前几个）

**回调输出示例**:

```
[10:30:15] 🔧 任务 a1b2c3d4 | system_update: System更新完成 (30%)
           └─ 新增类: 2, 增强类: 1
              • 应用: 名称, 类型, 开发商
              • 用户: 姓名, 年龄

[10:30:20] 🔍 任务 a1b2c3d4 | extraction: 提取完成 (80%)
           └─ 提取: 3 个实体, 2 个关系
              • 抖音 [应用]
              • 小明 [用户]
              • 张三的店 [商家]
              • 小明 → 抖音
              • 小明 → 张三的店
```

## 📊 增强的数据结构

### System Update 阶段结果

**新增字段**:

```python
{
    "needed": True,  # 新增：是否需要更新
    "added_classes_detail": [  # 新增：详细的类信息
        {
            "name": "应用",
            "description": "软件应用程序",
            "properties": ["名称", "类型", "开发商"]
        }
    ],
    "enhanced_classes_detail": [...],  # 新增：增强类的详细信息
    "total_classes_in_system": 10,  # 新增：System中的总类数
    # ... 原有字段保持不变
}
```

### Extraction 阶段结果

**增强字段**:

```python
{
    "entities": [  # 增强：现在包含完整的属性信息
        {
            "name": "抖音",
            "description": "短视频社交平台",
            "classes": ["应用"],
            "properties": {  # 新增：按类分组的属性
                "应用": {
                    "名称": "抖音",
                    "类型": "短视频"
                }
            }
        }
    ],
    "relationships": [  # 增强：现在包含 count 字段
        {
            "source": "小明",
            "target": "抖音",
            "description": "使用",
            "count": 1  # 新增
        }
    ],
    "entity_names": ["抖音", "小明"],  # 新增：实体名称列表
    "entity_classes": ["应用", "用户"]  # 新增：涉及的类列表
}
```

## 📝 修改的文件

1. **`src/models/graph.py`**
   - 新增 `print_graph()` 方法（约60行）

2. **`simplegraph.py`**
   - 增强 `_run_task()` 方法中的两个阶段输出
   - System Update 阶段：增加详细日志和结果数据（约40行）
   - Extraction 阶段：增加详细日志和结果数据（约50行）

3. **`example_simplegraph.py`**
   - 增强 `progress_callback()` 函数，显示更详细的信息（约30行）

4. **新增文档**
   - `DETAILED_OUTPUT_GUIDE.md` - 详细输出功能使用指南

## 🎯 使用场景

### 1. 开发调试

```python
# 查看详细的任务执行过程
sg = SimpleGraph(config_path=path, progress_callback=detailed_callback)
await sg.start()
task_id = await sg.submit_task(text)
# 日志会自动输出详细信息
```

### 2. 结果分析

```python
# 分析每个阶段的结果
stage_results = sg.get_task_stage_results(task_id)
system_result = stage_results["system_update"]["result"]
extraction_result = stage_results["extraction"]["result"]

# 查看提取了哪些实体
for entity in extraction_result["entities"]:
    print(f"{entity['name']}: {entity['classes']}")
    print(f"  属性: {entity['properties']}")
```

### 3. 图谱展示

```python
# 处理完所有任务后，查看完整图谱
await sg.stop()
sg.graph.print_graph()
```

## ✨ 特点

1. **信息丰富**: 每个阶段都输出关键信息，便于理解任务执行过程
2. **易于阅读**: 使用图标和缩进，输出清晰美观
3. **可定制**: 可以通过参数控制显示内容
4. **向后兼容**: 不影响现有功能，原有代码无需修改
5. **性能友好**: 详细输出仅在需要时生成，不影响核心性能

## 🔧 配置建议

### 开发环境

```python
import logging
logging.basicConfig(level=logging.INFO)  # 查看详细日志

sg = SimpleGraph(
    config_path=path,
    progress_callback=detailed_progress_callback  # 使用详细回调
)
```

### 生产环境

```python
logging.basicConfig(level=logging.WARNING)  # 减少日志输出

sg = SimpleGraph(
    config_path=path,
    progress_callback=simple_progress_callback  # 使用简单回调
)
```

## 📖 相关文档

- `DETAILED_OUTPUT_GUIDE.md` - 详细输出功能使用指南
- `PROGRESS_TRACKING.md` - 进度追踪功能说明
- `example_simplegraph.py` - 完整示例代码

## 🧪 测试

所有修改已通过语法检查：

```bash
python -m py_compile simplegraph.py
python -m py_compile src/models/graph.py
python -m py_compile example_simplegraph.py
```

## 🚀 快速开始

```python
import asyncio
from pathlib import Path
from simplegraph import SimpleGraph

async def main():
    sg = SimpleGraph(config_path=Path("config/config.yaml"))
    await sg.start()
    
    task_id = await sg.submit_task("你的文本...")
    
    # 等待完成
    while sg.get_task_status(task_id)["status"] not in ["completed", "failed"]:
        await asyncio.sleep(1)
    
    # 打印图谱
    sg.graph.print_graph()
    
    await sg.stop()

asyncio.run(main())
```

---

**实现者**: AI Assistant  
**日期**: 2025-12-31  
**版本**: v2.1
