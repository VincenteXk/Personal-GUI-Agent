"""演示改进后的执行器能力感知功能。

展示：
1. 新的 TaskCapability 定义
2. 执行器能力如何传递给大模型
3. 系统提示词如何包含执行器信息
"""

from task_framework import TaskAgent, TaskAgentConfig
from task_framework.implementations import (
    TerminalUserInput,
    TerminalUserInteraction,
    PhoneTaskExecutor,
    PhoneTaskConfig,
    GraphRAGQueryExecutor,
    GraphRAGConfig,
)
from src.AutoGLM.model import ModelConfig


def demo_executor_capabilities():
    """演示执行器能力定义。"""
    print("=" * 80)
    print("📦 执行器能力演示")
    print("=" * 80)
    print()

    # 创建执行器
    model_config = ModelConfig(
        base_url="http://localhost:8000/v1",
        api_key="your-api-key",
    )
    phone_config = PhoneTaskConfig(verbose=False)

    phone_executor = PhoneTaskExecutor(model_config, phone_config)
    graphrag_executor = GraphRAGQueryExecutor()

    # 展示 PhoneTaskExecutor 的能力
    print("🤖 PhoneTaskExecutor 能力:")
    print("-" * 80)
    for cap in phone_executor.get_capabilities():
        print(f"\n✨ {cap.name} (task_type: {cap.task_type})")
        print(f"   描述: {cap.description}")
        print(f"   参数:")
        for param in cap.parameters:
            required = "【必需】" if param.required else "【可选】"
            print(f"     - {param.name} {required}: {param.description}")
            if param.example:
                print(f"       示例: {param.example}")
        if cap.examples:
            print(f"   示例用法:")
            for ex in cap.examples:
                print(f"     - {ex.get('description', '示例')}")
    print()

    # 展示 GraphRAGQueryExecutor 的能力
    print("\n📚 GraphRAGQueryExecutor 能力:")
    print("-" * 80)
    for cap in graphrag_executor.get_capabilities():
        print(f"\n✨ {cap.name} (task_type: {cap.task_type})")
        print(f"   描述: {cap.description}")
        print(f"   参数:")
        for param in cap.parameters:
            required = "【必需】" if param.required else "【可选】"
            print(f"     - {param.name} {required}: {param.description}")
    print()

    # 测试 can_handle 方法（现在由父类提供）
    print("\n🔍 测试 can_handle 方法:")
    print("-" * 80)
    test_types = [
        "phone_automation",
        "graphrag_query",
        "unknown_type",
    ]
    for task_type in test_types:
        phone_can = phone_executor.can_handle(task_type)
        graphrag_can = graphrag_executor.can_handle(task_type)
        print(f"{task_type}:")
        print(f"  - PhoneTaskExecutor: {'✅ 支持' if phone_can else '❌ 不支持'}")
        print(
            f"  - GraphRAGQueryExecutor: {'✅ 支持' if graphrag_can else '❌ 不支持'}"
        )


def demo_agent_with_capabilities():
    """演示 TaskAgent 如何感知执行器能力。"""
    print("\n" + "=" * 80)
    print("🧠 TaskAgent 执行器能力感知演示")
    print("=" * 80)
    print()

    # 创建执行器
    model_config = ModelConfig(
        base_url="http://localhost:8000/v1",
        api_key="your-api-key",
    )

    phone_executor = PhoneTaskExecutor(model_config, PhoneTaskConfig(verbose=False))
    graphrag_executor = GraphRAGQueryExecutor()

    # 创建 Agent（注入执行器）
    agent = TaskAgent(
        user_input=TerminalUserInput(),
        user_interaction=TerminalUserInteraction(),
        task_executors=[phone_executor, graphrag_executor],
        config=TaskAgentConfig(verbose=False, enable_onboarding=False),
    )

    # 展示系统提示词（包含执行器能力）
    print("📋 系统提示词预览 (包含执行器能力):")
    print("-" * 80)
    prompt_lines = agent.system_prompt.split("\n")

    # 只显示执行器能力部分（最后200行左右）
    # print("... (省略基础提示词部分) ...\n")

    print(agent.system_prompt)
    # 找到执行器能力部分
    # start_showing = False
    # for line in prompt_lines:
    # if "可用的任务执行器" in line:
    # start_showing = True
    # if start_showing:
    # print(line)

    print()


def demo_perception_with_executors():
    """演示感知阶段如何包含执行器状态。"""
    print("\n" + "=" * 80)
    print("👁️ 感知阶段执行器状态演示")
    print("=" * 80)
    print()

    model_config = ModelConfig(
        base_url="http://localhost:8000/v1",
        api_key="your-api-key",
    )

    phone_executor = PhoneTaskExecutor(model_config, PhoneTaskConfig(verbose=False))
    graphrag_executor = GraphRAGQueryExecutor()

    agent = TaskAgent(
        user_input=TerminalUserInput(),
        user_interaction=TerminalUserInteraction(),
        task_executors=[phone_executor, graphrag_executor],
        config=TaskAgentConfig(verbose=False, enable_onboarding=False),
    )

    # 模拟初始化上下文
    from task_framework import TaskContext, TaskState, TaskInfo

    agent.context = TaskContext(state=TaskState.IDLE)
    agent.context.task_info = TaskInfo(original_input="查询用户购物偏好并打开淘宝")

    # 获取感知信息
    perception = agent._perceive_current_state()

    print("📝 感知信息示例:")
    print("-" * 80)
    print(perception)


def main():
    """运行所有演示。"""
    import sys

    if len(sys.argv) > 1:
        demo_type = sys.argv[1]
        if demo_type == "capabilities":
            demo_executor_capabilities()
        elif demo_type == "agent":
            demo_agent_with_capabilities()
        elif demo_type == "perception":
            demo_perception_with_executors()
        else:
            print(f"❌ 未知的演示类型: {demo_type}")
            print("可用类型: capabilities, agent, perception")
    else:
        # 运行所有演示
        demo_executor_capabilities()
        demo_agent_with_capabilities()
        demo_perception_with_executors()

        print("\n" + "=" * 80)
        print("✅ 所有演示完成！")
        print("=" * 80)
        print("\n💡 要单独运行某个演示，使用:")
        print("   python examples/executor_capability_demo.py capabilities")
        print("   python examples/executor_capability_demo.py agent")
        print("   python examples/executor_capability_demo.py perception")


if __name__ == "__main__":
    main()
