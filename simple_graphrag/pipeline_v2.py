"""
重构后的流水线 Pipeline V2

新流程：
1. 从 config.yaml 加载预定义 System（base_system）
2. 创建 Graph(system)，自动注入预定义实体
3. 对输入文本调用 SystemUpdater 检查并增量扩展 System
4. 使用 GraphExtractor 提取实体和关系
5. 使用 Combiner 融合到 Graph
6. 保存 Graph 和可视化
"""

import sys
from pathlib import Path
import yaml
import os
import webbrowser

# 确保从任何工作目录运行都能导入 simple_graphrag/src 下的模块
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.entity import System
from src.models.graph import Graph
from src.updaters.system_updater import SystemUpdater
from src.extractors.extractor import GraphExtractor
from src.combiners.combiner import Combiner
from src.llm.client import LLMClient
from src.utils.logger import setup_logging, get_logger
from graph_visualizer import GraphVisualizer
from dotenv import load_dotenv

load_dotenv()
setup_logging(verbose=True)
logger = get_logger(__name__)


class PipelineV2:
    """重构后的流水线处理器"""

    def __init__(self, config_path: Path):
        """
        初始化流水线

        Args:
            config_path: 配置文件路径（config.yaml）
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.project_root = Path(__file__).parent
        self.config_dir = config_path.parent

        # 初始化 LLM 客户端
        logger.info("初始化 LLM 客户端...")
        model_config = self.config["models"]["default_chat_model"]
        api_key = self._get_api_key(model_config)
        verbose = model_config.get("verbose", False)

        self.llm_client = LLMClient(
            provider="ark",
            model="deepseek-v3-2-251201",
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            verbose=verbose,
        )
        logger.info(f"LLM 客户端初始化完成 (verbose={verbose})")

        # 获取输出路径
        graph_db_config = self.config.get("graph_database", {})
        storage_path = graph_db_config.get("storage_path", "output/graph.pkl")
        self.graph_storage_path = self.project_root / storage_path

        visualization_path = graph_db_config.get(
            "visualization_path", "output/graph_visualization.html"
        )
        self.visualization_path = self.project_root / visualization_path
        self.auto_open_visualization = graph_db_config.get(
            "auto_open_visualization", True
        )
        self.render_class_master_nodes = graph_db_config.get(
            "render_class_master_nodes", True
        )

    def _load_config(self) -> dict:
        """加载配置文件"""
        with open(self.config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return self._replace_env_vars(config)

    def _replace_env_vars(self, obj):
        """递归替换环境变量"""
        if isinstance(obj, dict):
            return {k: self._replace_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._replace_env_vars(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
            env_var = obj[2:-1]
            return os.environ.get(env_var, obj)
        return obj

    def _get_api_key(self, model_config: dict) -> str:
        """获取 API Key"""
        api_key = model_config.get("api_key")
        if api_key and api_key.startswith("${") and api_key.endswith("}"):
            api_key = os.environ.get(api_key[2:-1])
        elif not api_key:
            api_key = os.environ.get("MIMO_API_KEY")
        return api_key

    def run(self, input_text, visualize: bool = True) -> Graph:
        """
        运行完整流水线

        Args:
            input_text: 输入的自然语言文本（str 或 List[str]）
            visualize: 是否生成可视化（默认 True）

        Returns:
            生成的 Graph
        """
        logger.info("=" * 60)
        logger.info("Pipeline V2 开始运行")
        logger.info("=" * 60)

        # 处理输入：统一转为列表
        if isinstance(input_text, str):
            texts = [input_text]
        else:
            texts = list(input_text)

        logger.info(f"输入文本数量: {len(texts)} 个")

        # Step 1: 加载预定义 System（只执行一次）
        system, graph = self.step1_load_system()

        # Step 2-4: 对每个文本执行完整流程（增量更新）
        for idx, text in enumerate(texts, 1):
            logger.info("=" * 60)
            logger.info(f"处理文本 {idx}/{len(texts)}")
            logger.info("=" * 60)
            logger.info(
                f"文本内容: {text[:100]}..." if len(text) > 100 else f"文本内容: {text}"
            )

            # Step 2: 增量扩展 System
            system = self.step2_update_system(system, text)

            # Step 3: 提取实体和关系
            entities, relationships = self.step3_extract(system, text)

            # Step 4: 融合到 Graph
            graph = self.step4_combine(graph, entities, relationships)

            logger.info(
                f"文本 {idx} 处理完成，当前 Graph: {graph.get_entity_count()} 个实体, "
                f"{graph.get_relationship_count()} 个关系"
            )
            logger.info("")

        # Step 5: 保存和可视化
        self.step5_save_and_visualize(graph, visualize=visualize)

        logger.info("=" * 60)
        logger.info("Pipeline V2 运行完成")
        logger.info(
            f"最终统计: {graph.get_entity_count()} 个实体, {graph.get_relationship_count()} 个关系"
        )
        logger.info("=" * 60)

        return graph

    def step1_load_system(self) -> tuple[System, Graph]:
        """
        步骤1: 加载预定义 System 和创建 Graph

        Returns:
            (System, Graph) 元组
        """
        logger.info("=" * 60)
        logger.info("步骤1: 加载预定义 System")
        logger.info("=" * 60)

        # 从 config.yaml 加载 base_system
        system = System.from_config_file(self.config_path, use_base_system=True)

        logger.info(f"加载 System: {len(system.get_all_classes())} 个类")
        logger.info(f"类列表: {system.get_all_classes()}")
        logger.info(f"预定义实体: {len(system.predefined_entities)} 个")

        # 创建 Graph（自动注入预定义实体）
        graph = Graph(system=system, include_predefined_entities=True)

        logger.info(f"Graph 创建完成: {graph.get_entity_count()} 个实体（含预定义）")
        logger.info("")

        return system, graph

    def step2_update_system(self, system: System, text: str) -> System:
        """
        步骤2: 增量扩展 System

        Args:
            system: 现有 System
            text: 输入文本

        Returns:
            扩展后的 System
        """
        logger.info("=" * 60)
        logger.info("步骤2: 检查并增量扩展 System")
        logger.info("=" * 60)

        # 初始化 SystemUpdater
        updater = SystemUpdater(self.llm_client)

        # 检查并更新
        system, changes = updater.check_and_update(system, text, auto_apply=True)

        if changes["needed"]:
            logger.info(f"System 已扩展:")
            logger.info(f"  新增类: {changes['added_classes']}")
            logger.info(f"  增强类: {changes['enhanced_classes']}")
            logger.info(f"  原因: {changes['details']}")
        else:
            logger.info("System 无需扩展")

        logger.info(f"当前 System 包含 {len(system.get_all_classes())} 个类")
        logger.info("")

        return system

    def step3_extract(self, system: System, text: str) -> tuple[list, list]:
        """
        步骤3: 提取实体和关系

        Args:
            system: System（包含类定义）
            text: 输入文本

        Returns:
            (实体列表, 关系列表) 元组
        """
        logger.info("=" * 60)
        logger.info("步骤3: 提取实体和关系")
        logger.info("=" * 60)

        # 初始化 GraphExtractor
        extraction_config = self.config.get("extraction", {})
        prompts_config = self.config["prompts"]
        extract_prompt_path = self.prompts_dir / prompts_config["extract_graph"]

        # 准备基础实体信息（从 system.predefined_entities）
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

        # 提取
        entities, relationships = extractor.extract(text)

        logger.info(f"提取完成: {len(entities)} 个实体, {len(relationships)} 个关系")
        logger.info("")

        return entities, relationships

    def step4_combine(self, graph: Graph, entities: list, relationships: list) -> Graph:
        """
        步骤4: 融合实体和关系到 Graph

        Args:
            graph: 现有 Graph
            entities: 提取的实体列表
            relationships: 提取的关系列表

        Returns:
            融合后的 Graph
        """
        logger.info("=" * 60)
        logger.info("步骤4: 融合实体和关系到 Graph")
        logger.info("=" * 60)

        # 初始化 Combiner
        combiner = Combiner(graph, strict_validation=False)

        # 融合
        stats = combiner.combine(entities, relationships)

        logger.info(f"融合完成:")
        logger.info(
            f"  实体: 新增 {stats['entities']['added']}, 更新 {stats['entities']['updated']}, 失败 {stats['entities']['failed']}"
        )
        logger.info(
            f"  关系: 新增 {stats['relationships']['added']}, 更新 {stats['relationships']['updated']}, 失败 {stats['relationships']['failed']}"
        )
        logger.info(
            f"当前 Graph: {graph.get_entity_count()} 个实体, {graph.get_relationship_count()} 个关系"
        )
        logger.info("")

        return graph

    def step5_save_and_visualize(self, graph: Graph, visualize: bool = True):
        """
        步骤5: 保存 Graph 和可视化

        Args:
            graph: Graph 对象
            visualize: 是否生成可视化
        """
        logger.info("=" * 60)
        logger.info("步骤5: 保存和可视化")
        logger.info("=" * 60)

        # 保存 Graph
        logger.info(f"保存 Graph 到: {self.graph_storage_path}")
        graph.save(self.graph_storage_path)

        # 可视化
        if visualize:
            logger.info(f"生成可视化: {self.visualization_path}")
            visualizer = GraphVisualizer(title="Knowledge Graph")
            visualizer.from_simple_graphrag(
                graph, render_class_master_nodes=self.render_class_master_nodes
            )
            visualizer.render_to_html(self.visualization_path)

            if self.auto_open_visualization:
                logger.info("打开可视化...")
                webbrowser.open(str(self.visualization_path))

        logger.info("")

    @property
    def prompts_dir(self) -> Path:
        """提示词目录"""
        return self.config_dir


def main():
    """主函数：运行示例"""
    config_path = PROJECT_ROOT / "config" / "config.yaml"

    # 示例输入文本
    input_text = [
        "我在抖音上刷到一家网红餐厅，名叫“张三的店”，于是打开美团外卖订了他们家的招牌套餐。",
        "我用高德地图查找了“张三的店”的位置，到达后用大众点评写了一条好评。",
        "我在小红书上看到一个很有趣的关于AI绘图的视频，然后用微信分享给了小明。",
        "我在Bilibili上看到了一本《相爱一场》的书籍介绍，便在淘宝上购买了一本。",
        # "我在网易云音乐听到了一首新歌《李四的歌》，立即用QQ将这首歌的链接发给了刘五。",
        # "我在知乎上看到一个关于理财的热门回答，然后在支付宝的余额宝里增加了投资金额。",
        # "我在快手上看到有人推荐一款蓝牙耳机，名叫“王六的耳机”，随后在京东商城搜索并下单购买了。",
    ]

    pipeline = PipelineV2(config_path)

    # 方式1：处理单个文本
    # graph = pipeline.run(input_text[0], visualize=True)

    # 方式2：处理文本列表（增量更新）
    graph = pipeline.run(input_text, visualize=True)

    print("\n" + "=" * 60)
    print("最终 Graph 统计:")
    print(f"  实体: {graph.get_entity_count()} 个")
    print(f"  关系: {graph.get_relationship_count()} 个")
    print(f"  类: {len(graph.system.get_all_classes())} 个")
    print("=" * 60)


if __name__ == "__main__":
    main()
