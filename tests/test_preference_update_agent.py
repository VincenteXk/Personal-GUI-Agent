"""单元测试 - PreferenceUpdateAgent"""

import json
import uuid
from openai import OpenAI
from task_framework.subagents import PreferenceUpdateAgent
from task_framework.implementations import TerminalUserInteraction
from task_framework.utils import ContextManager
from dotenv import load_dotenv
import os

load_dotenv()


def test_preference_update_agent():
    """测试PreferenceUpdateAgent"""
    print("\n" + "=" * 70)
    print("🧪 测试 PreferenceUpdateAgent")
    print("=" * 70)

    # 初始化客户端
    client = OpenAI(
        base_url=os.getenv("MODEL_BASE_URL", "https://api.xiaomimimo.com/v1"),
        api_key=os.getenv("MODEL_API_KEY"),
    )

    user_interaction = TerminalUserInteraction()
    context_manager = ContextManager()

    # 创建Agent
    agent = PreferenceUpdateAgent(
        user_interaction=user_interaction,
        model_client=client,
        model_name=os.getenv("MODEL_NAME", "mimo-v2-flash"),
        language="zh",
        context_manager=context_manager,
    )

    # 测试用例
    test_cases = [
        {
            "name": "外卖订餐 - 价格优先",
            "task_context": {
                "user_choices_in_session": {
                    "chosen_restaurant": "餐厅A",
                    "price": 30,
                    "distance": "1km"
                },
                "current_observations": {
                    "restaurants_seen": [
                        {"name": "餐厅A", "price": 30, "distance": "1km"},
                        {"name": "餐厅B", "price": 80, "distance": "2km"},
                        {"name": "餐厅C", "price": 35, "distance": "1.5km"}
                    ]
                }
            },
            "profile": {
                "scene_preferences": {
                    "shopping": {
                        "price_priority": "medium"
                    }
                }
            }
        },
        {
            "name": "微信发消息 - 消息风格",
            "task_context": {
                "user_choices_in_session": {
                    "recipient": "张三",
                    "message_tone": "friendly"
                },
                "current_observations": {
                    "message_content": "晚上见"
                }
            },
            "profile": {
                "scene_preferences": {
                    "social": {
                        "message_tone": "formal"
                    }
                }
            }
        }
    ]

    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 测试用例 {i}: {test_case['name']}")
        print("-" * 70)

        # 创建Context
        task_id = str(uuid.uuid4())
        context = context_manager.create_context(task_id)
        context.update(test_case["task_context"])
        context_manager.save_context(context)

        print(f"Task ID: {task_id}")
        print(f"Context: {json.dumps(test_case['task_context'], ensure_ascii=False, indent=2)}")

        # 分析并询问是否更新偏好
        preference_update = agent.analyze_and_update(
            task_id=task_id,
            user_profile=test_case["profile"],
            execution_history=[]
        )

        if preference_update:
            print(f"\n✅ 偏好更新建议:")
            print(json.dumps(preference_update, ensure_ascii=False, indent=2))
            results.append(preference_update)
        else:
            print(f"\n⚠️ 无需更新偏好或用户拒绝")

        # 清理Context
        context_manager.delete_context(task_id)

    return results


if __name__ == "__main__":
    results = test_preference_update_agent()
    print("\n" + "=" * 70)
    print(f"✅ 测试完成，共生成 {len(results)} 个偏好更新建议")
    print("=" * 70)
