"""
Descripttion:
Author: Sion's pota
version:
Date: 2026-01-08 16:57:14
LastEditors: Sion's pota
LastEditTime: 2026-01-08 16:57:37
"""

"""任务调度Agent使用示例。

演示新的"感知-思考-行动"循环架构。
"""

from task_framework import TaskAgent, TaskAgentConfig
from task_framework.implementations import TerminalUserInput, TerminalUserInteraction


def main():
    """运行任务调度Agent示例。"""

    # 配置Agent
    config = TaskAgentConfig(
        max_steps=20,
        max_retries=3,
        verbose=True,
        language="zh",
        enable_onboarding=False,  # 跳过首次引导
        enable_voice_input=False,
    )

    # 创建Agent实例
    agent = TaskAgent(
        user_input=TerminalUserInput(),
        user_interaction=TerminalUserInteraction(),
        config=config,
        # 如果有大模型客户端，可以传入：
        # model_client=your_model_client,
    )

    print("=" * 60)
    print("任务调度Agent示例 - 感知-思考-行动循环")
    print("=" * 60)
    print("\n架构特点：")
    print("- 🧠 大模型驱动的决策（而非预定义工作流）")
    print("- 🔄 感知-思考-行动循环")
    print("- 📝 记录已执行步骤和结果")
    print("- 🎯 动态调整执行路径")
    print("- 🤝 智能用户交互")
    print("\n注意：当前使用简化的决策逻辑（未连接大模型）")
    print("要使用完整功能，请配置并传入 model_client\n")

    # 运行Agent
    agent.run()


if __name__ == "__main__":
    main()
