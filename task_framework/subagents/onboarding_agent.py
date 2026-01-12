"""OnboardingAgent - 首次使用引导Agent。"""

import json
from typing import Any, Optional
from openai import OpenAI

from task_framework.prompts.onboarding_prompts import get_onboarding_system_prompt
from task_framework.utils import PermissionManager, PermissionConfig
from task_framework.interfaces import UserInteractionInterface, UserInputInterface, InteractionType


class OnboardingAgent:
    """首次使用引导Agent。

    负责引导用户完成权限设置和初始画像创建。
    """

    def __init__(
        self,
        user_interaction: UserInteractionInterface,
        user_input: UserInputInterface,
        model_client: OpenAI,
        model_name: str = "mimo-v2-flash",
        language: str = "zh",
        permissions_config_path: str = "config/permissions.json",
    ):
        """
        初始化OnboardingAgent。

        Args:
            user_interaction: 用户交互接口
            user_input: 用户输入接口
            model_client: OpenAI客户端
            model_name: 使用的模型名称
            language: 语言设置
            permissions_config_path: 权限配置文件路径
        """
        self.user_interaction = user_interaction
        self.user_input = user_input
        self.model_client = model_client
        self.model_name = model_name
        self.language = language
        self.permissions_config_path = permissions_config_path
        self.system_prompt = get_onboarding_system_prompt(language)

    def run(self) -> Optional[PermissionConfig]:
        """
        运行引导流程。

        Returns:
            完成的权限配置，如果用户取消则返回None
        """
        self.user_interaction.show_message(
            "欢迎使用个性化GUI助手！现在开始首次设置...", InteractionType.INFO
        )

        conversation_history = []
        max_turns = 20

        for turn in range(max_turns):
            # 构建消息
            if turn == 0:
                # 第一轮：开始引导
                user_message = "请开始引导我完成设置。"
            else:
                # 后续轮次：用户的选择
                user_message = self._get_user_input()
                if user_message.lower() in ["exit", "quit", "取消"]:
                    self.user_interaction.show_message(
                        "设置已取消", InteractionType.WARNING
                    )
                    return None

            conversation_history.append({"role": "user", "content": user_message})

            # 请求模型
            try:
                response = self.model_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        *conversation_history,
                    ],
                    model=self.model_name,
                    max_completion_tokens=1024,
                    temperature=0.3,
                )

                assistant_message = response.choices[0].message.content
                conversation_history.append(
                    {"role": "assistant", "content": assistant_message}
                )

                # 解析响应
                try:
                    response_data = json.loads(assistant_message)
                except json.JSONDecodeError:
                    # 尝试提取JSON
                    import re

                    json_match = re.search(r"\{.*\}", assistant_message, re.DOTALL)
                    if json_match:
                        response_data = json.loads(json_match.group())
                    else:
                        self.user_interaction.show_message(
                            "解析响应失败，请重试", InteractionType.ERROR
                        )
                        continue

                # 处理响应
                if response_data.get("type") == "question":
                    self._handle_question(response_data)
                elif response_data.get("type") == "completed":
                    return self._handle_completion(response_data)

            except Exception as e:
                self.user_interaction.show_message(
                    f"发生错误: {e}", InteractionType.ERROR
                )
                continue

        self.user_interaction.show_message(
            "设置超时，请稍后重试", InteractionType.WARNING
        )
        return None

    def _handle_question(self, question_data: dict[str, Any]) -> None:
        """处理问题。"""
        question = question_data.get("question", "")
        options = question_data.get("options", [])
        recommended = question_data.get("recommended")

        # 显示问题
        self.user_interaction.show_message(question, InteractionType.INFO)

        # 显示选项
        if options:
            for i, option in enumerate(options, 1):
                prefix = "✓ " if option == recommended else "  "
                self.user_interaction.show_message(f"{prefix}{i}. {option}", InteractionType.INFO)

    def _handle_completion(self, completion_data: dict[str, Any]) -> Optional[PermissionConfig]:
        """处理完成。"""
        try:
            # 构建权限配置
            permissions = completion_data.get("permissions", {})
            meta_preferences = completion_data.get("meta_preferences", {})

            config = PermissionConfig(
                user_id="default_user",
                permissions=permissions,
                meta_preferences=meta_preferences,
            )

            # 保存配置
            manager = PermissionManager(self.permissions_config_path)
            manager.save(config)

            self.user_interaction.show_message(
                "✅ 设置完成！配置已保存。", InteractionType.SUCCESS
            )

            return config

        except Exception as e:
            self.user_interaction.show_message(
                f"保存配置失败: {e}", InteractionType.ERROR
            )
            return None

    def _get_user_input(self) -> str:
        """获取用户输入。"""
        return self.user_input.get_input("你的选择: ")
