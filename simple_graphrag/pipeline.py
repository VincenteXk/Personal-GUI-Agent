"""
完整流水线：从原始输入到图生成

流程：
1. 输入未知的自然语言内容
2. 使用 text_converter 创建丰富信息的自然语言内容
3. 调用 system_builder 创建对应的系统配置
4. 使用 extract_graph 进行图生成
5. 打印最终信息
"""

import sys
from pathlib import Path

# 确保无论从哪个工作目录运行，都能导入 simple_graphrag/src 下的模块（import src.*）
PROJECT_ROOT = Path(__file__).resolve().parent  # .../simple_graphrag
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.llm.client import LLMClient
from src.builders.system_builder import SystemBuilder
from src.extractors.extractor import GraphExtractor
from src.models.graph import Graph
from src.models.entity import System
from src.utils.logger import setup_logging, get_logger
from dotenv import load_dotenv
from graph_visualizer import GraphVisualizer
import yaml
import os
import webbrowser

load_dotenv()
setup_logging(verbose=True)
logger = get_logger(__name__)


class Pipeline:
    """完整流水线处理器"""

    def __init__(self, config_path: Path):
        """
        初始化流水线

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = self._load_config()
        # 项目根目录（simple_graphrag 目录），用于统一输出路径
        self.project_root = Path(__file__).parent
        # 配置目录（simple_graphrag/config），用于读取 prompts / config 内资源
        self.config_dir = config_path.parent

        # 初始化LLM客户端
        logger.info("初始化LLM客户端...")
        model_config = self.config["models"]["default_chat_model"]
        api_key = model_config.get("api_key")
        if api_key and api_key.startswith("${") and api_key.endswith("}"):
            api_key = os.environ.get(api_key[2:-1])
        elif not api_key:
            api_key = os.environ.get("MIMO_API_KEY")

        # self.llm_client = LLMClient(
        #     api_key=api_key,
        #     base_url=model_config.get("api_base"),
        #     model=model_config.get("model", "mimo-v2-flash"),
        #     max_retries=model_config.get("max_retries", 10),

        self.llm_client = LLMClient(
            provider="ark",
            model="deepseek-v3-2-251201",
            base_url="https://ark.cn-beijing.volces.com/api/v3",
        )
        logger.info("LLM客户端初始化完成")

        # 加载提示词路径
        prompts_config = self.config["prompts"]
        self.prompts_dir = self.config_dir

        # 初始化文本转换器提示词
        self.text_converter_template = LLMClient.load_prompt_template(
            self.prompts_dir / prompts_config["text_converter"]
        )

        # 获取基础系统架构
        base_system = self.config.get("base_system", None)

        # 初始化系统构建器
        self.system_builder = SystemBuilder(
            llm_client=self.llm_client,
            core_prompt_path=self.prompts_dir / prompts_config["system_core"],
            rules_prompt_path=self.prompts_dir / prompts_config["system_rules"],
            build_prompt_path=self.prompts_dir / prompts_config["build_system"],
            base_system=base_system,
        )

        # 获取图数据库存储路径
        graph_db_config = self.config.get("graph_database", {})
        storage_path = graph_db_config.get("storage_path", "output/graph.pkl")
        # 输出统一放在 simple_graphrag/output 下（而不是 simple_graphrag/config/output）
        self.graph_storage_path = self.project_root / storage_path

        # 获取可视化配置
        self.auto_open_visualization = graph_db_config.get(
            "auto_open_visualization", True
        )
        visualization_path = graph_db_config.get(
            "visualization_path", "output/graph_visualization.html"
        )
        self.visualization_path = self.project_root / visualization_path

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

    def step1_convert_text(self, raw_input: str) -> str:
        """
        步骤1: 将原始输入转换为丰富的自然语言文本

        Args:
            raw_input: 原始输入内容

        Returns:
            转换后的丰富自然语言文本
        """
        logger.info("=" * 60)
        logger.info("步骤1: 文本转换")
        logger.info("=" * 60)
        logger.info(f"原始输入:\n{raw_input}\n")

        # 格式化提示词
        prompt = self.text_converter_template.format(input_content=raw_input)

        # 调用LLM进行转换
        logger.info("调用LLM进行文本转换...")
        messages = [{"role": "user", "content": prompt}]
        enriched_text = self.llm_client.chat_completion(messages, temperature=0.7)

        logger.info(f"转换后的自然语言文本:\n{enriched_text}\n")
        return enriched_text.strip()

    def step2_build_system(self, enriched_text: str) -> dict:
        """
        步骤2: 从丰富的文本构建系统配置

        Args:
            enriched_text: 丰富的自然语言文本

        Returns:
            系统配置字典
        """
        logger.info("=" * 60)
        logger.info("步骤2: 构建系统配置")
        logger.info("=" * 60)

        # 构建系统配置
        logger.info("调用系统构建器...")
        system_config = self.system_builder.build_system_from_example(enriched_text)

        logger.info(
            f"系统配置构建完成，包含 {len(system_config.get('classes', {}))} 个类"
        )
        logger.info("\n系统配置:")
        logger.info("=" * 60)
        print(yaml.dump(system_config, allow_unicode=True, default_flow_style=False))
        logger.info("=" * 60)

        return system_config

    def step3_extract_graph(self, enriched_text: str, system_config: dict) -> Graph:
        """
        步骤3: 使用系统配置提取实体和关系，生成图

        Args:
            enriched_text: 丰富的自然语言文本
            system_config: 系统配置

        Returns:
            生成的图对象
        """
        logger.info("=" * 60)
        logger.info("步骤3: 提取实体和关系，生成图")
        logger.info("=" * 60)

        # 构建 System（系统架构定义）
        classes_config = system_config.get("classes", {})
        if not classes_config:
            raise ValueError("系统配置中必须包含 'classes' 配置")

        # 获取基础实体
        base_system = self.config.get("base_system", {})
        base_entities = base_system.get("base_entities", [])

        system = System.from_dict(
            {"classes": classes_config, "base_entities": base_entities}
        )
        logger.info(f"已加载 {len(system.get_all_classes())} 个类配置")

        # 获取类列表（用于提示词）
        classes_list = list(system.get_all_classes())

        # 初始化提取器
        extraction_config = self.config.get("extraction", {})
        extract_prompt_path = self.prompts_dir / self.config["prompts"]["extract_graph"]

        extractor = GraphExtractor(
            llm_client=self.llm_client,
            prompt_template_path=extract_prompt_path,
            classes=classes_list,
            system=system,
            tuple_delimiter=extraction_config.get("tuple_delimiter", "|"),
            record_delimiter=extraction_config.get("record_delimiter", "^"),
            completion_delimiter=extraction_config.get("completion_delimiter", "DONE"),
            language=extraction_config.get("language", "中文"),
            base_entities=base_entities,
        )

        # 提取实体和关系
        logger.info("开始提取实体和关系...")
        entities, relationships = extractor.extract(enriched_text)

        logger.info(f"提取完成: {len(entities)} 个实体, {len(relationships)} 个关系")

        # 创建图（绑定 system）
        graph = Graph(system=system, include_predefined_entities=True)

        # 添加实体到图
        logger.info("添加实体到图...")
        for entity in entities:
            graph.add_entity(entity)
            class_names = [c.class_name for c in entity.classes]
            logger.debug(f"添加实体: {entity.name} (类: {class_names})")

        # 添加关系到图
        logger.info("添加关系到图...")
        for relationship in relationships:
            try:
                graph.add_relationship(relationship)
                logger.debug(
                    f"添加关系: {relationship.source} -> {relationship.target}"
                )
            except ValueError as e:
                logger.warning(
                    f"跳过关系 {relationship.source} -> {relationship.target}: {e}"
                )

        logger.info(
            f"图生成完成！共 {graph.get_entity_count()} 个实体节点，"
            f"{graph.get_class_node_count()} 个类节点，"
            f"{graph.get_relationship_count()} 个关系"
        )

        return graph

    def step4_print_results(self, graph: Graph):
        """
        步骤4: 打印最终结果

        Args:
            graph: 生成的图对象
        """
        logger.info("=" * 60)
        logger.info("步骤4: 打印最终结果")
        logger.info("=" * 60)

        logger.info("\n图统计信息:")
        logger.info("-" * 60)
        logger.info(f"实体节点数量: {graph.get_entity_count()}")
        logger.info(f"类节点数量: {graph.get_class_node_count()}")
        logger.info(f"关系数量: {graph.get_relationship_count()}")
        logger.info("-" * 60)

        logger.info("\n实体列表:")
        logger.info("-" * 60)
        for entity in graph.get_entities():
            class_names = [c.class_name for c in entity.classes]
            classes_str = f" (类: {', '.join(class_names)})" if class_names else ""
            logger.info(f"  • {entity.name}{classes_str}")
            logger.info(f"    描述: {entity.description}")

            # 打印属性
            if entity.classes:
                for class_instance in entity.classes:
                    if class_instance.properties:
                        props_str = ", ".join(
                            [
                                f"{p.property_name}={p.value}"
                                for p in class_instance.properties.values()
                                if p.value is not None
                            ]
                        )
                        if props_str:
                            logger.info(
                                f"    [{class_instance.class_name}] 属性: {props_str}"
                            )
            logger.info("")

        logger.info("\n关系列表:")
        logger.info("-" * 60)
        for relationship in graph.get_relationships():
            logger.info(f"  • {relationship.source} -> {relationship.target}")
            logger.info(f"    描述: {relationship.description}")
            logger.info(f"    次数: {relationship.count}")
            logger.info("")

        logger.info("=" * 60)

    def step5_save_graph(self, graph: Graph):
        """
        步骤5: 保存图数据库（增量更新）

        Args:
            graph: 要保存的图对象
        """
        logger.info("=" * 60)
        logger.info("步骤5: 保存图数据库")
        logger.info("=" * 60)

        # 确保输出目录存在
        self.graph_storage_path.parent.mkdir(parents=True, exist_ok=True)

        # 如果文件已存在，先加载并合并
        if self.graph_storage_path.exists():
            logger.info(f"检测到已存在的图数据库: {self.graph_storage_path}")
            logger.info("正在加载现有图数据库...")
            try:
                existing_graph = Graph.load(self.graph_storage_path)
                logger.info(
                    f"现有图数据库包含: {existing_graph.get_entity_count()} 个实体, "
                    f"{existing_graph.get_class_node_count()} 个类节点, "
                    f"{existing_graph.get_relationship_count()} 个关系"
                )

                # 合并新图到现有图
                logger.info("正在合并新图数据...")
                existing_graph.merge(graph)
                graph = existing_graph
                logger.info("图数据合并完成")
            except Exception as e:
                logger.warning(f"加载现有图数据库失败，将创建新图: {e}")
                # 如果加载失败，使用新图

        # 保存图
        logger.info(f"正在保存图数据库到: {self.graph_storage_path}")
        graph.save(self.graph_storage_path)
        logger.info(
            f"图数据库保存成功！包含 {graph.get_entity_count()} 个实体, "
            f"{graph.get_class_node_count()} 个类节点, "
            f"{graph.get_relationship_count()} 个关系"
        )

    def step6_visualize_graph(self, graph: Graph):
        """
        步骤6: 生成并自动打开可视化

        Args:
            graph: 要可视化的图对象
        """
        logger.info("=" * 60)
        logger.info("步骤6: 生成并打开可视化")
        logger.info("=" * 60)

        try:
            # 导入可视化器（使用相对路径或绝对路径）
            # 尝试从项目根目录导入
            if str(self.project_root) not in sys.path:
                sys.path.insert(0, str(self.project_root))

            # 确保可视化输出目录存在
            self.visualization_path.parent.mkdir(parents=True, exist_ok=True)

            # 生成可视化
            logger.info(f"正在生成可视化文件: {self.visualization_path}")
            gv = GraphVisualizer(title="Simple GraphRAG 知识图谱")
            gv.from_simple_graphrag(graph)
            gv.render_to_html(self.visualization_path)

            # 自动打开浏览器
            logger.info("正在打开浏览器...")
            visualization_url = self.visualization_path.resolve().as_uri()
            webbrowser.open(visualization_url)
            logger.info(f"可视化已在浏览器中打开: {visualization_url}")

        except ImportError as e:
            logger.warning(f"无法导入可视化模块: {e}")
            logger.warning("请确保 graph_visualizer.py 在项目根目录中")
        except Exception as e:
            logger.error(f"生成可视化时出错: {e}", exc_info=True)

    def run(self, raw_input: str) -> Graph:
        """
        运行完整流水线

        Args:
            raw_input: 原始输入内容

        Returns:
            生成的图对象
        """
        logger.info("\n" + "=" * 60)
        logger.info("开始运行完整流水线")
        logger.info("=" * 60)

        try:
            # 步骤1: 文本转换
            enriched_text = self.step1_convert_text(raw_input)

            # 步骤2: 构建系统配置
            system_config = self.step2_build_system(enriched_text)

            # 步骤3: 提取图
            graph = self.step3_extract_graph(enriched_text, system_config)

            # 步骤4: 打印结果
            self.step4_print_results(graph)

            # 步骤5: 保存图数据库
            self.step5_save_graph(graph)

            # 步骤6: 生成并打开可视化
            if self.auto_open_visualization:
                self.step6_visualize_graph(graph)

            logger.info("\n" + "=" * 60)
            logger.info("流水线执行完成！")
            logger.info("=" * 60)

            return graph

        except Exception as e:
            logger.error(f"流水线执行失败: {e}", exc_info=True)
            raise


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="完整流水线：从原始输入到图生成")
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        help="输入的自然语言内容（如果不提供，将使用示例输入）",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="启用详细日志输出",
    )
    args = parser.parse_args()

    # 设置日志
    if args.verbose:
        os.environ["SIMPLERAG_VERBOSE"] = "1"
        setup_logging(verbose=True)

    # 配置文件路径
    config_path = Path(__file__).parent / "config" / "config.yaml"
    logger.info(f"使用配置文件: {config_path}")

    # 初始化流水线
    pipeline = Pipeline(config_path)

    # 获取输入
    if args.input:
        raw_input = args.input
    else:
        # 使用示例输入
        raw_input = """
打开“小米社区”APP，查看了最新发布的Xiaomi MIMO 大模型，打开了浏览器，搜索并尝试使用Xiaomi MIMO 大模型。
        """

    # 运行流水线
    graph = pipeline.run(raw_input)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"程序执行失败: {e}", exc_info=True)
