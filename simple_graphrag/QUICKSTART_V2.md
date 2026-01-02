# Simple GraphRAG V2 快速开始

## 安装依赖

```bash
# 安装必要的包
pip install openai pyyaml networkx
```

## 配置

### 1. 环境变量

创建 `.env` 文件：

```env
MIMO_API_KEY=your_api_key_here
```

### 2. 配置文件

查看 `config/config.yaml` 中的 `base_system` 配置：

- **classes**：预定义的类（用户、可启动应用、购物平台等）
- **entities**：预定义的实体（我、快手、抖音、小红书等）

## 使用方法

### 方式1：使用 Pipeline V2（推荐）

```python
from pathlib import Path
from simple_graphrag.pipeline_v2 import PipelineV2

# 初始化
config_path = Path("config/config.yaml")
pipeline = PipelineV2(config_path)

# 输入文本（支持单个文本或文本列表）
text = "我昨天在小红书上看到一个很有趣的视频，然后用微信分享给了我的朋友。"

# 运行（自动完成所有步骤）
graph = pipeline.run(text, visualize=True)

# 查看结果
print(f"实体: {graph.get_entity_count()} 个")
print(f"关系: {graph.get_relationship_count()} 个")
print(f"类: {len(graph.system.get_all_classes())} 个")
```

#### 处理多个文本（增量更新）

```python
# 输入文本列表
texts = [
    "我在小红书上看到一个AI绘图的视频，用微信分享给了朋友。",
    "我在Bilibili上看到书籍介绍，便在淘宝上购买了一本。",
    "我经常在抖音和快手上刷短视频。",
]

# 对每个文本依次执行完整流程（增量更新到同一个 Graph）
graph = pipeline.run(texts, visualize=True)

# 说明：
# 1. System 加载和 Graph 创建只执行一次
# 2. 对每个文本都会执行：检查扩展 System → 提取 → 融合
# 3. 所有更新都累积在同一个 Graph 上
# 4. System 会随着文本的处理逐步扩展（如果需要）
```

### 方式2：分步操作

```python
from pathlib import Path
from src.models.entity import System
from src.models.graph import Graph
from src.updaters.system_updater import SystemUpdater
from src.extractors.extractor import GraphExtractor
from src.combiners.combiner import Combiner
from src.llm.client import LLMClient

# Step 1: 加载预定义 System
system = System.from_config_file("config/config.yaml", use_base_system=True)
print(f"加载了 {len(system.get_all_classes())} 个类")
print(f"加载了 {len(system.predefined_entities)} 个预定义实体")

# Step 2: 创建 Graph（自动注入预定义实体）
graph = Graph(system=system, include_predefined_entities=True)
print(f"Graph 包含 {graph.get_entity_count()} 个实体（预定义）")

# Step 3: 初始化 LLM 客户端
llm_client = LLMClient(
    provider="ark",
    model="deepseek-v3-2-251201",
    base_url="https://ark.cn-beijing.volces.com/api/v3"
)

# Step 4: 增量扩展 System（如果需要）
text = "我在拼多多上买了一本书。"

updater = SystemUpdater(llm_client)
system, changes = updater.check_and_update(system, text, auto_apply=True)

if changes["needed"]:
    print(f"System 已扩展:")
    print(f"  新增类: {changes['added_classes']}")
    print(f"  增强类: {changes['enhanced_classes']}")

# Step 5: 提取实体和关系
extractor = GraphExtractor(
    llm_client=llm_client,
    prompt_template_path=Path("config/prompts/extract_graph.txt"),
    classes=system.get_all_classes(),
    system=system,
    base_entities=[
        {"name": e.name, "description": e.description, "classes": e.classes}
        for e in system.predefined_entities
    ]
)

entities, relationships = extractor.extract(text)
print(f"提取了 {len(entities)} 个实体, {len(relationships)} 个关系")

# Step 6: 融合到 Graph
combiner = Combiner(graph, strict_validation=False)
stats = combiner.combine(entities, relationships)

print(f"融合完成:")
print(f"  实体: 新增 {stats['entities']['added']}, 更新 {stats['entities']['updated']}")
print(f"  关系: 新增 {stats['relationships']['added']}, 更新 {stats['relationships']['updated']}")

# Step 7: 保存
graph.save("output/graph.pkl")
print("Graph 已保存")
```

### 方式3：直接操作 Graph

```python
from src.models.entity import System, ClassDefinition, PropertyDefinition
from src.models.graph import Graph

# 创建 System
system = System()
system.add_class_definition(ClassDefinition(
    name="购物平台",
    description="可以用来购物的平台",
    properties=[
        PropertyDefinition(name="类型", required=False, value_required=False)
    ]
))

# 创建 Graph
graph = Graph(system=system)

# 创建实体（方式1：使用 Graph.create_entity）
taobao = graph.create_entity(
    name="淘宝",
    description="综合电商平台",
    class_names=["购物平台"],
    class_properties={"购物平台": {"类型": "综合电商"}}
)

# 创建实体（方式2：传统方式）
jd = Entity(name="京东", description="京东商城")
graph.add_entity(jd)  # 自动绑定
jd.add_class("购物平台")  # 不需要传 system
jd.set_property_value("购物平台", "类型", "综合电商")  # 不需要传 system

# 添加关系
from src.models.relationship import Relationship

graph.add_relationship(Relationship(
    source="淘宝",
    target="京东",
    description="竞争关系",
    strength=8
))

# 保存
graph.save("output/my_graph.pkl")
```

## 增量更新

```python
# 第一次运行
text1 = "我在淘宝上买了一本书。"
graph = pipeline.run(text1)
graph.save("output/graph.pkl")

# 第二次运行（增量更新）
graph = Graph.load("output/graph.pkl")  # 加载现有 graph（包含 system）

# 创建新 pipeline，复用现有 graph
pipeline2 = PipelineV2(config_path)
# 手动设置 system 和 graph
system = graph.system
# ... 运行 step2-step5 ...

text2 = "我在京东上买了一部手机。"
# 提取和融合会自动增量更新到 graph
```

## 测试

```bash
# 测试 System 加载
python test_system_from_config.py

# 测试 Entity 绑定
python test_entity_graph_binding.py

# 运行 Pipeline V2
python pipeline_v2.py
```

## 常见问题

### Q: 如何添加新的类定义？

```python
# 方式1：在 config.yaml 中定义
base_system:
  classes:
    新类名:
      description: "描述"
      properties:
        - name: "属性名"
          required: false
          value_required: false

# 方式2：代码中动态添加
graph.add_class_definition(ClassDefinition(
    name="新类名",
    description="描述",
    properties=[...]
))
```

### Q: 如何查看 Graph 中的实体和关系？

```python
# 查看所有实体
for entity in graph.get_entities():
    print(f"{entity.name}: {entity.description}")
    print(f"  类: {[c.class_name for c in entity.classes]}")

# 查看所有关系
for rel in graph.get_relationships():
    print(f"{rel.source} -> {rel.target}: {rel.description}")
```

### Q: 如何修改实体的类或属性？

```python
# 实体已经在 graph 中，自动绑定了
entity = graph.get_entity("淘宝")

# 添加新类
entity.add_class("社交平台")

# 修改属性
entity.set_property_value("购物平台", "类型", "新值")
```

### Q: System 动态扩展后，现有实体会自动更新吗？

不会。System 动态扩展只影响**新创建**的实体。

如果需要给现有实体添加新类：

```python
graph.add_class_to_entity("淘宝", "新类名", {"属性": "值"})
```

## 参考文档

- `ARCHITECTURE_V2.md` - 详细架构说明
- `REFACTOR_SUMMARY.md` - 重构总结
- `ENTITY_GRAPH_BINDING.md` - Entity 绑定机制
