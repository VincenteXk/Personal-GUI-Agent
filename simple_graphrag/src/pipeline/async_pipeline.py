"""
异步流水线 - 基于 pipeline_v2 改造

改动：
1. 所有LLM调用改为异步
2. 输出改为 GraphDelta 而非直接合并到 Graph
3. 支持任务取消检查
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, List

from ..models.entity import System, Entity
from ..models.delta import (
    GraphDelta,
    ClassDelta,
    EntityDelta,
    RelationshipDelta,
    PropertyDelta,
)
from ..models.task import Task
from ..updaters.system_updater import SystemUpdater
from ..extractors.extractor import GraphExtractor
from ..llm.client import LLMClient
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AsyncPipeline:
    """
    异步流水线处理器

    基于 pipeline_v2 改造，支持：
    - 异步执行
    - 输出 GraphDelta 增量包
    - 任务取消检查
    """

    def __init__(
        self,
        llm_client: LLMClient,
        config: dict,
        config_dir: Path,
    ):
        """
        初始化异步流水线

        Args:
            llm_client: LLM客户端
            config: 配置字典
            config_dir: 配置文件目录
        """
        self.llm_client = llm_client
        self.config = config
        self.config_dir = config_dir

    async def run_task(self, task: Task) -> GraphDelta:
        """
        异步执行单个任务，返回增量更新包

        Args:
            task: 任务对象（包含system_snapshot和input_text）

        Returns:
            GraphDelta增量更新包

        Raises:
            asyncio.CancelledError: 如果任务被取消
        """
        logger.info(f"开始执行任务: {task.task_id}")
        logger.debug(f"输入文本: {task.input_text[:100]}...")

        # 使用任务的system副本
        system = task.system_snapshot
        if system is None:
            raise ValueError("任务的system_snapshot不能为None")

        # 初始化增量数据
        class_deltas: List[ClassDelta] = []
        entity_deltas: List[EntityDelta] = []
        relationship_deltas: List[RelationshipDelta] = []

        try:
            # 检查取消
            self._check_cancelled(task)
            task.update_progress("system_update", "正在更新System...", 10)

            # Step 1: 增量扩展 System
            system, class_changes = await self._step_update_system(
                system, task.input_text
            )

            # 记录类的变更
            for class_name in class_changes.get("added_classes", []):
                class_def = system.get_class_definition(class_name)
                if class_def:
                    class_deltas.append(
                        ClassDelta(
                            name=class_def.name,
                            description=class_def.description,
                            properties=[
                                PropertyDelta(
                                    name=prop.name,
                                    description=prop.description,
                                    required=prop.required,
                                    value_required=prop.value_required,
                                    operation="add",
                                )
                                for prop in class_def.properties
                            ],
                            operation="add",
                        )
                    )

            for class_name in class_changes.get("enhanced_classes", []):
                class_def = system.get_class_definition(class_name)
                if class_def:
                    class_deltas.append(
                        ClassDelta(
                            name=class_def.name,
                            description=class_def.description,
                            properties=[
                                PropertyDelta(
                                    name=prop.name,
                                    description=prop.description,
                                    required=prop.required,
                                    value_required=prop.value_required,
                                    operation="update",
                                )
                                for prop in class_def.properties
                            ],
                            operation="update",
                        )
                    )

            # 检查取消
            self._check_cancelled(task)
            task.update_progress("extraction", "正在提取实体和关系...", 50)

            # Step 2: 提取实体和关系
            entities, relationships = await self._step_extract(system, task.input_text)

            # 转换为增量格式
            for entity in entities:
                # 提取实体的属性值
                properties_dict = {}
                for class_instance in entity.classes:
                    class_props = {}
                    for prop_name, prop_value in class_instance.properties.items():
                        class_props[prop_name] = prop_value.value or ""
                    if class_props:
                        properties_dict[class_instance.class_name] = class_props

                entity_deltas.append(
                    EntityDelta(
                        name=entity.name,
                        description=entity.description,
                        classes=[c.class_name for c in entity.classes],
                        properties=properties_dict,
                        operation="add",
                    )
                )

            for relationship in relationships:
                relationship_deltas.append(
                    RelationshipDelta(
                        source=relationship.source,
                        target=relationship.target,
                        description=relationship.description,
                        count=relationship.count,
                        operation="add",
                    )
                )

            # 检查取消
            self._check_cancelled(task)
            task.update_progress("completed", "任务完成", 100)

            # 构建GraphDelta
            delta = GraphDelta(
                task_id=task.task_id,
                classes=class_deltas,
                entities=entity_deltas,
                relationships=relationship_deltas,
                metadata={
                    "input_text": task.input_text[:200],
                    "entities_count": len(entity_deltas),
                    "relationships_count": len(relationship_deltas),
                    "classes_added": len(
                        [c for c in class_deltas if c.operation == "add"]
                    ),
                },
            )

            logger.info(f"任务执行完成: {delta.get_summary()}")
            return delta

        except asyncio.CancelledError:
            logger.info(f"任务被取消: {task.task_id}")
            raise
        except Exception as e:
            logger.error(f"任务执行失败: {e}", exc_info=True)
            raise

    def _check_cancelled(self, task: Task):
        """检查任务是否被取消"""
        if task.is_cancelled():
            raise asyncio.CancelledError(f"任务 {task.task_id} 被取消")

    async def _step_update_system(
        self, system: System, text: str
    ) -> tuple[System, Dict]:
        """
        步骤1: 增量扩展 System（异步）

        Returns:
            (更新后的System, 变更信息)
        """
        logger.debug("步骤1: 检查并增量扩展 System")

        # 初始化 SystemUpdater
        updater = SystemUpdater(self.llm_client)

        # 检查并更新（注意：check_and_update 内部会调用 LLM，但还不是异步的）
        # 我们需要将其改为异步版本
        system, changes = await self._check_and_update_async(updater, system, text)

        if changes["needed"]:
            logger.info(f"System 已扩展:")
            logger.info(f"  新增类: {changes['added_classes']}")
            logger.info(f"  增强类: {changes['enhanced_classes']}")
        else:
            logger.debug("System 无需扩展")

        return system, changes

    async def _check_and_update_async(
        self, updater: SystemUpdater, system: System, text: str
    ) -> tuple[System, Dict]:
        """异步版本的check_and_update"""
        logger.debug("检查 System 是否需要扩展（异步）")

        # 一次性完成检查和配置生成
        need_update, incremental_config = await self._check_and_generate_async(
            updater, system, text
        )

        if not need_update:
            logger.debug("现有 System 足够，无需扩展")
            return system, {
                "needed": False,
                "added_classes": [],
                "enhanced_classes": [],
                "details": "现有系统足够",
            }

        if not incremental_config or "classes" not in incremental_config:
            logger.warning("LLM 未返回有效的增量配置")
            return system, {
                "needed": True,
                "added_classes": [],
                "enhanced_classes": [],
                "details": "LLM 未返回有效配置",
            }

        logger.info(f"需要扩展 System，涉及 {len(incremental_config['classes'])} 个类")

        # 应用更新
        added, enhanced = updater._apply_update(system, incremental_config)
        logger.info(
            f"System 扩展完成: 新增 {len(added)} 个类, 增强 {len(enhanced)} 个类"
        )

        return system, {
            "needed": True,
            "added_classes": added,
            "enhanced_classes": enhanced,
            "details": f"新增 {len(added)} 个类, 增强 {len(enhanced)} 个类",
        }

    async def _check_and_generate_async(
        self, updater: SystemUpdater, system: System, text: str
    ) -> tuple[bool, Dict]:
        """异步版本的_check_and_generate"""
        import yaml

        system_yaml = yaml.dump(
            {
                "classes": {
                    name: system.get_class_definition(name).to_dict()
                    for name in system.get_all_classes()
                }
            },
            allow_unicode=True,
            default_flow_style=False,
        )

        logger.debug("调用 LLM 检查并生成配置（异步）...")
        response = await self.llm_client.extract_text_async(
            prompt_template=updater.prompt_template,
            temperature=0.3,
            system_yaml=system_yaml,
            text=text,
        )

        logger.debug(f"LLM 响应长度: {len(response)} 字符")

        # 解析响应
        if "SUFFICIENT" in response.upper():
            logger.debug("LLM 判断：系统足够")
            return False, {}

        # 尝试解析为 YAML 配置
        try:
            config = updater._parse_yaml_response(response)
            if config and "classes" in config and config["classes"]:
                logger.debug(f"解析到增量配置: {list(config['classes'].keys())}")
                return True, config
            else:
                logger.warning("LLM 响应不包含有效的类定义")
                return False, {}
        except Exception as e:
            logger.error(f"解析 LLM 响应失败: {e}")
            return False, {}

    async def _step_extract(
        self, system: System, text: str
    ) -> tuple[List[Entity], List]:
        """
        步骤2: 提取实体和关系（异步）

        Returns:
            (实体列表, 关系列表)
        """
        logger.debug("步骤2: 提取实体和关系")

        # 初始化 GraphExtractor
        extraction_config = self.config.get("extraction", {})
        prompts_config = self.config["prompts"]
        extract_prompt_path = self.config_dir / prompts_config["extract_graph"]

        # 准备基础实体信息
        base_entities = [
            {
                "name": e.name,
                "description": e.description,
                "classes": e.classes,
            }
            for e in system.predefined_entities
        ]

        extractor = GraphExtractor(
            llm_client=self.llm_client,
            prompt_template_path=extract_prompt_path,
            classes=system.get_all_classes(),
            system=system,
            tuple_delimiter=extraction_config.get("tuple_delimiter", "|"),
            record_delimiter=extraction_config.get("record_delimiter", "^"),
            completion_delimiter=extraction_config.get("completion_delimiter", "DONE"),
            language=extraction_config.get("language", "中文"),
            base_entities=base_entities,
            enable_check=extraction_config.get("enable_check", True),
        )

        # 异步提取
        entities, relationships = await self._extract_async(extractor, text)

        logger.info(f"提取完成: {len(entities)} 个实体, {len(relationships)} 个关系")

        return entities, relationships

    async def _extract_async(self, extractor: GraphExtractor, text: str):
        """异步版本的extract"""
        logger.debug("开始异步三步提取：实体 -> 类属性 -> 关系")

        # 准备模板变量
        classes_str = ",".join(extractor.classes)
        classes_info = extractor._generate_classes_info()
        base_entities_info = extractor._format_base_entities()

        # 调用LLM提取（异步）
        logger.debug("调用LLM进行三步提取（异步）...")
        response = await self.llm_client.extract_text_async(
            prompt_template=extractor.prompt_template,
            input_text=text,
            entity_types=classes_str,
            tuple_delimiter=extractor.tuple_delimiter,
            record_delimiter=extractor.record_delimiter,
            completion_delimiter=extractor.completion_delimiter,
            language=extractor.language,
            classes_info=classes_info,
            base_entities_info=base_entities_info,
        )

        logger.debug(f"LLM响应长度: {len(response)} 字符")

        # 如果启用检查，进行二次优化（异步）
        if extractor.enable_check:
            logger.info("开始检查和优化提取结果（异步）...")
            checked_response = await self._check_extraction_async(
                extractor, text, response, classes_str
            )
            response = checked_response
            logger.info("检查优化完成")

        # 解析响应
        entities, relationships = extractor._parse_response(response)

        return entities, relationships

    async def _check_extraction_async(
        self,
        extractor: GraphExtractor,
        input_text: str,
        extraction_result: str,
        entity_types: str,
    ) -> str:
        """异步版本的_check_extraction"""
        logger.debug("调用检查LLM优化提取结果（异步）...")

        response = await self.llm_client.extract_text_async(
            prompt_template=extractor.check_template,
            temperature=0.3,
            input_text=input_text,
            extraction_result=extraction_result,
            entity_types=entity_types,
        )

        return response
