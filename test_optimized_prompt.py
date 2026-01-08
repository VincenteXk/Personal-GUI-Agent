"""测试优化后的提示词生成效果"""

from task_framework.implementations import PhoneTaskExecutor, GraphRAGQueryExecutor
from task_framework.implementations.graphrag_query_executor import GraphRAGConfig

# 创建执行器
phone_executor = PhoneTaskExecutor()
graphrag_executor = GraphRAGQueryExecutor(
    GraphRAGConfig(backend_url="http://localhost:8000")
)

print("=" * 80)
print("📦 优化后的执行器能力显示")
print("=" * 80)
print()

# 显示 PhoneTaskExecutor 的能力
print("🤖 PhoneTaskExecutor 能力:")
print("-" * 80)
for cap in phone_executor.get_capabilities():
    print(f"\n✨ {cap.name} (task_type: {cap.task_type})")
    print(f"   描述: {cap.description}")

    if cap.parameters:
        print(f"   参数:")
        for param in cap.parameters:
            required = "必需" if param.required else "可选"
            print(f"     - {param.name} [{required}]: {param.description}")
            if param.example:
                print(f"       示例: {param.example}")

    if cap.examples:
        print(f"   示例用法:")
        for i, ex in enumerate(cap.examples, 1):
            print(f"     {i}. {ex.get('description', '示例')}")

    if cap.limitations:
        print(f"   限制:")
        for limit in cap.limitations:
            print(f"     - {limit}")

print()
print()

# 显示 GraphRAGQueryExecutor 的能力
print("📚 GraphRAGQueryExecutor 能力:")
print("-" * 80)
for cap in graphrag_executor.get_capabilities():
    print(f"\n✨ {cap.name} (task_type: {cap.task_type})")
    print(f"   描述: {cap.description}")

    if cap.parameters:
        print(f"   参数:")
        for param in cap.parameters:
            required = "必需" if param.required else "可选"
            print(f"     - {param.name} [{required}]: {param.description}")

    if cap.limitations:
        print(f"   限制:")
        for limit in cap.limitations:
            print(f"     - {limit}")

print()
print("=" * 80)
print("✅ 优化总结:")
print("=" * 80)
print("1. ✅ phone_automation: 从5个任务类型简化为1个")
print("2. ✅ 描述更清晰: 明确说明适合3-10步的简单操作序列")
print("3. ✅ 限制说明: 现在会在提示词中显示")
print("4. ✅ Token节省: 大幅减少提示词长度")
print()
