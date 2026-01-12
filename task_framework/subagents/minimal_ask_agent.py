"""MinimalAskAgent - 最小追问Agent。"""

import json
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
    ):
        """
        初始化MinimalAskAgent。

        Args:
            user_input: 用户输入接口
            user_interaction: 用户交互接口
            model_client: OpenAI客户端
            model_name: 使用的模型名称
            language: 语言设置
        """
        self.user_input = user_input
        self.user_interaction = user_interaction
        self.model_client = model_client
        self.model_name = model_name
        self.language = language
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

        for round_num in range(max_rounds):
            # 构建分析请求
            analysis_request = {
                "user_instruction": user_instruction,
                "user_profile": user_profile,
                "context": context,
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

        # 显示问题
        self.user_interaction.show_message(question, InteractionType.INFO)

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

                    # 尝试按选项名称匹配
                    if choice_input in options:
                        return choice_input

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
