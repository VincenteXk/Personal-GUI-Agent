# 详细输出功能使用指南

## 新增功能

### 1. 📊 Graph.print_graph() - 打印图谱详情

新增的 `print_graph()` 方法可以详细展示当前图谱的所有数据。

#### 使用方法

```python
from pathlib import Path
from simplegraph import SimpleGraph

sg = SimpleGraph(config_path=Path("config/config.yaml"))
await sg.start()

# ... 处理任务 ...

# 打印图谱详情
sg.graph.print_graph()

# 或者只显示实体，不显示属性和关系
sg.graph.print_graph(show_properties=False, show_relationships=False)
```

#### 输出内容

```
================================================================================
📊 Graph 数据概览
================================================================================

📈 统计信息:
  • 实体数量: 10
  • 类节点数量: 15
  • 类定义数量: 5
  • 关系数量: 8
  • 总节点数: 30

📚 类定义 (5 个):
  • 应用
    描述: 软件应用程序
    属性: 名称, 类型, 开发商
  • 用户
    描述: 使用应用的用户
    属性: 姓名, 年龄

👥 实体 (10 个):

  🔹 抖音
    描述: 短视频社交平台
    类别: 应用
    [应用] 属性:
      - 名称: 抖音
      - 类型: 短视频
      - 开发商: 字节跳动

  🔹 小明
    描述: 用户
    类别: 用户
    [用户] 属性:
      - 姓名: 小明
      - 年龄: 25

🔗 关系 (8 个):
  • 小明 → 抖音 (x2)
    使用
  • 抖音 → 字节跳动
    开发者

================================================================================
```

#### 参数说明

- `show_properties` (bool, 默认True): 是否显示实体的属性值
- `show_relationships` (bool, 默认True): 是否显示关系

### 2. 🔍 任务阶段详细输出

每个任务在执行时会输出详细的阶段信息到日志。

#### System Update 阶段

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

### 3. 📞 增强的进度回调

进度回调现在包含更详细的信息。

#### 使用示例

```python
def detailed_progress_callback(task_id: str, step: str, data: dict):
    """详细的进度回调"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    message = data.get("message", "")
    percentage = data.get("percentage", 0)
    
    print(f"[{timestamp}] {step}: {message} ({percentage}%)")
    
    # 阶段结果详情
    if "result" in data:
        result = data["result"]
        
        if step == "system_update":
            # System更新结果
            added_detail = result.get("added_classes_detail", [])
            for cls in added_detail:
                print(f"  新增类: {cls['name']}")
                print(f"    属性: {', '.join(cls['properties'])}")
            
            enhanced_detail = result.get("enhanced_classes_detail", [])
            for cls in enhanced_detail:
                print(f"  增强类: {cls['name']}")
            
            print(f"  总类数: {result.get('total_classes_in_system', 0)}")
        
        elif step == "extraction":
            # 提取结果
            entities = result.get("entities", [])
            relationships = result.get("relationships", [])
            
            print(f"  实体: {len(entities)} 个")
            for entity in entities[:5]:  # 显示前5个
                props = entity.get("properties", {})
                print(f"    • {entity['name']} [{', '.join(entity['classes'])}]")
                # 显示属性
                for class_name, class_props in props.items():
                    for prop_name, prop_value in class_props.items():
                        if prop_value:
                            print(f"      {prop_name}: {prop_value}")
            
            print(f"  关系: {len(relationships)} 个")
            for rel in relationships[:5]:  # 显示前5个
                print(f"    • {rel['source']} → {rel['target']}")
                print(f"      {rel['description']}")

sg = SimpleGraph(
    config_path=config_path,
    progress_callback=detailed_progress_callback
)
```

### 4. 📋 阶段结果数据结构

#### System Update 阶段结果

```python
{
    "needed": True,  # 是否需要更新
    "added_classes": ["应用", "用户"],  # 新增的类名列表
    "enhanced_classes": ["公司"],  # 增强的类名列表
    "added_classes_detail": [  # 新增类的详细信息
        {
            "name": "应用",
            "description": "软件应用程序",
            "properties": ["名称", "类型", "开发商"]
        }
    ],
    "enhanced_classes_detail": [...],  # 增强类的详细信息
    "total_classes_in_system": 10,  # System中的总类数
    "details": "新增 2 个类, 增强 1 个类"
}
```

#### Extraction 阶段结果

```python
{
    "entities_count": 3,  # 实体数量
    "relationships_count": 2,  # 关系数量
    "entities": [  # 实体详情列表
        {
            "name": "抖音",
            "description": "短视频社交平台",
            "classes": ["应用"],
            "properties": {  # 按类分组的属性
                "应用": {
                    "名称": "抖音",
                    "类型": "短视频"
                }
            }
        }
    ],
    "relationships": [  # 关系详情列表
        {
            "source": "小明",
            "target": "抖音",
            "description": "使用",
            "count": 1
        }
    ],
    "entity_names": ["抖音", "小明", "张三的店"],  # 实体名称列表
    "entity_classes": ["应用", "用户", "商家"]  # 涉及的类列表
}
```

## 完整示例

```python
import asyncio
from pathlib import Path
from simplegraph import SimpleGraph
from datetime import datetime

def progress_callback(task_id, step, data):
    """进度回调"""
    icons = {
        "started": "▶️",
        "system_update": "🔧",
        "extraction": "🔍",
        "completed": "✅"
    }
    icon = icons.get(step, "•")
    print(f"{icon} {step}: {data['message']} ({data.get('percentage', 0)}%)")

async def main():
    # 初始化
    sg = SimpleGraph(
        config_path=Path("config/config.yaml"),
        progress_callback=progress_callback
    )
    await sg.start()
    
    # 提交任务
    task_id = await sg.submit_task(
        "小明在抖音上看到张三的店，用美团订了外卖。"
    )
    
    # 等待完成
    while sg.get_task_status(task_id)["status"] == "running":
        await asyncio.sleep(0.5)
    
    # 查看阶段结果
    stage_results = sg.get_task_stage_results(task_id)
    
    print("\n=== System Update 结果 ===")
    system_result = stage_results["system_update"]["result"]
    print(f"新增类: {system_result['added_classes']}")
    print(f"增强类: {system_result['enhanced_classes']}")
    
    print("\n=== Extraction 结果 ===")
    extraction_result = stage_results["extraction"]["result"]
    print(f"实体: {extraction_result['entity_names']}")
    print(f"关系数: {extraction_result['relationships_count']}")
    
    # 打印完整图谱
    print("\n=== 完整图谱 ===")
    sg.graph.print_graph()
    
    await sg.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

## 日志级别配置

要查看所有详细日志，确保日志级别设置为 INFO 或 DEBUG：

```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## 提示

1. **使用 print_graph() 查看最终结果**: 在所有任务完成后调用，可以看到完整的知识图谱
2. **使用进度回调实时监控**: 在任务执行过程中了解当前进度
3. **使用阶段结果分析**: 获取每个阶段的详细数据用于后续处理
4. **调整日志级别**: 根据需要调整日志详细程度
   - `DEBUG`: 最详细，包括所有调试信息
   - `INFO`: 适中，包括关键步骤和结果
   - `WARNING`: 仅警告和错误

## 性能考虑

- `print_graph()` 会遍历所有实体和关系，对于大型图谱可能较慢
- 详细的日志输出会增加一些开销，但通常可以忽略不计
- 阶段结果存储在内存中，大量任务时注意内存使用

---

更多信息请参考：

- `PROGRESS_TRACKING.md` - 进度追踪功能详细说明
- `example_simplegraph.py` - 完整示例代码
