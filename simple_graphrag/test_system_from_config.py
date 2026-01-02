"""
测试从 config.yaml 加载 System
"""

from pathlib import Path
from src.models.entity import System

# 加载配置
config_path = Path(__file__).parent / "config" / "config.yaml"

print("=" * 60)
print("测试：从 config.yaml 加载 base_system")
print("=" * 60)

# 加载 base_system
system = System.from_config_file(config_path, use_base_system=True)

print(f"\nSystem 名称: {system.name}")
print(f"System 包含类: {len(system.get_all_classes())} 个")
print(f"类列表: {system.get_all_classes()}")

print(f"\nSystem 包含预定义实体: {len(system.predefined_entities)} 个")
for entity in system.predefined_entities:
    print(f"  - {entity.name}: {entity.description} (类: {entity.classes})")

# 测试类定义
print("\n" + "=" * 60)
print("部分类定义详情")
print("=" * 60)

test_classes = ["用户", "可启动应用", "购物平台"]
for class_name in test_classes:
    class_def = system.get_class_definition(class_name)
    if class_def:
        print(f"\n类: {class_def.name}")
        print(f"  描述: {class_def.description}")
        print(f"  属性: {len(class_def.properties)} 个")
        for prop in class_def.properties:
            print(
                f"    - {prop.name} (必选: {prop.required}, 值必填: {prop.value_required})"
            )

print("\n" + "=" * 60)
print("测试通过！")
print("=" * 60)
