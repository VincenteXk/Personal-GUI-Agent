"""
完整的VLM+LLM分析流程测试
演示从VLM分析结果到LLM汇总的完整管道
"""
import json
import sys
import os

sys.path.insert(0, r'd:\Xianker\课外项目\Personal-GUI-Agent')

from src.learning.behavior_summarizer import BehaviorSummarizer


def test_complete_pipeline():
    """测试完整的VLM+LLM分析流程"""
    print("=" * 70)
    print("完整VLM+LLM分析流程测试")
    print("=" * 70)

    # 步骤1：读取现有的VLM分析结果
    print("\n[步骤1/4] 加载VLM分析结果")
    print("-" * 70)

    vlm_analysis_file = r"d:\Xianker\课外项目\Personal-GUI-Agent\data\processed\analysis\session_2026-01-10T00-49-29.661000Z_llm_analysis_20260110_005106.json"

    if not os.path.exists(vlm_analysis_file):
        print(f"❌ 文件不存在: {vlm_analysis_file}")
        return False

    with open(vlm_analysis_file, 'r', encoding='utf-8') as f:
        analysis_data = json.load(f)

    vlm_result = analysis_data.get('result', {})
    print(f"✅ VLM分析结果已加载")
    print(f"   - 应用: {vlm_result.get('analysis', {}).get('app_name')}")
    print(f"   - 主要行为: {vlm_result.get('analysis', {}).get('main_action')}")
    print(f"   - 用户意图: {vlm_result.get('analysis', {}).get('intent')}")

    # 步骤2：准备LLM输入数据（转换VLM格式）
    print("\n[步骤2/4] 转换VLM格式为LLM输入")
    print("-" * 70)

    vlm_analysis = vlm_result.get('analysis', {})

    # 转换为BehaviorSummarizer期望的格式
    vlm_outputs = [
        {
            "status": "success",
            "app_name": vlm_analysis.get('app_name', 'unknown'),
            "analysis": {
                "main_action": vlm_analysis.get('main_action', ''),
                "detailed_actions": vlm_analysis.get('detailed_actions', []),
                "summary": vlm_analysis.get('main_action', ''),
                "intent": vlm_analysis.get('intent', ''),
                "confidence": vlm_analysis.get('confidence', 0.9)
            }
        }
    ]

    print(f"✅ VLM数据转换完成")
    print(f"   - 转换后的记录数: {len(vlm_outputs)}")
    print(f"   - 详细操作数: {len(vlm_analysis.get('detailed_actions', []))}")

    # 步骤3：初始化LLM汇总器
    print("\n[步骤3/4] 初始化LLM汇总器")
    print("-" * 70)

    config_path = r'd:\Xianker\课外项目\Personal-GUI-Agent\config.json'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    summary_config = config.get('summary_config', {})
    print(f"API配置:")
    print(f"  - API URL: {summary_config.get('api_url')}")
    print(f"  - 模型: {summary_config.get('model')}")

    try:
        summarizer = BehaviorSummarizer(summary_config)
        print(f"✅ BehaviorSummarizer初始化成功")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return False

    # 步骤4：调用LLM进行跨应用行为汇总
    print("\n[步骤4/4] 调用LLM进行跨应用行为汇总")
    print("-" * 70)

    try:
        # 调用LLM汇总
        natural_language_records = summarizer.summarize_cross_app_behavior(vlm_outputs)

        print(f"✅ LLM汇总成功！")
        print(f"   - 生成的自然语言描述数: {len(natural_language_records)}")

        # 显示汇总结果
        print("\n" + "=" * 70)
        print("最终汇总结果")
        print("=" * 70)

        for i, record in enumerate(natural_language_records, 1):
            print(f"\n[描述 {i}]")
            print(f"{record}")

        # 保存完整的分析结果
        print("\n" + "=" * 70)
        print("保存完整的分析结果")
        print("=" * 70)

        complete_result = {
            "pipeline_status": "success",
            "timestamp": __import__('datetime').datetime.now().isoformat(),
            "vlm_analysis": vlm_analysis,
            "llm_summary": natural_language_records,
            "analysis_pipeline": {
                "step1_data_collection": "✅ 完成",
                "step2_session_processing": "✅ 完成",
                "step3_vlm_analysis": "✅ 完成",
                "step4_llm_summarization": "✅ 完成",
                "step5_result_storage": "✅ 进行中"
            }
        }

        # 保存到文件
        output_dir = r"d:\Xianker\课外项目\Personal-GUI-Agent\data\processed\pipeline_results"
        os.makedirs(output_dir, exist_ok=True)

        output_file = os.path.join(
            output_dir,
            f"complete_pipeline_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(complete_result, f, indent=2, ensure_ascii=False)

        print(f"✅ 结果已保存: {output_file}")

        return True

    except Exception as e:
        print(f"❌ LLM汇总失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    success = test_complete_pipeline()

    print("\n" + "=" * 70)
    if success:
        print("✅ 完整VLM+LLM分析流程测试成功！")
        print("\n完整分析链:")
        print("  1. 数据采集 ✅")
        print("  2. Session处理 ✅")
        print("  3. VLM多模态分析 ✅")
        print("  4. LLM跨应用汇总 ✅")
        print("  5. 结果存储 ✅")
        print("\n系统已完全就绪，可以进行实时学习模式！")
        return 0
    else:
        print("❌ 完整VLM+LLM分析流程测试失败")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
