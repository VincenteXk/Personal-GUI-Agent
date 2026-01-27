"""MinimalAskAgent - 最小追问Agent。"""

import json
import requests
from typing import Any, Optional
from openai import OpenAI

from task_framework.prompts.minimal_ask_prompts import get_minimal_ask_system_prompt
from task_framework.interfaces import UserInputInterface, UserInteractionInterface, InteractionType


class MinimalAskAgent:
    """最小追问Agent。

    分析任务缺失信息，生成最小化的追问。
    """

    def __init__(
        self,
        user_input: UserInputInterface,
        user_interaction: UserInteractionInterface,
        model_client: OpenAI,
        model_name: str = "mimo-v2-flash",
        language: str = "zh",
        graphrag_url: str = "http://localhost:8000",
    ):
        """
        初始化MinimalAskAgent。

        Args:
            user_input: 用户输入接口
            user_interaction: 用户交互接口
            model_client: OpenAI客户端
            model_name: 使用的模型名称
            language: 语言设置
            graphrag_url: GraphRAG 后端服务地址
        """
        self.user_input = user_input
        self.user_interaction = user_interaction
        self.model_client = model_client
        self.model_name = model_name
        self.language = language
        self.graphrag_url = graphrag_url
        self.system_prompt = get_minimal_ask_system_prompt(language)

    def analyze_and_ask(
        self,
        user_instruction: str,
        user_profile: Optional[dict[str, Any]] = None,
        context: Optional[dict[str, Any]] = None,
        max_rounds: int = 3,
    ) -> dict[str, Any]:
        """
        分析任务并进行追问。

        Args:
            user_instruction: 用户原始指令
            user_profile: 用户画像
            context: 当前上下文
            max_rounds: 最大追问轮数

        Returns:
            完整的任务信息
        """
        if user_profile is None:
            user_profile = {}
        if context is None:
            context = {}

        task_info = {
            "original_instruction": user_instruction,
            "key_info": {},
            "constraints": [],
        }

        # 查询 GraphRAG 获取相关上下文
        graphrag_context = self._query_graphrag_context(user_instruction)

        for round_num in range(max_rounds):
            # 构建分析请求
            analysis_request = {
                "user_instruction": user_instruction,
                "user_profile": user_profile,
                "context": context,
                "graphrag_context": graphrag_context,  # 添加 GraphRAG 上下文
                "current_task_info": task_info,
            }

            # 请求模型分析
            try:
                response = self.model_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {
                            "role": "user",
                            "content": json.dumps(analysis_request, ensure_ascii=False),
                        },
                    ],
                    model=self.model_name,
                    max_completion_tokens=512,
                    temperature=0.3,
                )

                response_text = response.choices[0].message.content

                # 解析响应
                try:
                    response_data = json.loads(response_text)
                except json.JSONDecodeError:
                    # 尝试提取JSON
                    import re

                    json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                    if json_match:
                        response_data = json.loads(json_match.group())
                    else:
                        self.user_interaction.show_message(
                            "分析失败，请重试", InteractionType.ERROR
                        )
                        continue

                # 检查是否需要追问
                if not response_data.get("needs_clarification", False):
                    # 信息充足，返回任务信息
                    task_info.update(response_data.get("task_info", {}))
                    return task_info

                # 需要追问
                question_data = response_data
                user_answer = self._ask_question(question_data)

                # 更新任务信息
                field = question_data.get("field", "")
                if field:
                    task_info["key_info"][field] = user_answer

            except Exception as e:
                self.user_interaction.show_message(
                    f"分析出错: {e}", InteractionType.ERROR
                )
                continue

        # 达到最大轮数，返回当前任务信息
        return task_info

    def _ask_question(self, question_data: dict[str, Any]) -> str:
        """
        向用户提问。

        Args:
            question_data: 问题数据

        Returns:
            用户的回答
        """
        question = question_data.get("question", "")
        question_type = question_data.get("question_type", "open_ended")
        options = question_data.get("options", [])
        default_option = question_data.get("default_option")

        # 显示问题（使用 QUESTION 类型触发 TTS）
        self.user_interaction.show_message(question, InteractionType.QUESTION)

        if question_type == "single_choice" and options:
            # 单选题
            for i, option in enumerate(options, 1):
                prefix = "✓ " if option == default_option else "  "
                self.user_interaction.show_message(
                    f"{prefix}{i}. {option}", InteractionType.INFO
                )

            # 获取用户选择
            while True:
                try:
                    choice_input = self.user_input.get_input("请选择 (输入数字或选项名称)")

                    # 尝试按数字解析
                    if choice_input.isdigit():
                        idx = int(choice_input) - 1
                        if 0 <= idx < len(options):
                            return options[idx]

                    # 尝试按选项名称精确匹配
                    if choice_input in options:
                        return choice_input

                    # 使用 LLM 进行语义匹配
                    matched = self._match_option_with_llm(choice_input, options)
                    if matched:
                        return matched

                    self.user_interaction.show_message(
                        "无效的选择，请重试", InteractionType.WARNING
                    )
                except Exception:
                    self.user_interaction.show_message(
                        "输入错误，请重试", InteractionType.WARNING
                    )

        elif question_type == "multi_choice" and options:
            # 多选题
            for i, option in enumerate(options, 1):
                self.user_interaction.show_message(f"{i}. {option}", InteractionType.INFO)

            choice_input = self.user_input.get_input("请选择 (用逗号分隔多个选项)")
            return choice_input

        else:
            # 开放式问题
            return self.user_input.get_input("请输入")

    def _query_graphrag_context(self, user_instruction: str) -> list[dict[str, Any]]:
        """
        查询 GraphRAG 获取与用户指令相关的上下文信息。

        使用"我"实体的关系来获取历史记录，而非关键词搜索。

        Args:
            user_instruction: 用户指令

        Returns:
            相关的上下文信息列表
        """
        try:
            # 查询"我"实体的详情，包含所有关系
            url = f"{self.graphrag_url}/api/entities/我"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            entity_data = response.json()

            # 提取相关的关系信息作为上下文
            context_items = []
            relationships = entity_data.get("relationships", [])
            
            for rel in relationships:
                context_items.append({
                    "type": "relationship",
                    "source": rel.get("source", ""),
                    "target": rel.get("target", ""),
                    "description": rel.get("description", ""),
                })

            # 限制返回数量
            return context_items[:15]

        except Exception as e:
            # 查询失败不影响主流程，静默返回空列表
            print(f"[GraphRAG] 上下文查询失败: {e}")
            return []

    def _match_option_with_llm(self, user_input: str, options: list[str]) -> Optional[str]:
        """
        使用 LLM 理解用户输入并匹配到最合适的选项。

        Args:
            user_input: 用户输入（可能是语音识别结果，包含噪声）
            options: 可选项列表

        Returns:
            匹配到的选项，如果无法匹配返回 None
        """
        try:
            prompt = f"""用户输入: "{user_input}"
可选项: {options}

请判断用户想选择哪个选项。
规则：
1. 如果用户输入包含或接近某个选项，返回该选项
2. 如果用户说"第X个"或数字，返回对应选项
3. 如果完全无法判断，返回 NONE

只返回选项内容或NONE，不要其他解释。"""

            response = self.model_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model_name,
                max_completion_tokens=50,
                temperature=0.1,
            )

            matched = response.choices[0].message.content.strip()

            # 验证返回的是有效选项
            if matched in options:
                return matched
            if matched == "NONE":
                return None

            # 尝试模糊匹配返回结果
            for option in options:
                if option in matched or matched in option:
                    return option

            return None

        except Exception as e:
            print(f"[LLM] 选项匹配失败: {e}")
            return None

