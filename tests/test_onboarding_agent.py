"""单元测试 - OnboardingAgent"""

import json
from openai import OpenAI
from task_framework.subagents import OnboardingAgent
from task_framework.implementations import TerminalUserInteraction, TerminalUserInput
from dotenv import load_dotenv
import os

load_dotenv()


def test_onboarding_agent():
    """测试OnboardingAgent"""
    print("\n" + "=" * 70)
    print("🧪 测试 OnboardingAgent")
    print("=" * 70)

    # 初始化客户端
    client = OpenAI(
        base_url=os.getenv("MODEL_BASE_URL", "https://api.xiaomimimo.com/v1"),
        api_key=os.getenv("MODEL_API_KEY"),
    )

    user_interaction = TerminalUserInteraction()
    user_input = TerminalUserInput()

    # 创建Agent
    agent = OnboardingAgent(
        user_interaction=user_interaction,
        user_input=user_input,
        model_client=client,
        model_name=os.getenv("MODEL_NAME", "mimo-v2-flash"),
        language="zh",
        permissions_config_path="config/permissions.json",
    )

    print("\n📝 开始引导流程...")
    print("提示：输入选项编号或选项名称，输入 'exit' 退出\n")

    # 运行引导
    config = agent.run()

    if config:
        print("\n✅ 引导完成！")
        print(f"用户ID: {config.user_id}")
        print(f"权限配置: {json.dumps(config.permissions, ensure_ascii=False, indent=2)}")
        print(f"元偏好: {json.dumps(config.meta_preferences, ensure_ascii=False, indent=2)}")
        return True
    else:
        print("\n❌ 引导失败或被取消")
        return False


if __name__ == "__main__":
    success = test_onboarding_agent()
    exit(0 if success else 1)
