"""完整集成测试 - 验证TaskAgentV2的完整流程"""

import json
from openai import OpenAI
from task_framework.agent_v2 import TaskAgentV2
from task_framework.config import TaskAgentConfig
from task_framework.implementations import (
    TerminalUserInput,
    TerminalUserInteraction,
)
from dotenv import load_dotenv
import os

load_dotenv()


class IntegrationTestRunner:
    """集成测试运行器"""

    def __init__(self):
        """初始化"""
        self.client = OpenAI(
            base_url=os.getenv("MODEL_BASE_URL", "https://api.xiaomimimo.com/v1"),
            api_key=os.getenv("MODEL_API_KEY"),
        )
        self.user_input = TerminalUserInput()
        self.user_interaction = TerminalUserInteraction()

    def run_scenario(self, scenario_name: str, user_instruction: str) -> bool:
        """
        运行单个场景测试。

        Args:
            scenario_name: 场景名称
            user_instruction: 用户指令

        Returns:
            是否成功
        """
        print(f"\n{'=' * 70}")
        print(f"🧪 场景测试: {scenario_name}")
        print(f"📝 指令: {user_instruction}")
        print(f"{'=' * 70}\n")

        try:
            # 配置Agent
            config = TaskAgentConfig(
                max_steps=20,
                max_retries=3,
                verbose=True,
                language="zh",
                enable_onboarding=False,
                enable_minimal_ask=True,
                enable_plan_preview=True,
                enable_preference_update=True,
                cleanup_context_after_task=True,
                model_base_url=os.getenv("MODEL_BASE_URL"),
                model_api_key=os.getenv("MODEL_API_KEY"),
                model_name=os.getenv("MODEL_NAME", "mimo-v2-flash"),
            )

            # 创建Agent
            agent = TaskAgentV2(
                user_input=self.user_input,
                user_interaction=self.user_interaction,
                model_client=self.client,
                config=config,
            )

            # 执行任务流程
            result = agent._execute_task_flow(user_instruction)

            print(f"\n✅ 场景完成: {result}")
            return True

        except Exception as e:
            print(f"\n❌ 场景失败: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("🚀 完整集成测试 - TaskAgentV2")
    print("=" * 70)

    runner = IntegrationTestRunner()

    # 测试场景
    scenarios = [
        {
            "name": "外卖订餐",
            "instruction": "我想点份川菜外卖"
        },
        {
            "name": "微信发消息",
            "instruction": "给张三发条消息说晚上见"
        },
        {
            "name": "删除文件",
            "instruction": "删除照片里的截图"
        }
    ]

    results = {}
    for scenario in scenarios:
        success = runner.run_scenario(
            scenario_name=scenario["name"],
            user_instruction=scenario["instruction"]
        )
        results[scenario["name"]] = success

    # 总结
    print("\n" + "=" * 70)
    print("📊 测试总结")
    print("=" * 70)
    for name, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status}: {name}")

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\n总计: {passed}/{total} 通过")
    print("=" * 70 + "\n")

    return all(results.values())


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
