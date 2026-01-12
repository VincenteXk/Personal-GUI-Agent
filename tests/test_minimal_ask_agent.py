"""单元测试 - MinimalAskAgent"""

import json
from openai import OpenAI
from task_framework.subagents import MinimalAskAgent
from task_framework.implementations import TerminalUserInput, TerminalUserInteraction
from dotenv import load_dotenv
import os

load_dotenv()


def test_minimal_ask_agent():
    """测试MinimalAskAgent"""
    print("\n" + "=" * 70)
    print("🧪 测试 MinimalAskAgent")
    print("=" * 70)

    # 初始化客户端
    client = OpenAI(
        base_url=os.getenv("MODEL_BASE_URL", "https://api.xiaomimimo.com/v1"),
        api_key=os.getenv("MODEL_API_KEY"),
    )

    user_input = TerminalUserInput()
    user_interaction = TerminalUserInteraction()

    # 创建Agent
    agent = MinimalAskAgent(
        user_input=user_input,
        user_interaction=user_interaction,
        model_client=client,
        model_name=os.getenv("MODEL_NAME", "mimo-v2-flash"),
        language="zh",
    )

    # 测试用例
    test_cases = [
        {
            "instruction": "我想点份川菜外卖",
            "profile": {
                "common_apps": ["美团", "饿了么"],
                "scene_preferences": {
                    "shopping": {
                        "app_preference": ["美团", "饿了么"]
                    }
                }
            }
        },
        {
            "instruction": "给张三发条消息说晚上见",
            "profile": {
                "common_apps": ["微信"],
            }
        },
        {
            "instruction": "删除照片里的截图",
            "profile": {}
        }
    ]

    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 测试用例 {i}: {test_case['instruction']}")
        print("-" * 70)

        task_info = agent.analyze_and_ask(
            user_instruction=test_case["instruction"],
            user_profile=test_case["profile"],
            max_rounds=2
        )

        print(f"\n✅ 分析结果:")
        print(json.dumps(task_info, ensure_ascii=False, indent=2))
        results.append(task_info)

    return results


if __name__ == "__main__":
    results = test_minimal_ask_agent()
    print("\n" + "=" * 70)
    print(f"✅ 测试完成，共处理 {len(results)} 个用例")
    print("=" * 70)
