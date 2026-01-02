"""
Combiner：融合实体和关系到图

职责：
1. 接收一个现有 Graph 和新的实体/关系列表
2. 去重：相同名称的实体合并类和属性
3. 增量：添加新实体、新关系
4. 校验：确保所有实体符合 graph.system 的定义
"""

from typing import List
from ..models.entity import Entity
from ..models.relationship import Relationship
from ..models.graph import Graph
from ..utils.logger import get_logger

logger = get_logger(__name__)


class Combiner:
    """
    Combiner：融合实体和关系到图

    核心逻辑：
    - Graph 内部已经实现了 add_entity() 的去重/合并逻辑
    - Combiner 只需批量调用 add_entity() 和 add_relationship()
    - 提供统计信息和日志输出
    """

    def __init__(self, graph: Graph, strict_validation: bool = True):
        """
        初始化 Combiner

        Args:
            graph: 要融合到的目标图
            strict_validation: 是否严格校验实体类/属性（默认 True）
        """
        self.graph = graph
        self.strict_validation = strict_validation

    def combine_entities(self, entities: List[Entity]) -> dict:
        """
        融合实体到图

        Args:
            entities: 要融合的实体列表

        Returns:
            统计信息字典 {added: 新增数量, updated: 更新数量, failed: 失败数量}
        """
        logger.info(f"开始融合 {len(entities)} 个实体到图")

        stats = {"added": 0, "updated": 0, "failed": 0}

        for entity in entities:
            try:
                # 检查实体是否已存在
                existing = self.graph.get_entity(entity.name)

                # Graph.add_entity() 内部会处理去重/合并逻辑
                self.graph.add_entity(entity, strict_validation=self.strict_validation)

                if existing:
                    stats["updated"] += 1
                    logger.debug(f"更新实体: {entity.name}")
                else:
                    stats["added"] += 1
                    logger.debug(f"新增实体: {entity.name}")

            except Exception as e:
                stats["failed"] += 1
                logger.warning(f"融合实体失败 '{entity.name}': {e}")

        logger.info(
            f"实体融合完成: 新增 {stats['added']} 个, 更新 {stats['updated']} 个, 失败 {stats['failed']} 个"
        )
        return stats

    def combine_relationships(self, relationships: List[Relationship]) -> dict:
        """
        融合关系到图

        Args:
            relationships: 要融合的关系列表

        Returns:
            统计信息字典 {added: 新增数量, updated: 更新数量, failed: 失败数量}
        """
        logger.info(f"开始融合 {len(relationships)} 个关系到图")

        stats = {"added": 0, "updated": 0, "failed": 0}

        for relationship in relationships:
            try:
                # 检查关系是否已存在（包括 refer 字段）
                new_refer_set = set([r.upper() for r in relationship.refer])
                existing = any(
                    rel.source.upper() == relationship.source.upper()
                    and rel.target.upper() == relationship.target.upper()
                    and rel.description == relationship.description
                    and set([r.upper() for r in rel.refer])
                    == new_refer_set  # refer 必须相同
                    for rel in self.graph.get_relationships()
                )

                # Graph.add_relationship() 内部会处理去重/更新强度
                self.graph.add_relationship(relationship)

                if existing:
                    stats["updated"] += 1
                    logger.debug(
                        f"更新关系: {relationship.source} -> {relationship.target}"
                    )
                else:
                    stats["added"] += 1
                    logger.debug(
                        f"新增关系: {relationship.source} -> {relationship.target}"
                    )

            except Exception as e:
                stats["failed"] += 1
                logger.warning(
                    f"融合关系失败 '{relationship.source} -> {relationship.target}': {e}"
                )

        logger.info(
            f"关系融合完成: 新增 {stats['added']} 个, 更新 {stats['updated']} 个, 失败 {stats['failed']} 个"
        )
        return stats

    def combine(
        self,
        entities: List[Entity],
        relationships: List[Relationship],
    ) -> dict:
        """
        融合实体和关系到图（便捷方法）

        Args:
            entities: 要融合的实体列表
            relationships: 要融合的关系列表

        Returns:
            统计信息字典 {
                entities: {added, updated, failed},
                relationships: {added, updated, failed}
            }
        """
        logger.info("=" * 60)
        logger.info("开始融合实体和关系")
        logger.info("=" * 60)

        # 先融合实体（关系依赖实体存在）
        entity_stats = self.combine_entities(entities)

        # 再融合关系
        relationship_stats = self.combine_relationships(relationships)

        logger.info("=" * 60)
        logger.info("融合完成")
        logger.info(
            f"图统计: {self.graph.get_entity_count()} 个实体, {self.graph.get_relationship_count()} 个关系"
        )
        logger.info("=" * 60)

        return {
            "entities": entity_stats,
            "relationships": relationship_stats,
        }
