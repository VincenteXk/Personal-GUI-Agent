# Simple GraphRAG Architecture V2

## 核心概念

### 1. System（系统架构定义）

**System** 是"系统"的抽象架构定义，包含：

- **类定义（ClassDefinition）**：类名、描述、属性定义列表
- **预定义实体（PredefinedEntity）**：预先配置的实体及其类归属

#### 关键特性

- **单调可扩展**：只能新增/增强类定义，不能删除
- **可实例化**：每个 Graph 绑定一个 System 实例
- **可从 Config 加载**：`System.from_config_file(config_path, use_base_system=True)`

```python
# 从 config.yaml 加载
system = System.from_config_file("config/config.yaml", use_base_system=True)

# 动态扩展
system.add_class_definition(ClassDefinition(
    name="新类",
    description="...",
    properties=[...]
))
```

### 2. Graph（具体实例）

**Graph** 使用某个 System，形成具体实例，包含：

- **实体（Entity）**：中心节点，拥有名称、描述、类实例列表
- **类节点（ClassNode）**：实体:类节点（如"小红书:购物平台"）
- **类主节点（ClassMasterNode）**：类本身（如"购物平台"），从 system 派生
- **关系（Relationship）**：连接任意节点

#### 关键特性

- **绑定 System**：`Graph(system=my_system)`
- **自动注入预定义实体**：`Graph(system, include_predefined_entities=True)`
- **保存/加载包含 System**：`graph.save(path)` / `Graph.load(path)`

```python
# 创建 Graph
graph = Graph(system=system, include_predefined_entities=True)

# 实体自动绑定 graph
entity = graph.create_entity(
    name="淘宝",
    class_names=["购物平台"],
    class_properties={"购物平台": {"类型": "电商"}}
)

# 后续操作自动使用 graph.system
entity.add_class("社交平台")  # ✓ 不需要传 system
```

### 3. Entity（实体）

**Entity** 表示知识图谱中的中心节点，持有对 Graph 的引用。

#### 自动绑定机制

- `Graph.add_entity(entity)` 自动设置 `entity._graph = self`
- `Entity.add_class()` / `set_property_value()` 自动使用 `entity._graph.system`

```python
# 方式1：Graph.create_entity()（推荐）
entity = graph.create_entity("微信", "社交平台", ["交流平台"])

# 方式2：传统方式
entity = Entity(name="微信", description="社交平台")
graph.add_entity(entity)  # 自动绑定
entity.add_class("交流平台")  # ✓ 自动使用 graph.system
```

## 新流程架构

### Pipeline V2 工作流程

```
┌─────────────────────────────────────────────────────────┐
│ 1. 从 config.yaml 加载预定义 System (base_system)      │
│    - 8 个预定义类（用户、可启动应用、购物平台等）       │
│    - 9 个预定义实体（我、快手、抖音、小红书等）         │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ 2. 创建 Graph(system)                                   │
│    - 自动注入预定义实体到图中                            │
│    - 实体自动绑定 graph                                  │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ 3. SystemUpdater：增量扩展 System                       │
│    - 检查现有 System 是否能囊括输入文本                  │
│    - 如需扩展，调用 LLM 生成增量 YAML                    │
│    - 应用到 System（add_class_definition）               │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ 4. GraphExtractor：提取实体和关系                       │
│    - 基于 System 的类定义提取                            │
│    - 返回 Entity 和 Relationship 列表                    │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ 5. Combiner：融合到 Graph                               │
│    - 去重：相同名称的实体合并类和属性                    │
│    - 增量：添加新实体、新关系                            │
│    - 校验：确保符合 graph.system 定义                    │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ 6. 保存 Graph 和可视化                                  │
│    - graph.save() 包含 system 和所有节点/关系            │
│    - 生成 HTML 可视化                                    │
└─────────────────────────────────────────────────────────┘
```

## 核心组件

### SystemUpdater

**职责**：增量扩展 System

```python
updater = SystemUpdater(llm_client)
system, changes = updater.check_and_update(system, text, auto_apply=True)

# changes = {
#     "needed": True,
#     "added_classes": ["新类1", "新类2"],
#     "enhanced_classes": ["已有类1"],
#     "details": "原因说明"
# }
```

**工作流程**：

1. 生成 System 的 YAML 表示
2. 调用 LLM 检查是否需要扩展
3. 如需扩展，生成增量 YAML 配置
4. 解析并应用到 System

### GraphExtractor

**职责**：从文本提取实体和关系

```python
extractor = GraphExtractor(
    llm_client=llm_client,
    prompt_template_path=prompt_path,
    classes=system.get_all_classes(),
    system=system,
    ...
)

entities, relationships = extractor.extract(text)
```

**特点**：

- 基于 System 的类定义提取
- 三步提取：实体 → 类属性 → 关系
- 返回标准 Entity 和 Relationship 对象

### Combiner

**职责**：融合实体和关系到 Graph

```python
combiner = Combiner(graph, strict_validation=False)
stats = combiner.combine(entities, relationships)

# stats = {
#     "entities": {"added": 3, "updated": 2, "failed": 0},
#     "relationships": {"added": 5, "updated": 1, "failed": 0}
# }
```

**特点**：

- 利用 Graph.add_entity() 的内置去重/合并逻辑
- 提供详细统计信息
- 可选严格校验模式

## 使用示例

### 快速开始

```python
from pathlib import Path
from simple_graphrag.pipeline_v2 import PipelineV2

# 初始化
config_path = Path("config/config.yaml")
pipeline = PipelineV2(config_path)

# 运行
text = "我昨天在小红书上看到一个有趣的视频，然后用微信分享给了朋友。"
graph = pipeline.run(text, visualize=True)

# 结果
print(f"实体: {graph.get_entity_count()} 个")
print(f"关系: {graph.get_relationship_count()} 个")
print(f"类: {len(graph.system.get_all_classes())} 个")
```

### 增量更新示例

```python
# 第一次运行
text1 = "我在淘宝上买了一本书。"
graph = pipeline.run(text1)

# 保存
graph.save("output/graph.pkl")

# 第二次运行（增量更新）
graph = Graph.load("output/graph.pkl")  # 加载现有 graph（含 system）
pipeline.graph = graph  # 复用现有 graph

text2 = "我在京东上买了一部手机。"
graph = pipeline.run(text2)  # 增量添加
```

## Config.yaml 结构

```yaml
# 基础系统架构
base_system:
  classes:
    用户:
      description: "用户本人，执行操作的主体"
      properties: []
    可启动应用:
      description: "可以被启动的应用程序"
      properties:
        - name: "启动方式"
          required: true
          value_required: true
          description: "应用的启动方式"
    # ... 更多类

  # 预定义实体
  entities:
    - name: "我"
      description: "用户本人"
      classes: ["用户"]
    - name: "快手"
      description: "短视频平台"
      classes: ["可启动应用", "视频平台", "信息流"]
    # ... 更多预定义实体
```

## 关键优化

1. **System 可实例化**：不再是全局单例，每个 Graph 绑定独立 System
2. **Entity 自动绑定 Graph**：简化 API，无需显式传 system
3. **System 动态扩展**：支持增量添加类定义，立即生效
4. **预定义实体自动注入**：Graph 创建时可选注入 system.predefined_entities
5. **单一真相源**：Graph 不缓存"类本身"，每次直接查 system
6. **保存/加载包含 System**：graph.save() 包含完整 system 定义

## 测试

- **test_system_from_config.py**：测试从 config.yaml 加载 System
- **test_entity_graph_binding.py**：测试 Entity 自动绑定 Graph
- **pipeline_v2.py**：完整流水线示例

## 向后兼容

- 旧的 `Graph.load()` 可以加载包含 `class_definitions` 的旧文件
- Entity 仍然支持显式传 `system` 参数（优先级更高）
- 保留 `ClassConfig` 兼容接口（内部调用 System）
