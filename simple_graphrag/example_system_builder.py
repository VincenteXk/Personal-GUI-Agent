"""
系统构建器使用示例

演示如何使用 SystemBuilder 从例子中构建系统配置
"""

from pathlib import Path
from src.builders.system_builder import SystemBuilder
from src.llm.client import LLMClient
from src.utils.logger import setup_logging, get_logger
from dotenv import load_dotenv
import yaml

load_dotenv()
setup_logging(verbose=True)
logger = get_logger(__name__)


def example_build_system():
    """示例1: 从例子构建系统配置"""
    logger.info("=" * 60)
    logger.info("示例1: 从例子构建系统配置")
    logger.info("=" * 60)

    # 初始化LLM客户端
    llm_client = LLMClient(
        api_key=None,  # 从环境变量读取
        base_url="https://api.xiaomimimo.com/v1",
        model="mimo-v2-flash",
    )

    # 配置文件路径
    config_path = Path(__file__).parent / "config" / "config.yaml"

    # 加载配置
    import yaml as yaml_lib

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml_lib.safe_load(f)

    # 初始化系统构建器
    prompts_config = config["prompts"]
    base_system = config.get("base_system", None)
    builder = SystemBuilder(
        llm_client=llm_client,
        core_prompt_path=config_path.parent / prompts_config["system_core"],
        rules_prompt_path=config_path.parent / prompts_config["system_rules"],
        build_prompt_path=config_path.parent / prompts_config["build_system"],
        base_system=base_system,
    )

    # 示例文本
    example_text = """
    我在小红书上拥有自己的一个账号，我经常通过小红书查找美妆教程，以及Lolita衣服，
    同时我喜欢在上面购买衣服。我拥有一个微信，微信号为"hymnly"，
    我喜欢在上面和我的一个朋友"Alice"聊天，Alice的微信号未知（没有收集到的数据），
    但是他有一个小红书号，我们在小红书上也是朋友。我另有一个微信好友"Bob"他没有微信号。
    """

    # 构建系统配置（使用统一接口）
    logger.info("开始构建系统配置...")
    system_config = builder.build_or_extend_system(example_text)

    # 输出结果
    logger.info("\n构建的系统配置:")
    logger.info("=" * 60)
    print(yaml.dump(system_config, allow_unicode=True, default_flow_style=False))
    logger.info("=" * 60)


def example_validate_and_extend():
    """示例2: 验证现有系统并扩展"""
    logger.info("\n" + "=" * 60)
    logger.info("示例2: 验证现有系统并扩展")
    logger.info("=" * 60)

    # 初始化LLM客户端
    llm_client = LLMClient(
        api_key=None,
        base_url="https://api.xiaomimimo.com/v1",
        model="mimo-v2-flash",
    )

    # 配置文件路径
    config_path = Path(__file__).parent / "config" / "config.yaml"

    # 加载配置
    import yaml as yaml_lib

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml_lib.safe_load(f)

    # 初始化系统构建器
    prompts_config = config["prompts"]
    base_system = config.get("base_system", None)
    builder = SystemBuilder(
        llm_client=llm_client,
        core_prompt_path=config_path.parent / prompts_config["system_core"],
        rules_prompt_path=config_path.parent / prompts_config["system_rules"],
        build_prompt_path=config_path.parent / prompts_config["build_system"],
        base_system=base_system,
    )

    # 现有系统配置（包含基础架构 + 部分类）
    existing_system = {
        "classes": {
            "用户": {
                "description": "用户本人，执行操作的主体",
                "properties": [],
            },
            "可启动应用": {
                "description": "可以被(我)启动的应用程序",
                "properties": [
                    {
                        "name": "启动方式",
                        "required": True,
                        "value_required": True,
                        "description": "应用的启动方式",
                    }
                ],
            },
            "联系人": {
                "description": "联系人",
                "properties": [
                    {
                        "name": "关系类型",
                        "required": False,
                        "value_required": False,
                        "description": "联系人的关系类型",
                    }
                ],
            },
        }
    }

    # 新的示例文本（包含现有系统无法表示的信息）
    new_example_text = """
    我在小红书上拥有自己的一个账号，我经常通过小红书查找美妆教程，以及Lolita衣服，
    同时我喜欢在上面购买衣服。我拥有一个微信，微信号为"hymnly"。
    """

    # 验证并扩展系统（使用统一接口）
    logger.info("开始验证现有系统...")
    is_adequate, updated_system, message = builder.validate_and_extend_system(
        existing_system, new_example_text
    )

    logger.info(f"\n验证结果: {'系统充分' if is_adequate else '系统需要扩展'}")
    logger.info(f"消息: {message}")

    if not is_adequate and updated_system:
        logger.info("\n扩展后的系统配置:")
        logger.info("=" * 60)
        print(yaml.dump(updated_system, allow_unicode=True, default_flow_style=False))
        logger.info("=" * 60)


if __name__ == "__main__":
    try:
        example_build_system()
        example_validate_and_extend()
    except Exception as e:
        logger.error(f"示例运行失败: {e}", exc_info=True)
