"""完整的任务调度Agent示例 - 整合所有执行器。

展示如何使用任务调度Agent整合：
1. AutoGLM PhoneAgent - 手机自动化
2. GraphRAG - 知识库查询
3. KnowledgeBase - 本地知识库
"""

from ast import Mod
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
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()


def main():
    """运行完整的任务调度Agent示例。"""

    print("=" * 70)
    print("完整任务调度Agent示例 - 整合多个执行器")
    print("=" * 70)

    # 配置大模型（如果有）
    model_config = ModelConfig(
        base_url="https://api-inference.modelscope.cn/v1",  # 替换为你的模型服务地址
        api_key=os.getenv("PHONE_AGENT_API_KEY"),  # 替换为你的API密钥
        model_name="ZhipuAI/AutoGLM-Phone-9B",  # 替换为你的模型名称
    )

    # 配置手机任务执行器
    phone_config = PhoneTaskConfig(
        device_id=None,  # 自动检测设备
        max_steps=50,
        lang="zh",
        verbose=True,
    )
    phone_executor = PhoneTaskExecutor(model_config, phone_config)

    # 配置GraphRAG查询执行器
    graphrag_config = GraphRAGConfig(
        backend_url="http://localhost:8000",  # GraphRAG后端服务地址
        timeout=30,
    )
    graphrag_executor = GraphRAGQueryExecutor(graphrag_config)

    # 汇总所有执行器
    task_executors = [
        phone_executor,
        graphrag_executor,
    ]

    # 配置任务调度Agent
    agent_config = TaskAgentConfig(
        max_steps=20,
        max_retries=3,
        verbose=True,
        language="zh",
        enable_onboarding=False,
        # 如果有大模型客户端，可以传入model相关配置
        model_base_url="https://api.xiaomimimo.com/v1",
        model_api_key="sk-cax6c5zkwtab5ue1n8hbs4upswp8me9h1s60t6u1f6yagrk0",
        model_name="mimo-v2-flash",
    )

    # 创建任务调度Agent
    agent = TaskAgent(
        user_input=TerminalUserInput(),
        user_interaction=TerminalUserInteraction(),
        task_executors=task_executors,
        # model_client=model_client,  # 如果有大模型客户端
        config=agent_config,
    )

    print("=" * 70)
    print("任务调度Agent已启动")
    print("=" * 70)
    print("\n💡 示例任务：")
    print("1. 手机任务: '打开微信，找到测试联系人1'")
    print("2. 知识查询: '查询我在微信中的常用操作'")
    print("3. GraphRAG查询: '搜索用户购物偏好'")
    print("\n注意：当前使用简化决策模式（未连接大模型）")
    print("要使用完整功能，请配置 model_client 参数\n")

    # 运行Agent
    agent.run()


def demo_direct_executor_usage():
    """演示直接使用执行器（不通过TaskAgent）。"""

    print("\n" + "=" * 70)
    print("直接使用执行器示例")
    print("=" * 70 + "\n")

    # 1. 使用知识库执行器
    print("📚 测试知识库执行器...\n")
    knowledge_executor = KnowledgeExecutor()

    # 搜索习惯
    result = knowledge_executor.execute_task(
        "search_habits", {"query": "微信", "limit": 3}, {}
    )
    print(f"✅ {result.message}")
    if result.success and result.data.get("results"):
        for i, habit in enumerate(result.data["results"][:3], 1):
            print(f"   {i}. App: {habit.get('app')}, Action: {habit.get('action')}")
    print()

    # 获取统计信息
    result = knowledge_executor.execute_task("get_statistics", {}, {})
    print(f"✅ {result.message}")
    if result.success:
        print(f"   总节点数: {result.data.get('total_nodes', 0)}")
        print(f"   应用节点: {result.data.get('app_nodes', 0)}")
        print(f"   操作节点: {result.data.get('action_nodes', 0)}")
        print(f"   总交互次数: {result.data.get('total_interactions', 0)}")
    print()

    # 2. 使用GraphRAG执行器（需要后端服务运行）
    print("🔍 测试GraphRAG查询执行器...\n")
    graphrag_executor = GraphRAGQueryExecutor()

    result = graphrag_executor.execute_task(
        "graphrag_query", {"query": "用户习惯", "query_type": "keyword", "limit": 3}, {}
    )

    if result.success:
        print(f"✅ {result.message}")
        results = result.data.get("results", [])
        for i, item in enumerate(results[:3], 1):
            print(f"   {i}. {item.get('text', item)[:50]}...")
    else:
        print(f"⚠️ {result.message}")
        print(f"   提示: 请确保GraphRAG后端服务正在运行")
    print()

    # 3. 使用手机任务执行器（需要设备连接和模型服务）
    print("📱 手机任务执行器...")
    print("   提示: 需要设备连接和模型服务，这里仅展示配置\n")

    # 展示配置示例
    print("   配置示例:")
    print("   ```python")
    print("   model_config = ModelConfig(")
    print("       base_url='http://localhost:8000/v1',")
    print("       api_key='your-api-key',")
    print("   )")
    print("   phone_executor = PhoneTaskExecutor(model_config)")
    print("   result = phone_executor.execute_task(")
    print("       'phone_automation',")
    print("       {'instruction': '打开微信'},")
    print("       {}")
    print("   )")
    print("   ```\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        # 演示直接使用执行器
        demo_direct_executor_usage()
    else:
        # 运行完整的Agent
        main()
