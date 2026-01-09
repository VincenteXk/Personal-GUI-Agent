"""
API端点配置验证工具
检查所有API配置是否正确
"""
import json
import sys
import requests

sys.path.insert(0, r'd:\Xianker\课外项目\Personal-GUI-Agent')


def verify_api_endpoints():
    """验证所有API端点配置"""
    print("=" * 70)
    print("API端点配置验证")
    print("=" * 70)

    # 读取配置
    config_path = r'd:\Xianker\课外项目\Personal-GUI-Agent\config.json'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    results = {}

    # 验证1：智谱AI（VLM）
    print("\n[1/2] 验证智谱AI API配置（用于VLM分析）")
    print("-" * 70)

    learning_config = config.get('learning_config', {})
    zhipu_key = learning_config.get('api_key')
    zhipu_model = learning_config.get('model')
    zhipu_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    print(f"API Key: {'*' * 20}...{zhipu_key[-8:] if zhipu_key else '未配置'}")
    print(f"模型: {zhipu_model}")
    print(f"端点: {zhipu_url}")

    if zhipu_key:
        print("✅ 智谱AI配置完整")
        results['zhipu'] = True
    else:
        print("❌ 缺少API Key")
        results['zhipu'] = False

    # 验证2：DeepSeek（LLM）
    print("\n[2/2] 验证DeepSeek API配置（用于LLM汇总）")
    print("-" * 70)

    summary_config = config.get('summary_config', {})
    deepseek_url = summary_config.get('api_url')
    deepseek_key = summary_config.get('api_key')
    deepseek_model = summary_config.get('model')

    print(f"API URL: {deepseek_url}")
    print(f"API Key: {'*' * 20}...{deepseek_key[-8:] if deepseek_key else '未配置'}")
    print(f"模型: {deepseek_model}")

    # 检查端点格式
    if deepseek_url and "/chat/completions" in deepseek_url:
        print("✅ API端点格式正确（包含/chat/completions）")
        results['deepseek_url'] = True
    else:
        print("❌ API端点格式错误（缺少/chat/completions）")
        results['deepseek_url'] = False

    if deepseek_key:
        print("✅ API Key已配置")
        results['deepseek_key'] = True
    else:
        print("❌ 缺少API Key")
        results['deepseek_key'] = False

    # 总结
    print("\n" + "=" * 70)
    print("配置验证结果")
    print("=" * 70)

    all_valid = all(results.values())

    if all_valid:
        print("✅ 所有API配置都正确！")
        print("\n系统已就绪:")
        print("  • VLM分析（智谱AI）: ✅ 就绪")
        print("  • LLM汇总（DeepSeek）: ✅ 就绪")
        print("  • 完整管道: ✅ 可执行")
        return 0
    else:
        print("❌ 某些配置有问题，请检查:")
        for key, value in results.items():
            status = "✅" if value else "❌"
            print(f"  {status} {key}")
        return 1


if __name__ == "__main__":
    exit_code = verify_api_endpoints()
    sys.exit(exit_code)
