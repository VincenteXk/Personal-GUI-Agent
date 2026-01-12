"""初始化功能的集成测试脚本。"""

import sys
import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from task_framework.implementations import (
    TerminalUserInput,
    TerminalUserInteraction,
)
from task_framework.subagents import (
    RiskDisclosureAgent,
    PermissionConfigAgent,
    ProfileInitAgent,
)

load_dotenv()


class OnboardingFlowTest:
    """初始化流程集成测试。"""

    def __init__(self):
        """初始化测试。"""
        self.client = OpenAI(
            base_url=os.getenv("MODEL_BASE_URL", "https://api.xiaomimimo.com/v1"),
            api_key=os.getenv("MODEL_API_KEY"),
        )
        self.user_input = TerminalUserInput()
        self.user_interaction = TerminalUserInteraction()
        self.model_name = os.getenv("MODEL_NAME", "mimo-v2-flash")
        self.language = "zh"
        self.onboarding_data = {}

    def run(self) -> None:
        """运行完整的初始化流程测试。"""
        print("\n" + "=" * 70)
        print("🚀 初始化流程集成测试")
        print("=" * 70 + "\n")

        try:
            # 第1步：风险提示
            print("\n[第1步] 风险提示")
            print("-" * 70)
            risk_agent = RiskDisclosureAgent(
                user_input=self.user_input,
                user_interaction=self.user_interaction,
                model_client=self.client,
                model_name=self.model_name,
                language=self.language,
            )
            agreed = risk_agent.run()
            if not agreed:
                print("❌ 用户未同意风险提示，中断初始化")
                return

            # 第2步：权限配置
            print("\n[第2步] 权限配置")
            print("-" * 70)
            perm_agent = PermissionConfigAgent(
                user_input=self.user_input,
                user_interaction=self.user_interaction,
                model_client=self.client,
                model_name=self.model_name,
                language=self.language,
            )
            permissions = perm_agent.run()
            self.onboarding_data["permissions"] = permissions
            print(f"\n收集的权限配置: {permissions}")

            # 第3步：初始画像
            print("\n[第3步] 初始画像创建")
            print("-" * 70)
            profile_agent = ProfileInitAgent(
                user_input=self.user_input,
                user_interaction=self.user_interaction,
                model_client=self.client,
                model_name=self.model_name,
                language=self.language,
            )
            profile = profile_agent.run()
            self.onboarding_data["profile"] = profile
            print(f"\n收集的用户画像: {profile}")
            print("\n场景偏好已集成到画像初始化中")

            # 总结
            print("\n" + "=" * 70)
            print("✅ 初始化流程完成")
            print("=" * 70)
            print(f"\n完整的初始化数据:")
            import json
            print(json.dumps(self.onboarding_data, indent=2, ensure_ascii=False))

        except KeyboardInterrupt:
            print("\n\n⚠️ 测试被中断")
        except Exception as e:
            print(f"\n\n❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()


def main():
    """主函数。"""
    test = OnboardingFlowTest()
    test.run()


if __name__ == "__main__":
    main()
