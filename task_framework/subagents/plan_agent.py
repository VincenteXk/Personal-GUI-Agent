"""PlanGenerationAgent - 计划生成Agent。"""

import json
from typing import Any, Optional
from openai import OpenAI

from task_framework.prompts.plan_prompts import (
    get_plan_generation_system_prompt,
    get_plan_modification_system_prompt,
)
from task_framework.interfaces import UserInputInterface, UserInteractionInterface, InteractionType


class PlanGenerationAgent:
    """计划生成Agent。

    生成任务执行计划，支持用户修改。
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
        初始化PlanGenerationAgent。

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
        self.generation_prompt = get_plan_generation_system_prompt(language)
        self.modification_prompt = get_plan_modification_system_prompt(language)

    def generate_plan(
        self,
        task_info: dict[str, Any],
        user_profile: Optional[dict[str, Any]] = None,
    ) -> Optional[dict[str, Any]]:
        """
        生成任务执行计划。

        Args:
            task_info: 任务信息
            user_profile: 用户画像

        Returns:
            执行计划
        """
        if user_profile is None:
            user_profile = {}

        # 构建请求
        request_data = {
            "task_info": task_info,
            "user_profile": user_profile,
        }

        try:
            response = self.model_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": self.generation_prompt},
                    {
                        "role": "user",
                        "content": json.dumps(request_data, ensure_ascii=False),
                    },
                ],
                model=self.model_name,
                max_completion_tokens=1024,
                temperature=0.3,
            )

            response_text = response.choices[0].message.content

            # 解析响应
            try:
                response_data = json.loads(response_text)
            except json.JSONDecodeError:
                import re

                json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if json_match:
                    response_data = json.loads(json_match.group())
                else:
                    self.user_interaction.show_message(
                        "计划生成失败", InteractionType.ERROR
                    )
                    return None

            return response_data.get("plan")

        except Exception as e:
            self.user_interaction.show_message(
                f"生成计划出错: {e}", InteractionType.ERROR
            )
            return None

    def preview_and_confirm_plan(
        self,
        plan: dict[str, Any],
        max_modifications: int = 3,
    ) -> Optional[dict[str, Any]]:
        """
        预览计划并允许用户修改。

        Args:
            plan: 执行计划
            max_modifications: 最大修改次数

        Returns:
            最终确认的计划
        """
        current_plan = plan

        for mod_round in range(max_modifications + 1):
            # 显示计划
            self._display_plan(current_plan)

            if mod_round == 0:
                # 第一次显示，询问是否满意
                response = self.user_interaction.get_confirmation(
                    "计划是否满意？", default=True
                )
                if response:
                    return current_plan
            else:
                # 后续轮次，询问是否继续修改
                response = self.user_interaction.get_confirmation(
                    "是否继续修改？", default=False
                )
                if not response:
                    return current_plan

            # 获取用户修改意见
            feedback = self.user_input.get_input("请描述你的修改需求")

            if feedback.lower() in ["skip", "跳过", "不改"]:
                return current_plan

            # 修改计划
            modified_plan = self._modify_plan(current_plan, feedback)
            if modified_plan:
                current_plan = modified_plan
            else:
                self.user_interaction.show_message(
                    "修改失败，保持原计划", InteractionType.WARNING
                )

        self.user_interaction.show_message(
            "已达到最大修改次数，使用当前计划", InteractionType.INFO
        )
        return current_plan

    def _display_plan(self, plan: dict[str, Any]) -> None:
        """显示计划。"""
        self.user_interaction.show_message("\n📋 执行计划预览", InteractionType.INFO)
        self.user_interaction.show_message(
            f"任务类型: {plan.get('task_type', 'N/A')}", InteractionType.INFO
        )
        self.user_interaction.show_message(
            f"使用应用: {plan.get('app', 'N/A')}", InteractionType.INFO
        )
        self.user_interaction.show_message(
            f"风险等级: {plan.get('risk_level', 'N/A')}", InteractionType.INFO
        )

        self.user_interaction.show_message("\n执行步骤:", InteractionType.INFO)
        for step in plan.get("steps", []):
            self.user_interaction.show_message(f"  {step}", InteractionType.INFO)

        if plan.get("alternative_mode"):
            self.user_interaction.show_message(
                f"\n备选方案: {plan.get('alternative_mode')}", InteractionType.INFO
            )

    def _modify_plan(self, current_plan: dict[str, Any], feedback: str) -> Optional[dict[str, Any]]:
        """修改计划。"""
        request_data = {
            "current_plan": current_plan,
            "user_feedback": feedback,
        }

        try:
            response = self.model_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": self.modification_prompt},
                    {
                        "role": "user",
                        "content": json.dumps(request_data, ensure_ascii=False),
                    },
                ],
                model=self.model_name,
                max_completion_tokens=1024,
                temperature=0.3,
            )

            response_text = response.choices[0].message.content

            # 解析响应
            try:
                response_data = json.loads(response_text)
            except json.JSONDecodeError:
                import re

                json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if json_match:
                    response_data = json.loads(json_match.group())
                else:
                    return None

            modified_plan = response_data.get("modified_plan")
            changes = response_data.get("changes", "")

            if changes:
                self.user_interaction.show_message(
                    f"✓ 修改: {changes}", InteractionType.SUCCESS
                )

            return modified_plan

        except Exception as e:
            self.user_interaction.show_message(
                f"修改计划出错: {e}", InteractionType.ERROR
            )
            return None
