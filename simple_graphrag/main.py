"""
简化版GraphRAG主入口
"""

import argparse
import os
from pathlib import Path
from src.database.manager import GraphDatabaseManager
from src.utils.logger import setup_logging, get_logger
from dotenv import load_dotenv
from src.models.graph import Graph

load_dotenv()

logger = get_logger(__name__)


def print_graph(graph: Graph):
    logger.info("=" * 50)
    logger.info("图统计信息")
    logger.info("=" * 50)
    logger.info(f"实体数量: {graph.get_entity_count()}")
    logger.info(f"关系数量: {graph.get_relationship_count()}")
    logger.info("=" * 50)
    logger.info("实体列表:")
    logger.info("=" * 50)
    for entity in graph.get_entities():
        class_names = [c.class_name for c in entity.classes]
        classes_str = f" (类: {', '.join(class_names)})" if class_names else ""
        logger.info(f"实体: {entity.name}{classes_str}: {entity.description}")
    logger.info("=" * 50)
    logger.info("关系列表:")
    logger.info("=" * 50)
    for relationship in graph.get_relationships():
        logger.info(
            f"关系: {relationship.source} -> {relationship.target} (次数: {relationship.count})"
        )
    logger.info("=" * 50)


def main():
    """主函数示例"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="简化版GraphRAG - 大模型支持的图数据库"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="启用详细日志输出（等同于设置 SIMPLERAG_VERBOSE=1）",
    )
    args = parser.parse_args()

    # 设置日志
    if args.verbose:
        os.environ["SIMPLERAG_VERBOSE"] = "1"
        logger.info("启用详细日志模式")

    setup_logging(verbose=args.verbose)

    # 配置文件路径
    config_path = Path(__file__).parent / "config" / "config.yaml"
    logger.info(f"使用配置文件: {config_path}")

    # 初始化数据库管理器
    manager = GraphDatabaseManager(config_path)

    # 示例1: 初始化数据库
    initial_text = """
我在小红书上拥有自己的一个账号，我经常通过小红书查找美妆教程，以及Lolita衣服，同时我喜欢在上面购买衣服。我拥有一个微信，微信号为"hymnly"，我喜欢在上面和我的一个朋友”Alice“聊天，但是他有一个小红书号，我们在小红书上也是朋友。我另有一个微信好友"Bob"他没有微信号
    """

    logger.info("=" * 50)
    logger.info("示例1: 初始化数据库")
    logger.info("=" * 50)
    graph = manager.initialize_database(initial_text)

    print_graph(graph)

    # 示例2: 增量更新数据库
    new_text = """
    微软公司在2023年发布了Windows 11操作系统。
    微软公司还开发了Azure云服务平台。
    萨提亚·纳德拉在2014年成为微软CEO。
    """

    logger.info("\n" + "=" * 50)
    logger.info("示例2: 增量更新数据库")
    logger.info("=" * 50)
    updated_graph = manager.incremental_update(new_text)

    print_graph(updated_graph)


if __name__ == "__main__":
    main()
