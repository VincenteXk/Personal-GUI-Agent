"""
行为链汇总模块 - 将多个VLM的应用级分析汇总为自然语言操作记录
"""
import json
from typing import List, Dict, Any
import requests


class BehaviorSummarizer:
    """将多个VLM的应用级分析汇总为自然语言操作记录"""

    def __init__(self, llm_config: Dict[str, Any]):
        """
        初始化行为汇总器

        Args:
            llm_config: LLM配置，包含api_key、model、api_url等
        """
        self.api_key = llm_config.get('api_key', '')
        self.model = llm_config.get('model', 'glm-4')
        self.api_url = llm_config.get('api_url', 'https://open.bigmodel.cn/api/paas/v4/chat/completions')
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def summarize_cross_app_behavior(self, vlm_outputs: List[Dict[str, Any]]) -> List[str]:
        """
        跨应用行为汇总

        输入: List[VLMAnalysisResult]
        输出: List[自然语言描述]

        示例输入:
        [
          {"app": "Chrome", "actions": [{"type": "search", "target": "火锅"}], "summary": "搜索火锅"},
          {"app": "美团", "actions": [{"type": "browse"}, {"type": "order"}], "summary": "浏览并下单"}
        ]

        示例输出:
        [
          "我在Chrome浏览器搜索火锅推荐",
          "我打开美团浏览火锅店并下单了XX火锅"
        ]
        """
        if not vlm_outputs:
            return []

        # 过滤成功的分析结果
        successful_outputs = [o for o in vlm_outputs if o.get('status') == 'success']

        if not successful_outputs:
            return []

        # 构建LLM提示词
        prompt = self.build_llm_prompt(successful_outputs)

        try:
            # 调用LLM API
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2048
                },
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    message = result["choices"][0].get("message", {})
                    content = message.get("content", "")

                    # 尝试解析JSON格式的回答
                    try:
                        # 提取JSON数组
                        import re
                        json_match = re.search(r'\[.*\]', content, re.DOTALL)
                        if json_match:
                            json_str = json_match.group(0)
                            return json.loads(json_str)
                    except:
                        pass

                    # 如果无法解析JSON，返回原始文本
                    return [content]
            else:
                print(f"LLM API请求失败，状态码: {response.status_code}")
                return []

        except Exception as e:
            print(f"LLM汇总过程出错: {str(e)}")
            return []

    def build_llm_prompt(self, vlm_outputs: List[Dict[str, Any]]) -> str:
        """构建LLM汇总提示词"""
        # 构建应用操作序列
        app_sequence = []
        for output in vlm_outputs:
            app_name = output.get('app_name', '未知应用')
            analysis = output.get('analysis', {})
            actions = analysis.get('actions', [])
            summary = analysis.get('summary', '')

            app_info = {
                "app": app_name,
                "summary": summary,
                "actions": actions
            }
            app_sequence.append(app_info)

        prompt = f"""请将以下应用操作序列汇总为自然语言描述：

{json.dumps(app_sequence, ensure_ascii=False, indent=2)}

要求：
1. 每条描述以"我"开头
2. 合并逻辑相关的操作（如搜索+浏览+下单）
3. 保留关键信息（应用名、操作对象、重要参数）
4. 按时间顺序排列
5. 返回JSON数组格式，例如：["描述1", "描述2", ...]
6. 每条描述应该是完整的自然语言句子，长度50-200字

请直接返回JSON数组，不要包含其他文本。"""

        return prompt
