"""TaskAgent集成层 - 将各个Subagent集成到主Agent中"""

import uuid
from typing import Any, Optional
from openai import OpenAI

from task_framework.subagents import (
    MinimalAskAgent,
    PlanGenerationAgent,
    PreferenceUpdateAgent,
)
from task_framework.utils import ContextManager, PermissionManager
from task_framework.interfaces import (
    UserInputInterface,
    UserInteractionInterface,
    InteractionType,
)


class TaskAgentIntegration:
    """TaskAgent集成层 - 管理各个Subagent的协作"""

    def __init__(
        self,
        user_input: UserInputInterface,
        user_interaction: UserInteractionInterface,
        model_client: OpenAI,
        model_name: str = "mimo-v2-flash",
        language: str = "zh",
        permissions_config_path: str = "config/permissions.json",
        context_temp_dir: str = "temp/contexts",
    ):
        """
        初始化集成层。

        Args:
            user_input: 用户输入接口
            user_interaction: 用户交互接口
            model_client: OpenAI客户端
            model_name: 使用的模型名称
            language: 语言设置
            permissions_config_path: 权限配置路径
            context_temp_dir: Context临时目录
        """
        self.user_input = user_input
        self.user_interaction = user_interaction
        self.model_client = model_client
        self.model_name = model_name
        self.language = language

        # 初始化工具
        self.permission_manager = PermissionManager(permissions_config_path)
        self.context_manager = ContextManager(context_temp_dir)

        # 初始化各个Subagent
        self.minimal_ask_agent = MinimalAskAgent(
            user_input=user_input,
            user_interaction=user_interaction,
            model_client=model_client,
            model_name=model_name,
            language=language,
        )

        self.plan_agent = PlanGenerationAgent(
            user_input=user_input,
            user_interaction=user_interaction,
            model_client=model_client,
            model_name=model_name,
            language=language,
        )

        self.preference_agent = PreferenceUpdateAgent(
            user_interaction=user_interaction,
            model_client=model_client,
            model_name=model_name,
            language=language,
            context_manager=self.context_manager,
        )

    def normalize_and_ask(
        self,
        user_instruction: str,
        user_profile: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        第1步：指令标准化和追问。

        Args:
            user_instruction: 用户指令
            user_profile: 用户画像

        Returns:
            完整的任务信息
        """
        if user_profile is None:
            user_profile = {}

        self.user_interaction.show_message(
            "\n📋 第1步：分析任务并追问缺失信息...",
            InteractionType.INFO
        )

        task_info = self.minimal_ask_agent.analyze_and_ask(
            user_instruction=user_instruction,
            user_profile=user_profile,
            max_rounds=2
        )

        self.user_interaction.show_message(
            "✅ 任务分析完成",
            InteractionType.SUCCESS
        )

        return task_info

    def generate_and_preview_plan(
        self,
        task_info: dict[str, Any],
        user_profile: Optional[dict[str, Any]] = None,
    ) -> Optional[dict[str, Any]]:
        """
        第2步：生成计划并预览。

        Args:
            task_info: 任务信息
            user_profile: 用户画像

        Returns:
            最终确认的计划
        """
        if user_profile is None:
            user_profile = {}

        self.user_interaction.show_message(
            "\n📋 第2步：生成执行计划...",
            InteractionType.INFO
        )

        # 生成计划
        plan = self.plan_agent.generate_plan(
            task_info=task_info,
            user_profile=user_profile
        )

        if not plan:
            self.user_interaction.show_message(
                "❌ 计划生成失败",
                InteractionType.ERROR
            )
            return None

        self.user_interaction.show_message(
            "✅ 计划生成完成",
            InteractionType.SUCCESS
        )

        # 预览并确认
        self.user_interaction.show_message(
            "\n📋 第3步：预览计划...",
            InteractionType.INFO
        )

        final_plan = self.plan_agent.preview_and_confirm_plan(
            plan=plan,
            max_modifications=2
        )

        if not final_plan:
            self.user_interaction.show_message(
                "❌ 计划被拒绝",
                InteractionType.ERROR
            )
            return None

        self.user_interaction.show_message(
            "✅ 计划已确认",
            InteractionType.SUCCESS
        )

        return final_plan

    def create_task_context(self, task_id: Optional[str] = None) -> str:
        """
        创建任务Context。

        Args:
            task_id: 任务ID（可选）

        Returns:
            任务ID
        """
        if task_id is None:
            task_id = str(uuid.uuid4())

        context = self.context_manager.create_context(task_id)
        self.context_manager.save_context(context)

        return task_id

    def record_execution_choice(
        self,
        task_id: str,
        key: str,
        value: Any,
    ) -> bool:
        """
        记录执行过程中的用户选择。

        Args:
            task_id: 任务ID
            key: 选择键名
            value: 选择值

        Returns:
            是否记录成功
        """
        return self.context_manager.add_user_choice(task_id, key, value)

    def record_execution_observation(
        self,
        task_id: str,
        key: str,
        value: Any,
    ) -> bool:
        """
        记录执行过程中的观察。

        Args:
            task_id: 任务ID
            key: 观察键名
            value: 观察值

        Returns:
            是否记录成功
        """
        return self.context_manager.add_observation(task_id, key, value)

    def analyze_and_update_preferences(
        self,
        task_id: str,
        user_profile: Optional[dict[str, Any]] = None,
        execution_history: Optional[list[dict[str, Any]]] = None,
    ) -> Optional[dict[str, Any]]:
        """
        第4步：分析偏好并询问是否更新。

        Args:
            task_id: 任务ID
            user_profile: 用户画像
            execution_history: 执行历史

        Returns:
            偏好更新数据（如果用户同意）
        """
        if user_profile is None:
            user_profile = {}
        if execution_history is None:
            execution_history = []

        self.user_interaction.show_message(
            "\n📋 第4步：分析偏好并询问是否更新...",
            InteractionType.INFO
        )

        preference_update = self.preference_agent.analyze_and_update(
            task_id=task_id,
            user_profile=user_profile,
            execution_history=execution_history
        )

        if preference_update:
            self.user_interaction.show_message(
                "✅ 偏好更新建议已生成",
                InteractionType.SUCCESS
            )
        else:
            self.user_interaction.show_message(
                "⚠️ 无需更新偏好",
                InteractionType.INFO
            )

        return preference_update

    def cleanup_task_context(self, task_id: str) -> bool:
        """
        清理任务Context。

        Args:
            task_id: 任务ID

        Returns:
            是否清理成功
        """
        return self.context_manager.delete_context(task_id)

    def get_permission_mode(self, permission_key: str) -> str:
        """
        获取权限模式。

        Args:
            permission_key: 权限键名

        Returns:
            权限模式: "auto" | "confirm" | "forbidden"
        """
        return self.permission_manager.check_permission_mode(permission_key)

    def check_sensitive_operation(self, operation_type: str) -> bool:
        """
        检查敏感操作是否被允许。

        Args:
            operation_type: 操作类型（如 "auto_payment", "auto_delete"）

        Returns:
            是否允许自动执行
        """
        mode = self.get_permission_mode(operation_type)
        return mode == "auto"
