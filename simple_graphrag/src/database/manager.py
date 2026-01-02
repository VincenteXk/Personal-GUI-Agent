"""
图数据库管理器，负责初始化和增量更新
"""

from pathlib import Path
from typing import Optional
import yaml
import os

from ..models.graph import Graph
from ..models.entity import Entity, System
from ..models.relationship import Relationship
from ..extractors.extractor import GraphExtractor
from ..llm.client import LLMClient
from ..utils.logger import get_logger

logger = get_logger(__name__)


class GraphDatabaseManager:
    """图数据库管理器"""

    def __init__(self, config_path: Path):
        """
        初始化数据库管理器

        Args:
            config_path: 配置文件路径
        """
        logger.info(f"初始化数据库管理器，配置文件: {config_path}")
        self.config_path = config_path
        self.config = self._load_config()
        self.graph_path = Path(self.config["graph_database"]["storage_path"])
        logger.debug(f"图数据库存储路径: {self.graph_path}")

        # 初始化LLM客户端
        logger.debug("初始化LLM客户端...")
        model_config = self.config["models"]["default_chat_model"]
        # 处理API key（可能是环境变量引用或直接值）
        api_key = model_config.get("api_key")
        if api_key and api_key.startswith("${") and api_key.endswith("}"):
            api_key = os.environ.get(api_key[2:-1])
        elif not api_key:
            api_key = os.environ.get("MIMO_API_KEY")

        logger.debug(f"LLM模型: {model_config.get('model', 'mimo-v2-flash')}")
        logger.debug(f"API Base: {model_config.get('api_base')}")
        self.llm_client = LLMClient(
            api_key=api_key,
            base_url=model_config.get("api_base"),
            model=model_config.get("model", "mimo-v2-flash"),
            max_retries=model_config.get("max_retries", 10),
        )
        logger.debug("LLM客户端初始化完成")

        # 加载 System（类配置 + 预定义实体）
        logger.debug("加载System配置...")
        classes_config = self.config.get("classes", {})
        if not classes_config:
            raise ValueError("配置文件中必须包含 'classes' 配置")
        base_entities = self.config.get("base_system", {}).get("base_entities", [])
        self.system = System.from_dict(
            {"classes": classes_config, "base_entities": base_entities}
        )
        logger.debug(f"已加载 {len(self.system.get_all_classes())} 个类配置")

        # 初始化提取器
        logger.debug("初始化提取器...")
        prompt_path = Path(self.config["prompts"]["extract_graph"])
        # 如果提示词路径是相对路径，则相对于配置文件目录
        if not prompt_path.is_absolute():
            # 配置文件目录的父目录（simple_graphrag目录）
            prompt_path = config_path.parent / prompt_path

        logger.debug(f"提示词模板路径: {prompt_path}")
        logger.debug(f"实体类型: {self.config['entity_types']}")

        extraction_config = self.config.get("extraction", {})
        # 获取类列表（用于提示词）
        classes_list = list(self.system.get_all_classes())
        self.extractor = GraphExtractor(
            llm_client=self.llm_client,
            prompt_template_path=prompt_path,
            classes=classes_list,
            system=self.system,
            tuple_delimiter=extraction_config.get("tuple_delimiter", "|"),
            record_delimiter=extraction_config.get("record_delimiter", "^"),
            completion_delimiter=extraction_config.get("completion_delimiter", "DONE"),
            language=extraction_config.get("language", "中文"),
        )
        logger.debug("提取器初始化完成")

    def _load_config(self) -> dict:
        """加载配置文件"""
        with open(self.config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # 处理环境变量替换
        def replace_env_vars(obj):
            if isinstance(obj, dict):
                return {k: replace_env_vars(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_env_vars(item) for item in obj]
            elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
                env_var = obj[2:-1]
                return os.environ.get(env_var, obj)
            return obj

        return replace_env_vars(config)

    def initialize_database(self, input_text: str) -> Graph:
        """
        初始化数据库：从输入文本建立初始图

        Args:
            input_text: 输入文本（格式特殊，不需要手动分片）

        Returns:
            创建的图对象
        """
        logger.info("=" * 60)
        logger.info("开始初始化数据库")
        logger.info("=" * 60)
        logger.debug(f"输入文本长度: {len(input_text)} 字符")
        logger.debug(f"输入文本内容:\n{input_text}")

        # 创建新图
        graph = Graph(system=self.system, include_predefined_entities=True)
        logger.debug("创建新图对象")

        # 提取实体和关系
        logger.info("正在提取实体和关系...")
        entities, relationships = self.extractor.extract(input_text)

        logger.info(f"提取到 {len(entities)} 个实体和 {len(relationships)} 个关系")

        # 添加实体到图
        logger.debug("添加实体到图...")
        added_entities = 0
        updated_entities = 0
        for entity in entities:
            existing = graph.get_entity(entity.name)
            graph.add_entity(entity)
            if existing:
                updated_entities += 1
                logger.debug(f"更新实体: {entity.name}")
            else:
                added_entities += 1
                class_names = [c.class_name for c in entity.classes]
                logger.debug(f"添加新实体: {entity.name} (类: {class_names})")

        logger.info(
            f"实体处理完成: 新增 {added_entities} 个, 更新 {updated_entities} 个"
        )

        # 添加关系到图
        logger.debug("添加关系到图...")
        added_relationships = 0
        skipped_relationships = 0
        for relationship in relationships:
            try:
                graph.add_relationship(relationship)
                added_relationships += 1
                logger.debug(
                    f"添加关系: {relationship.source} -> {relationship.target}"
                )
            except ValueError as e:
                skipped_relationships += 1
                logger.warning(
                    f"跳过关系 {relationship.source} -> {relationship.target}: {e}"
                )

        logger.info(
            f"关系处理完成: 新增 {added_relationships} 个, 跳过 {skipped_relationships} 个"
        )

        # 保存图
        self._save_graph(graph)

        logger.info(
            f"数据库初始化完成！共 {graph.get_entity_count()} 个中心节点，{graph.get_class_node_count()} 个类节点，{graph.get_relationship_count()} 个关系"
        )
        logger.info("=" * 60)

        return graph

    def incremental_update(self, new_text: str) -> Graph:
        """
        增量更新数据库：添加新数据到现有图

        Args:
            new_text: 新的输入文本

        Returns:
            更新后的图对象
        """
        logger.info("=" * 60)
        logger.info("开始增量更新数据库")
        logger.info("=" * 60)
        logger.debug(f"新文本长度: {len(new_text)} 字符")
        logger.debug(f"新文本内容:\n{new_text}")

        # 加载现有图
        if self.graph_path.exists():
            logger.info("加载现有图...")
            graph = Graph.load(self.graph_path)
            logger.info(
                f"现有图包含 {graph.get_entity_count()} 个实体和 {graph.get_relationship_count()} 个关系"
            )
            logger.debug(f"从文件加载图: {self.graph_path}")
        else:
            logger.info("未找到现有图，创建新图...")
            graph = Graph(system=self.system, include_predefined_entities=True)

        # 从新文本提取实体和关系
        logger.info("正在从新文本提取实体和关系...")
        entities, relationships = self.extractor.extract(new_text)

        logger.info(
            f"从新文本提取到 {len(entities)} 个实体和 {len(relationships)} 个关系"
        )

        # 创建临时图用于合并
        logger.debug("创建临时图用于合并...")
        temp_graph = Graph(system=self.system, include_predefined_entities=True)

        # 添加新实体
        logger.debug("添加新实体到临时图...")
        temp_entities_count = 0
        for entity in entities:
            temp_graph.add_entity(entity)
            temp_entities_count += 1
            class_names = [c.class_name for c in entity.classes]
            logger.debug(f"临时图添加实体: {entity.name} (类: {class_names})")

        logger.debug(f"临时图包含 {temp_entities_count} 个实体")

        # 添加新关系（需要确保节点存在，可能是中心节点或类节点）
        logger.debug("添加新关系到临时图...")
        temp_relationships_count = 0
        skipped_temp_relationships = 0
        for relationship in relationships:
            # 检查源节点是否存在（可能是中心节点或类节点）
            source_key = relationship.source.upper()
            source_exists = (
                source_key in temp_graph._entities
                or source_key in temp_graph._class_nodes
            )

            # 检查目标节点是否存在（可能是中心节点或类节点）
            target_key = relationship.target.upper()
            target_exists = (
                target_key in temp_graph._entities
                or target_key in temp_graph._class_nodes
            )

            if source_exists and target_exists:
                try:
                    temp_graph.add_relationship(relationship)
                    temp_relationships_count += 1
                    logger.debug(
                        f"临时图添加关系: {relationship.source} -> {relationship.target}"
                    )
                except ValueError as e:
                    skipped_temp_relationships += 1
                    logger.debug(f"临时图跳过关系: {e}")
            else:
                skipped_temp_relationships += 1
                logger.debug(
                    f"临时图跳过关系（节点不存在）: {relationship.source} -> {relationship.target}"
                )

        logger.debug(
            f"临时图包含 {temp_relationships_count} 个关系, 跳过 {skipped_temp_relationships} 个"
        )

        # 合并临时图到主图
        logger.info("合并新数据到现有图...")
        before_merge_entities = graph.get_entity_count()
        before_merge_class_nodes = graph.get_class_node_count()
        before_merge_relationships = graph.get_relationship_count()

        graph.merge(temp_graph)

        after_merge_entities = graph.get_entity_count()
        after_merge_class_nodes = graph.get_class_node_count()
        after_merge_relationships = graph.get_relationship_count()

        logger.info(
            f"合并完成: 中心节点 {before_merge_entities} -> {after_merge_entities}, "
            f"类节点 {before_merge_class_nodes} -> {after_merge_class_nodes}, "
            f"关系 {before_merge_relationships} -> {after_merge_relationships}"
        )
        logger.debug(f"新增中心节点: {after_merge_entities - before_merge_entities} 个")
        logger.debug(
            f"新增类节点: {after_merge_class_nodes - before_merge_class_nodes} 个"
        )
        logger.debug(
            f"新增关系: {after_merge_relationships - before_merge_relationships} 个"
        )

        # 保存更新后的图
        self._save_graph(graph)

        logger.info(
            f"增量更新完成！现在共有 {graph.get_entity_count()} 个中心节点，{graph.get_class_node_count()} 个类节点，{graph.get_relationship_count()} 个关系"
        )
        logger.info("=" * 60)

        return graph

    def _save_graph(self, graph: Graph) -> None:
        """保存图到文件"""
        logger.debug(f"保存图到文件: {self.graph_path}")
        graph.save(self.graph_path)
        logger.info(f"图已保存到: {self.graph_path}")

    def load_graph(self) -> Optional[Graph]:
        """加载图"""
        if self.graph_path.exists():
            return Graph.load(self.graph_path)
        return None

    def get_graph(self) -> Optional[Graph]:
        """获取当前图（如果不存在则返回None）"""
        return self.load_graph()
