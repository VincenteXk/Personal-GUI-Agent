"""
实体属性功能示例

演示如何使用新的类-属性系统创建实体
"""

from pathlib import Path
from src.models.entity import Entity
from src.models.graph import Graph
from src.database.manager import GraphDatabaseManager
from src.utils.logger import setup_logging, get_logger
from dotenv import load_dotenv

load_dotenv()
setup_logging(verbose=True)
logger = get_logger(__name__)


def example_entity_properties():
    """演示实体属性的使用"""

    # 加载配置（会自动加载类定义）
    config_path = Path(__file__).parent / "config" / "config.yaml"
    manager = GraphDatabaseManager(config_path)

    # 创建图
    graph = Graph(system=manager.system, include_predefined_entities=True)

    # 方式1：使用 Graph.create_entity() 创建并自动加入图（推荐，简洁）
    xiaohongshu = graph.create_entity(
        name="小红书",
        description="一个集购物、社交和信息流于一体的应用平台",
        class_names=["可启动应用", "交流平台", "信息流", "购物平台"],
        class_properties={
            "可启动应用": {"启动方式": "点击应用图标启动"},
            "购物平台": {"偏好": "偏向女装、时尚生活类的购物平台"},
        },
    )

    # 方式2：传统方式 - 先创建实体，再添加到图（会自动绑定 graph）
    pinduoduo = Entity(
        name="拼多多",
        description="以性价比为亮点的生活百货购物平台",
    )
    # 添加到图后，实体会自动绑定 graph，后续操作自动使用 graph.system
    graph.add_entity(pinduoduo)

    # 现在可以直接操作，不需要传 system 参数（自动使用 graph.system）
    pinduoduo.add_class("购物平台")
    pinduoduo.set_property_value(
        "购物平台",
        "偏好",
        value="以性价比为亮点的生活百货购物平台",
    )

    # 打印实体信息
    logger.info("=" * 60)
    logger.info("实体类-属性示例")
    logger.info("=" * 60)

    for entity in graph.get_entities():
        logger.info(f"\n实体名称: {entity.name}")
        logger.info(f"实体描述: {entity.description}")
        logger.info(f"实体类: {[c.class_name for c in entity.classes]}")

        for class_instance in entity.classes:
            logger.info(f"\n  类: {class_instance.class_name}")
            for prop_name, prop_value in class_instance.properties.items():
                prop_info = f"    属性: {prop_name}"
                if prop_value.value:
                    prop_info += f" = {prop_value.value}"
                logger.info(prop_info)

    # 演示添加类
    logger.info("\n" + "=" * 60)
    logger.info("演示：为拼多多添加'可启动应用'类")
    logger.info("=" * 60)

    try:
        pinduoduo_entity = graph.get_entity("拼多多")
        if pinduoduo_entity:
            pinduoduo_entity.add_class("可启动应用")
            pinduoduo_entity.set_property_value(
                "可启动应用", "启动方式", value="点击应用图标启动"
            )
            logger.info(
                f"成功添加类！现在拼多多的类为: {[c.class_name for c in pinduoduo_entity.classes]}"
            )
    except ValueError as e:
        logger.error(f"添加类失败: {e}")

    # 演示属性验证
    logger.info("\n" + "=" * 60)
    logger.info("演示：尝试创建缺少必选属性的实体")
    logger.info("=" * 60)

    try:
        invalid_entity = Entity(
            name="测试应用",
            description="测试实体",
        )
        invalid_entity.add_class("可启动应用", system=graph.system)
        # 不设置必选属性"启动方式"，应该会失败
        graph.add_entity(invalid_entity)
    except ValueError as e:
        logger.error(f"创建实体失败（预期行为）: {e}")

    # 查看类配置信息
    logger.info("\n" + "=" * 60)
    logger.info("类配置信息")
    logger.info("=" * 60)

    for class_name in graph.system.get_all_classes():
        class_def = graph.system.get_class_definition(class_name)
        if class_def:
            logger.info(f"\n类: {class_name}")
            logger.info(f"  描述: {class_def.description}")
            logger.info(f"  属性:")
            for prop_def in class_def.properties:
                required_str = "必选" if prop_def.required else "可选"
                value_required_str = "值必填" if prop_def.value_required else "值可选"
                logger.info(
                    f"    - {prop_def.name} ({required_str}, {value_required_str})"
                )
                if prop_def.description:
                    logger.info(f"      描述: {prop_def.description}")


if __name__ == "__main__":
    example_entity_properties()
