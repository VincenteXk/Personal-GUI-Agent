"""
文本转换器使用示例

演示如何使用 TextConverter 将简略内容转换为丰富的自然语言文本
"""

from pathlib import Path
from src.llm.client import LLMClient
from src.utils.logger import setup_logging, get_logger
from dotenv import load_dotenv

load_dotenv()
setup_logging(verbose=True)
logger = get_logger(__name__)


def example_text_converter():
    """示例: 使用文本转换器将简略内容转换为丰富的自然语言"""
    logger.info("=" * 60)
    logger.info("示例: 文本转换器")
    logger.info("=" * 60)

    # 初始化LLM客户端
    llm_client = LLMClient(
        api_key=None,  # 从环境变量读取
        base_url="https://api.xiaomimimo.com/v1",
        model="mimo-v2-flash",
    )

    # 加载提示词模板
    config_path = Path(__file__).parent / "config" / "config.yaml"
    prompt_path = Path(__file__).parent / "config" / "prompts" / "text_converter.txt"

    prompt_template = LLMClient.load_prompt_template(prompt_path)
    logger.info(f"已加载提示词模板: {prompt_path}")

    # 示例输入：简略的笔记或结构化内容
    example_inputs = [
        # 示例1: 简略笔记
        """- 小红书账号
- 查找美妆教程
- 购买衣服
- 微信，微信号hymnly
- 朋友Alice，小红书号""",
        # 示例2: 结构化列表
        """应用使用情况：
1. 抖音 - 观看短视频，关注美食博主
2. 淘宝 - 购买电子产品，收藏店铺
3. 微信 - 微信号：mywechat123，与同事Bob聊天""",
        # 示例3: 关键词列表
        """手机应用：小红书、微信、支付宝
活动：购物、聊天、支付
联系人：Alice（微信好友）、Bob（小红书关注）""",
    ]

    for i, input_content in enumerate(example_inputs, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"示例 {i}:")
        logger.info(f"{'='*60}")
        logger.info(f"输入内容:\n{input_content}\n")

        # 格式化提示词
        prompt = prompt_template.format(input_content=input_content)

        # 调用LLM
        logger.info("调用LLM进行文本转换...")
        messages = [{"role": "user", "content": prompt}]
        response = llm_client.chat_completion(messages, temperature=0.7)

        logger.info(f"\n转换后的自然语言文本:")
        logger.info(f"{response}\n")


if __name__ == "__main__":
    try:
        example_text_converter()
        logger.info("=" * 60)
        logger.info("示例运行完成")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"示例运行失败: {e}", exc_info=True)
