"""
测试分组逻辑 - 验证每个实体是否有唯一的 group ID
"""

from graph_visualizer import GraphVisualizer
from src.models.graph import Graph
from src.models.entity import Entity
from src.models.entity import ClassInstance
from src.models.entity import System
from pathlib import Path

# 创建一个测试图
system = System.from_dict(
    {
        "classes": {
            "类A": {"description": "测试类A", "properties": []},
            "类B": {"description": "测试类B", "properties": []},
            "类C": {"description": "测试类C", "properties": []},
        }
    }
)
graph = Graph(system=system)

# 添加几个测试实体
entity1 = Entity(name="实体1", description="测试实体1", classes=[ClassInstance("类A")])
entity2 = Entity(name="实体2", description="测试实体2", classes=[ClassInstance("类B")])
entity3 = Entity(name="实体3", description="测试实体3", classes=[ClassInstance("类C")])

graph.add_entity(entity1)
graph.add_entity(entity2)
graph.add_entity(entity3)

# 创建可视化器
gv = GraphVisualizer(title="分组测试")

# 为每个实体分配唯一的 group ID
entity_group_map = {}
current_group = 1

entities = graph.get_entities()
print(f"处理 {len(entities)} 个实体...")

for entity in entities:
    entity_group_map[entity.name] = current_group
    print(f"  实体 '{entity.name}' -> Group ID: {current_group}")
    current_group += 1

    # 添加实体节点
    gv.add_node(
        node_id=entity.name,
        label=entity.name,
        group=entity_group_map[entity.name],
        size=18,
        description=entity.description,
        node_type="entity",
    )

    # 添加类节点
    class_nodes = graph.get_class_nodes(entity.name)
    for class_node in class_nodes:
        print(
            f"    类节点 '{class_node.node_id}' -> Group ID: {entity_group_map[entity.name]}"
        )
        gv.add_node(
            node_id=class_node.node_id,
            label=f"{class_node.entity_name}:{class_node.class_name}",
            group=entity_group_map[entity.name],  # 与实体使用相同的 group ID
            size=12,
            description=class_node.description,
            node_type="class_node",
        )

# 检查所有节点的 group ID
print("\n所有节点的 Group ID 分配:")
for node in gv.nodes:
    print(f"  {node['id']}: Group {node['group']}")

# 检查是否有重复的 group ID（对于不同的实体）
entity_groups = {}
for node in gv.nodes:
    if node.get("node_type") == "entity":
        entity_name = node["id"]
        group_id = node["group"]
        if group_id in entity_groups:
            print(f"\n警告: Group ID {group_id} 被多个实体使用!")
            print(f"  - {entity_groups[group_id]}")
            print(f"  - {entity_name}")
        else:
            entity_groups[group_id] = entity_name

print(f"\n总结: 共 {len(entity_groups)} 个不同的实体分组")
