"""
测试 Entity 自动绑定 Graph 的功能
"""

from src.models.entity import Entity, System, ClassDefinition, PropertyDefinition
from src.models.graph import Graph

# 创建一个 system
system = System.from_dict(
    {
        "classes": {
            "购物平台": {
                "description": "购物平台类",
                "properties": [
                    {"name": "成立时间", "required": False, "value_required": False},
                    {"name": "类型", "required": True, "value_required": True},
                ],
            },
            "公司": {"description": "公司类", "properties": []},
        }
    }
)

# 创建图
graph = Graph(system=system)

print("=" * 60)
print("测试1: 使用 Graph.create_entity() 创建实体（推荐方式）")
print("=" * 60)

# 方式1：使用 create_entity（自动绑定 graph）
entity1 = graph.create_entity(
    name="淘宝",
    description="阿里巴巴旗下的购物平台",
    class_names=["购物平台", "公司"],
    class_properties={"购物平台": {"成立时间": "2003", "类型": "综合电商"}},
)

print(f"实体名称: {entity1.name}")
print(f"实体描述: {entity1.description}")
print(f"实体类: {[c.class_name for c in entity1.classes]}")
print(f"是否绑定 Graph: {entity1.graph is not None}")
print(f"购物平台-成立时间: {entity1.get_property_value('购物平台', '成立时间').value}")
print(f"购物平台-类型: {entity1.get_property_value('购物平台', '类型').value}")

print("\n" + "=" * 60)
print("测试2: 传统方式 - 先创建 Entity，再添加到图")
print("=" * 60)

# 方式2：传统方式
entity2 = Entity(name="京东", description="京东购物平台")
print(f"创建后，绑定 Graph: {entity2.graph is not None}")  # 应该是 False

# 添加到图后会自动绑定
graph.add_entity(entity2)
print(f"添加到图后，绑定 Graph: {entity2.graph is not None}")  # 应该是 True

# 现在可以不传 system 参数
entity2.add_class("购物平台")  # 不需要传 system
entity2.set_property_value("购物平台", "类型", "综合电商")  # 不需要传 system

print(f"实体名称: {entity2.name}")
print(f"实体类: {[c.class_name for c in entity2.classes]}")
print(f"购物平台-类型: {entity2.get_property_value('购物平台', '类型').value}")

print("\n" + "=" * 60)
print("测试3: 动态添加类定义 + 创建实体")
print("=" * 60)

# 动态添加新类
graph.add_class_definition(
    ClassDefinition(
        name="社交平台",
        description="社交平台类",
        properties=[
            PropertyDefinition(name="用户数", required=False, value_required=False)
        ],
    )
)

# 立即可以使用新类
entity3 = graph.create_entity(
    name="小红书",
    description="社交购物平台",
    class_names=["购物平台", "社交平台"],
    class_properties={"购物平台": {"类型": "社交电商"}, "社交平台": {"用户数": "2亿"}},
)

print(f"实体名称: {entity3.name}")
print(f"实体类: {[c.class_name for c in entity3.classes]}")
print(f"购物平台-类型: {entity3.get_property_value('购物平台', '类型').value}")
print(f"社交平台-用户数: {entity3.get_property_value('社交平台', '用户数').value}")

print("\n" + "=" * 60)
print("测试4: 给已有实体添加新类")
print("=" * 60)

# 给已有实体添加新类
graph.add_class_to_entity("淘宝", "社交平台", {"用户数": "8亿"})

entity1_updated = graph.get_entity("淘宝")
print(f"实体名称: {entity1_updated.name}")
print(f"实体类: {[c.class_name for c in entity1_updated.classes]}")
print(
    f"社交平台-用户数: {entity1_updated.get_property_value('社交平台', '用户数').value}"
)

print("\n" + "=" * 60)
print("所有测试通过！")
print("=" * 60)
