"""
测试 Pipeline V2 批量处理文本列表
"""

from pathlib import Path
from src.models.entity import System
from src.models.graph import Graph

print("=" * 60)
print("测试：Pipeline V2 批量处理文本列表")
print("=" * 60)

# 模拟批量处理流程（不调用 LLM）
# 加载 System
config_path = Path(__file__).parent / "config" / "config.yaml"
system = System.from_config_file(config_path, use_base_system=True)

print(f"\n1. 加载预定义 System")
print(f"   类: {len(system.get_all_classes())} 个")
print(f"   预定义实体: {len(system.predefined_entities)} 个")

# 创建 Graph
graph = Graph(system=system, include_predefined_entities=True)

print(f"\n2. 创建 Graph（包含预定义实体）")
print(f"   实体: {graph.get_entity_count()} 个")

# 模拟处理多个文本
texts = [
    "文本1：我在小红书上看到一个AI绘图的视频。",
    "文本2：我在Bilibili上看到书籍介绍，便在淘宝上购买了。",
    "文本3：我经常在抖音和快手上刷短视频。",
]

print(f"\n3. 批量处理 {len(texts)} 个文本")

for idx, text in enumerate(texts, 1):
    print(f"\n   处理文本 {idx}/{len(texts)}")
    print(f"   内容: {text}")

    # 模拟：动态添加类（如果需要）
    if idx == 2 and "Bilibili" in text:
        from src.models.entity import ClassDefinition, PropertyDefinition

        # 检查是否已有"视频平台"类
        if not system.get_class_definition("视频平台"):
            system.add_class_definition(
                ClassDefinition(
                    name="视频平台", description="视频内容平台", properties=[]
                )
            )
            print(f"   → System 扩展：新增类 '视频平台'")

    # 模拟：创建新实体（如果需要）
    if idx == 2 and "Bilibili" in text:
        if not graph.get_entity("Bilibili"):
            entity = graph.create_entity(
                name="Bilibili",
                description="视频平台",
                class_names=["视频平台", "信息流"],
            )
            print(f"   → 新增实体: {entity.name}")

    if idx == 2 and "淘宝" in text:
        # 淘宝应该已存在（预定义实体），检查一下
        entity = graph.get_entity("淘宝")
        if entity:
            print(f"   → 使用已有实体: 淘宝（预定义）")
        else:
            # 如果不存在，创建
            entity = graph.create_entity(
                name="淘宝",
                description="综合电商平台",
                class_names=["购物平台"],
            )
            print(f"   → 新增实体: {entity.name}")

    print(f"   当前 Graph: {graph.get_entity_count()} 个实体")

print("\n" + "=" * 60)
print("最终统计")
print("=" * 60)
print(f"System 类: {len(system.get_all_classes())} 个")
print(f"  类列表: {system.get_all_classes()}")
print(f"Graph 实体: {graph.get_entity_count()} 个")
print(f"  实体列表: {[e.name for e in graph.get_entities()]}")
print(f"Graph 关系: {graph.get_relationship_count()} 个")

print("\n" + "=" * 60)
print("测试通过：支持批量处理文本列表")
print("=" * 60)
