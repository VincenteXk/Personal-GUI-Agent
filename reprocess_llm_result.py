"""
重新处理现有的LLM分析结果，使用改进的JSON解析器
"""
import json
import sys
import os

sys.path.insert(0, r'd:\Xianker\课外项目\Personal-GUI-Agent')

from src.learning.vlm_analyzer import VLMAnalyzer


def reprocess_llm_analysis(analysis_file: str):
    """重新处理LLM分析结果文件"""
    print("=" * 60)
    print("重新处理LLM分析结果")
    print("=" * 60)

    # 读取现有文件
    with open(analysis_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"\n原始文件: {analysis_file}")
    print(f"分析时间: {data.get('analysis_time')}")
    print(f"使用模型: {data.get('model')}")

    # 提取原始响应
    result = data.get('result', {})
    analysis = result.get('analysis', {})

    if 'raw_response' not in analysis:
        print("\n❌ 未找到raw_response字段，无法重新处理")
        return False

    raw_response = analysis['raw_response']
    print(f"\n原始响应长度: {len(raw_response)}")

    # 使用改进的JSON解析器
    try:
        parsed_json = VLMAnalyzer.extract_json_from_response(raw_response)
        print("\n✅ JSON解析成功！")

        # 更新分析结果
        data['result']['analysis'] = parsed_json
        data['result']['analysis']['raw_response'] = raw_response

        # 保留reasoning
        if 'reasoning' in analysis:
            data['result']['analysis']['reasoning'] = analysis['reasoning']

        # 移除error字段
        if 'error' in data['result']['analysis']:
            del data['result']['analysis']['error']

        # 保存更新后的文件
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\n✅ 文件已更新: {analysis_file}")

        # 显示解析后的内容
        print("\n" + "=" * 60)
        print("解析后的内容摘要")
        print("=" * 60)
        print(f"应用名称: {parsed_json.get('app_name')}")
        print(f"主要行为: {parsed_json.get('main_action')}")
        print(f"用户意图: {parsed_json.get('intent')}")
        print(f"置信度: {parsed_json.get('confidence')}")

        detailed_actions = parsed_json.get('detailed_actions', [])
        print(f"\n详细操作数: {len(detailed_actions)}")

        if detailed_actions:
            print("\n前3个操作:")
            for i, action in enumerate(detailed_actions[:3], 1):
                print(f"  {i}. {action.get('time')}: {action.get('action')}")

        return True

    except ValueError as e:
        print(f"\n❌ JSON解析失败: {e}")
        return False


def main():
    """主函数"""
    analysis_file = r"d:\Xianker\课外项目\Personal-GUI-Agent\data\processed\analysis\session_2026-01-10T00-49-29.661000Z_llm_analysis_20260110_005106.json"

    if not os.path.exists(analysis_file):
        print(f"❌ 文件不存在: {analysis_file}")
        return 1

    success = reprocess_llm_analysis(analysis_file)

    if success:
        print("\n" + "=" * 60)
        print("✅ 重新处理完成")
        print("=" * 60)
        print("\n现在可以:")
        print("1. 使用更新后的分析结果")
        print("2. 将结果传递给后续处理流程")
        print("3. 查看完整的用户行为分析")
        return 0
    else:
        print("\n❌ 重新处理失败")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
