"""集成测试 - 完整的任务流程"""

import json
import uuid
from openai import OpenAI
from task_framework.subagents import (
    MinimalAskAgent,
    PlanGenerationAgent,
    PreferenceUpdateAgent,
)
from task_framework.implementations import TerminalUserInput, TerminalUserInteraction
from task_framework.utils import ContextManager, PermissionManager
from dotenv import load_dotenv
import os

load_dotenv()


class IntegratedTaskFlow:
    """集成的任务流程"""

    def __init__(self):
        """初始化"""
        self.client = OpenAI(
            base_url=os.getenv("MODEL_BASE_URL", "https://api.xiaomimimo.com/v1"),
            api_key=os.getenv("MODEL_API_KEY"),
        )
        self.model_name = os.getenv("MODEL_NAME", "mimo-v2-flash")
        self.user_input = TerminalUserInput()
        self.user_interaction = TerminalUserInteraction()
        self.context_manager = ContextManager()
        self.permission_manager = PermissionManager()

        # 初始化各个Agent
        self.minimal_ask_agent = MinimalAskAgent(
            user_input=self.user_input,
            user_interaction=self.user_interaction,
            model_client=self.client,
            model_name=self.model_name,
            language="zh",
        )

        self.plan_agent = PlanGenerationAgent(
            user_input=self.user_input,
            user_interaction=self.user_interaction,
            model_client=self.client,
            model_name=self.model_name,
            language="zh",
        )

        self.preference_agent = PreferenceUpdateAgent(
            user_interaction=self.user_interaction,
            model_client=self.client,
            model_name=self.model_name,
            language="zh",
            context_manager=self.context_manager,
        )

    def execute_task(self, user_instruction: str, user_profile: dict = None) -> bool:
        """
        执行完整的任务流程。

        Args:
            user_instruction: 用户指令
            user_profile: 用户画像

        Returns:
            是否成功
        """
        if user_profile is None:
            user_profile = {}

        task_id = str(uuid.uuid4())
        print(f"\n{'=' * 70}")
        print(f"📌 任务ID: {task_id}")
        print(f"📝 用户指令: {user_instruction}")
        print(f"{'=' * 70}\n")

        # 创建Context
        context = self.context_manager.create_context(task_id)
        self.context_manager.save_context(context)

        try:
            # 第1步：分析任务并追问
            print("📋 第1步：分析任务并追问缺失信息...")
            print("-" * 70)
            task_info = self.minimal_ask_agent.analyze_and_ask(
                user_instruction=user_instruction,
                user_profile=user_profile,
                max_rounds=2
            )
            print(f"✅ 任务分析完成")
            print(json.dumps(task_info, ensure_ascii=False, indent=2))

            # 第2步：生成计划
            print(f"\n📋 第2步：生成执行计划...")
            print("-" * 70)
            plan = self.plan_agent.generate_plan(
                task_info=task_info,
                user_profile=user_profile
            )

            if not plan:
                print("❌ 计划生成失败")
                return False

            print(f"✅ 计划生成完成")

            # 第3步：预览并确认计划
            print(f"\n📋 第3步：预览计划...")
            print("-" * 70)
            final_plan = self.plan_agent.preview_and_confirm_plan(
                plan=plan,
                max_modifications=2
            )

            if not final_plan:
                print("❌ 计划被拒绝")
                return False

            print(f"✅ 计划已确认")

            # 第4步：模拟执行（这里只是演示，实际执行由AutoGLM处理）
            print(f"\n📋 第4步：模拟任务执行...")
            print("-" * 70)
            print(f"应用: {final_plan.get('app', 'N/A')}")
            print(f"步骤数: {len(final_plan.get('steps', []))}")
            print(f"风险等级: {final_plan.get('risk_level', 'N/A')}")

            # 更新Context（模拟执行结果）
            self.context_manager.add_user_choice(
                task_id,
                "execution_status",
                "completed"
            )
            self.context_manager.add_observation(
                task_id,
                "final_result",
                "任务执行成功"
            )
            print(f"✅ 任务执行完成（模拟）")

            # 第5步：分析偏好并询问是否更新
            print(f"\n📋 第5步：分析偏好并询问是否更新...")
            print("-" * 70)
            preference_update = self.preference_agent.analyze_and_update(
                task_id=task_id,
                user_profile=user_profile,
                execution_history=[]
            )

            if preference_update:
                print(f"✅ 偏好更新建议已生成")
            else:
                print(f"⚠️ 无需更新偏好")

            # 清理Context
            print(f"\n📋 清理Context...")
            self.context_manager.delete_context(task_id)
            print(f"✅ Context已清理")

            print(f"\n{'=' * 70}")
            print(f"✅ 任务流程完成")
            print(f"{'=' * 70}\n")

            return True

        except Exception as e:
            print(f"\n❌ 任务执行出错: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("🧪 集成测试 - 完整的任务流程")
    print("=" * 70)

    flow = IntegratedTaskFlow()

    # 测试用例
    test_cases = [
        {
            "instruction": "我想点份川菜外卖",
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
            "instruction": "给张三发条消息说晚上见",
            "profile": {
                "common_apps": ["微信"],
            }
        }
    ]

    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔄 执行测试用例 {i}/{len(test_cases)}")
        success = flow.execute_task(
            user_instruction=test_case["instruction"],
            user_profile=test_case["profile"]
        )
        results.append(success)

    # 总结
    print("\n" + "=" * 70)
    print("📊 测试总结")
    print("=" * 70)
    print(f"总用例数: {len(results)}")
    print(f"成功: {sum(results)}")
    print(f"失败: {len(results) - sum(results)}")
    print(f"成功率: {sum(results) / len(results) * 100:.1f}%")
    print("=" * 70 + "\n")

    return all(results)


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
