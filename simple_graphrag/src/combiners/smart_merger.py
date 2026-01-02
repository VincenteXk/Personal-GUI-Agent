"""
智能合并器

使用LLM进行智能合并，处理去重、对齐、冲突解决和优化。
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field

from ..models.entity import System, Entity, ClassDefinition, PropertyDefinition
from ..models.graph import Graph
from ..models.delta import (
    GraphDelta,
    ClassDelta,
    EntityDelta,
    RelationshipDelta,
    PropertyDelta,
)
from ..llm.client import LLMClient
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MergeResult:
    """
    合并结果

    Attributes:
        optimized_delta: 优化后的增量更新包
        duplicates_found: 发现的重复项数量
        conflicts_resolved: 解决的冲突数量
        names_aligned: 对齐的命名数量
        descriptions_optimized: 优化的描述数量
        notes: 合并说明
        llm_input: LLM输入数据（如果使用了LLM）
        llm_response: LLM原始响应（如果使用了LLM）
    """

    optimized_delta: GraphDelta
    duplicates_found: int = 0
    conflicts_resolved: int = 0
    names_aligned: int = 0
    descriptions_optimized: int = 0
    notes: str = ""
    llm_input: Optional[dict] = None
    llm_response: Optional[str] = None

    def get_summary(self) -> str:
        """获取合并摘要"""
        return (
            f"MergeResult: {self.duplicates_found} duplicates, "
            f"{self.conflicts_resolved} conflicts, "
            f"{self.names_aligned} aligned, "
            f"{self.descriptions_optimized} optimized"
        )


class SmartMerger:
    """
    智能合并器

    使用LLM进行智能合并，处理：
    - 去重：识别相同实体/关系的不同表达
    - 对齐：统一命名和描述
    - 冲突解决：处理属性值冲突
    - 优化：合并重复信息，提炼精准描述
    """

    def __init__(
        self,
        llm_client: LLMClient,
        prompt_path: Optional[Path] = None,
        enable_smart_merge: bool = True,
    ):
        """
        初始化智能合并器

        Args:
            llm_client: LLM客户端
            prompt_path: 合并提示词模板路径
            enable_smart_merge: 是否启用LLM智能合并（False则使用简单合并）
        """
        self.llm_client = llm_client
        self.enable_smart_merge = enable_smart_merge

        # 加载提示词模板
        if prompt_path and prompt_path.exists():
            self.prompt_template = LLMClient.load_prompt_template(prompt_path)
            logger.info(f"已加载智能合并提示词: {prompt_path}")
        else:
            self.prompt_template = None
            if enable_smart_merge:
                logger.warning("未找到智能合并提示词，将使用简单合并")
                self.enable_smart_merge = False

    async def merge_delta(
        self,
        current_system: System,
        current_graph: Graph,
        delta: GraphDelta,
    ) -> MergeResult:
        """
        智能合并增量更新到当前system和graph

        Args:
            current_system: 当前的System
            current_graph: 当前的Graph
            delta: 待合并的增量更新包

        Returns:
            合并结果
        """
        logger.info(f"开始智能合并: {delta.get_summary()}")

        if not self.enable_smart_merge or self.prompt_template is None:
            # 简单合并（不使用LLM）
            logger.info("使用简单合并模式")
            return await self._simple_merge(current_system, current_graph, delta)

        # LLM智能合并
        logger.info("使用LLM智能合并模式")
        return await self._llm_merge(current_system, current_graph, delta)

    async def _simple_merge(
        self,
        current_system: System,
        current_graph: Graph,
        delta: GraphDelta,
    ) -> MergeResult:
        """
        简单合并（不使用LLM，直接应用增量）
        """
        logger.debug("执行简单合并...")

        # 直接使用原始delta，不做优化
        optimized_delta = delta

        return MergeResult(
            optimized_delta=optimized_delta,
            notes="简单合并模式，未使用LLM优化",
        )

    async def _llm_merge(
        self,
        current_system: System,
        current_graph: Graph,
        delta: GraphDelta,
    ) -> MergeResult:
        """
        LLM智能合并
        """
        logger.debug("准备LLM合并输入...")

        # 准备当前状态信息
        current_system_yaml = self._serialize_system(current_system)
        entity_count = current_graph.get_entity_count()
        relationship_count = current_graph.get_relationship_count()
        existing_entities = list(current_graph._entities.keys())[:50]  # 最多50个
        existing_entities_detail = self._get_entities_detail(current_graph, limit=20)

        # 准备增量更新信息
        delta_json = json.dumps(delta.to_dict(), ensure_ascii=False, indent=2)

        # 记录LLM输入
        llm_input_data = {
            "current_system_classes": list(current_system.get_all_classes()),
            "entity_count": entity_count,
            "relationship_count": relationship_count,
            "existing_entities_sample": existing_entities,
            "delta_summary": delta.get_summary(),
            "delta_details": delta.to_dict(),
        }

        # 调用LLM
        logger.debug("调用LLM进行智能合并...")
        response = await self.llm_client.extract_text_async(
            prompt_template=self.prompt_template,
            temperature=0.3,
            current_system=current_system_yaml,
            entity_count=entity_count,
            relationship_count=relationship_count,
            existing_entities=", ".join(existing_entities),
            existing_entities_detail=existing_entities_detail,
            delta=delta_json,
        )

        logger.debug(f"LLM响应长度: {len(response)} 字符")

        # 解析LLM响应
        try:
            optimized_data = self._parse_llm_response(response)
            optimized_delta = self._build_optimized_delta(delta.task_id, optimized_data)

            # 提取合并统计
            merge_summary = optimized_data.get("merge_summary", {})

            result = MergeResult(
                optimized_delta=optimized_delta,
                duplicates_found=merge_summary.get("duplicates_found", 0),
                conflicts_resolved=merge_summary.get("conflicts_resolved", 0),
                names_aligned=merge_summary.get("names_aligned", 0),
                descriptions_optimized=merge_summary.get("descriptions_optimized", 0),
                notes=merge_summary.get("notes", ""),
                llm_input=llm_input_data,
                llm_response=response,
            )

            logger.info(f"智能合并完成: {result.get_summary()}")
            return result

        except Exception as e:
            logger.error(f"解析LLM响应失败: {e}")
            logger.debug(f"原始响应: {response[:500]}")
            # 降级到简单合并
            logger.warning("降级到简单合并模式")
            return await self._simple_merge(current_system, current_graph, delta)

    def _serialize_system(self, system: System) -> str:
        """序列化System为YAML字符串"""
        import yaml

        system_dict = {
            "classes": {
                name: system.get_class_definition(name).to_dict()
                for name in system.get_all_classes()
            }
        }
        return yaml.dump(system_dict, allow_unicode=True, default_flow_style=False)

    def _get_entities_detail(self, graph: Graph, limit: int = 20) -> str:
        """获取现有实体的详细信息（JSON格式）"""
        entities_data = []
        for i, (name, entity) in enumerate(graph._entities.items()):
            if i >= limit:
                break
            entities_data.append(
                {
                    "name": entity.name,
                    "description": (
                        entity.description[:100] if entity.description else ""
                    ),
                    "classes": [c.class_name for c in entity.classes],
                }
            )
        return json.dumps(entities_data, ensure_ascii=False, indent=2)

    def _parse_llm_response(self, response: str) -> dict:
        """解析LLM返回的JSON响应"""
        # 移除可能的markdown代码块标记
        response = re.sub(r"```json\s*\n", "", response)
        response = re.sub(r"```\s*$", "", response)
        response = response.strip()

        # 解析JSON
        data = json.loads(response)
        return data

    def _build_optimized_delta(self, task_id: str, optimized_data: dict) -> GraphDelta:
        """从LLM优化结果构建GraphDelta"""
        # 解析类增量
        classes = []
        for cls_data in optimized_data.get("optimized_classes", []):
            properties = [
                PropertyDelta(
                    name=p["name"],
                    description=p.get("description"),
                    required=p.get("required"),
                    value_required=p.get("value_required"),
                    operation=p.get("operation", "add"),
                )
                for p in cls_data.get("properties", [])
            ]
            classes.append(
                ClassDelta(
                    name=cls_data["name"],
                    description=cls_data.get("description"),
                    properties=properties,
                    operation=cls_data.get("operation", "add"),
                )
            )

        # 解析实体增量
        entities = []
        for ent_data in optimized_data.get("optimized_entities", []):
            # 如果operation是merge，需要记录merge_target
            operation = ent_data.get("operation", "add")
            merge_target = ent_data.get("merge_target")

            # 如果是merge操作，使用merge_target作为实体名
            entity_name = (
                merge_target
                if operation == "merge" and merge_target
                else ent_data["name"]
            )

            entities.append(
                EntityDelta(
                    name=entity_name,
                    description=ent_data.get("description"),
                    classes=ent_data.get("classes", []),
                    properties=ent_data.get("properties", {}),
                    operation=operation,
                )
            )

        # 解析关系增量
        relationships = []
        for rel_data in optimized_data.get("optimized_relationships", []):
            relationships.append(
                RelationshipDelta(
                    source=rel_data["source"],
                    target=rel_data["target"],
                    description=rel_data["description"],
                    count=rel_data.get("count", 1),
                    refer=rel_data.get("refer", []),  # 添加 refer 字段支持
                    operation=rel_data.get("operation", "add"),
                )
            )

        return GraphDelta(
            task_id=task_id,
            classes=classes,
            entities=entities,
            relationships=relationships,
            metadata=optimized_data.get("merge_summary", {}),
        )
