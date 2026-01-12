"""单元测试 - PlanGenerationAgent"""

import json
from openai import OpenAI
from task_framework.subagents import PlanGenerationAgent
from task_framework.implementations import TerminalUserInput, TerminalUserInteraction
from dotenv import load_dotenv
import os

load_dotenv()


def test_plan_generation_agent():
    """测试PlanGenerationAgent"""
    print("\n" + "=" * 70)
    print("🧪 测试 PlanGenerationAgent")
    print("=" * 70)

    # 初始化客户端
    client = OpenAI(
        base_url=os.getenv("MODEL_BASE_URL", "https://api.xiaomimimo.com/v1"),
        api_key=os.getenv("MODEL_API_KEY"),
    )

    user_input = TerminalUserInput()
    user_interaction = TerminalUserInteraction()

    # 创建Agent
    agent = PlanGenerationAgent(
        user_input=user_input,
        user_interaction=user_interaction,
        model_client=client,
        model_name=os.getenv("MODEL_NAME", "mimo-v2-flash"),
        language="zh",
    )

    # 测试用例
    test_cases = [
        {
            "task_info": {
                "task_type": "外卖订餐",
                "key_info": {
                    "cuisine": "川菜",
                    "delivery_address": "家"
                },
                "constraints": []
            },
            "profile": {
                "common_apps": ["美团", "饿了么"],
                "scene_preferences": {
                    "shopping": {
                        "price_priority": "medium",
                        "app_preference": ["美团"]
                    }
                }
            }
        },
        {
            "task_info": {
                "task_type": "微信发消息",
                "key_info": {
                    "recipient": "张三",
                    "message": "晚上见"
                },
                "constraints": []
            },
            "profile": {
                "common_apps": ["微信"],
            }
        }
    ]

    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 测试用例 {i}: {test_case['task_info']['task_type']}")
        print("-" * 70)

        # 生成计划
        plan = agent.generate_plan(
            task_info=test_case["task_info"],
            user_profile=test_case["profile"]
        )

        if plan:
            print(f"\n✅ 生成的计划:")
            print(json.dumps(plan, ensure_ascii=False, indent=2))

            # 预览并确认（自动确认，不进行修改）
            print(f"\n📋 预览计划...")
            final_plan = agent.preview_and_confirm_plan(
                plan=plan,
                max_modifications=0  # 不允许修改，直接确认
            )

            if final_plan:
                print(f"\n✅ 最终计划已确认")
                results.append(final_plan)
        else:
            print(f"\n❌ 计划生成失败")

    return results


if __name__ == "__main__":
    results = test_plan_generation_agent()
    print("\n" + "=" * 70)
    print(f"✅ 测试完成，共生成 {len(results)} 个计划")
    print("=" * 70)
