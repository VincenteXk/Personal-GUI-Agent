"""简单的任务Agent使用示例。"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from task_framework import TaskAgent, TaskAgentConfig
from task_framework.implementations import TerminalUserInput, TerminalUserInteraction


def main():
    """运行简单的任务Agent示例。"""
    print("="*60)
    print("任务执行框架 - 简单示例")
    print("="*60)
    
    # 创建配置
    config = TaskAgentConfig(
        verbose=True,
        max_steps=20,
        enable_onboarding=True,
        language="zh",
    )
    
    # 创建用户输入和交互接口
    user_input = TerminalUserInput()
    user_interaction = TerminalUserInteraction()
    
    # 创建任务Agent
    agent = TaskAgent(
        user_input=user_input,
        user_interaction=user_interaction,
        config=config,
    )
    
    # 运行Agent
    try:
        agent.run()
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
    except Exception as e:
        print(f"\n\n发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
