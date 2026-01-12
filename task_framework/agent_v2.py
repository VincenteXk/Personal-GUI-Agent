"""修改后的TaskAgent - 集成各个Subagent"""

import uuid
from typing import Any, Optional
from datetime import datetime

from .config import TaskAgentConfig
from .context import TaskContext, TaskInfo, TaskState
from .integration import TaskAgentIntegration
from .interfaces import (
    UserInputInterface,
    UserInteractionInterface,
    DeviceCapabilityInterface,
    ProfileManagerInterface,
    TaskExecutorInterface,
    InteractionType,
)
from .implementations.phone_task_executor import PhoneTaskExecutor
from .subagents import ProfileInitAgent
from openai import OpenAI


class TaskAgentV2:
    """
    改进的TaskAgent - 集成各个Subagent。

    流程：
    1. 指令标准化和追问 (MinimalAskAgent)
    2. 生成计划并预览 (PlanGenerationAgent)
    3. 执行任务 (AutoGLM PhoneAgent)
    4. 分析偏好并更新 (PreferenceUpdateAgent)
    """

    def __init__(
        self,
        user_input: UserInputInterface,
        user_interaction: UserInteractionInterface,
        device_capability: Optional[DeviceCapabilityInterface] = None,
        profile_manager: Optional[ProfileManagerInterface] = None,
        task_executors: Optional[list[TaskExecutorInterface]] = None,
        model_client: Optional[OpenAI] = None,
        config: Optional[TaskAgentConfig] = None,
    ):
        """初始化TaskAgentV2"""
        self.user_input = user_input
        self.user_interaction = user_interaction
        self.device_capability = device_capability
        self.profile_manager = profile_manager
        self.task_executors = task_executors or []
        self.config = config or TaskAgentConfig()

        # 初始化模型客户端
        if model_client is not None:
            self.model_client = model_client
        elif self.config.model_base_url and self.config.model_api_key:
            self.model_client = OpenAI(
                base_url=self.config.model_base_url,
                api_key=self.config.model_api_key,
            )
        else:
            raise ValueError("model_client is not set")

        # 初始化集成层
        self.integration = TaskAgentIntegration(
            user_input=user_input,
            user_interaction=user_interaction,
            model_client=self.model_client,
            model_name=self.config.model_name,
            language=self.config.language,
            permissions_config_path=self.config.permissions_config_path,
            context_temp_dir=self.config.context_temp_dir,
        )

        # 初始化PhoneTaskExecutor用于真实任务执行
        self.phone_executor = PhoneTaskExecutor()

        # 初始化上下文
        self.context: Optional[TaskContext] = None
        self._is_onboarded = not self.config.enable_onboarding

    def run(self) -> None:
        """运行Agent主循环"""
        # 首次引导
        if not self._is_onboarded:
            self._run_onboarding()
            self._is_onboarded = True

        # 主循环
        self.user_interaction.show_message(
            "欢迎使用个性化GUI助手！输入 'exit' 或 'quit' 退出。",
            InteractionType.INFO
        )

        while True:
            try:
                # 接收用户输入
                task_input = self.user_input.get_input("\n💬 请输入任务描述")

                if task_input.lower() in ["exit", "quit", "退出"]:
                    self.user_interaction.show_message("再见！", InteractionType.INFO)
                    break

                if not task_input.strip():
                    continue

                # 执行任务
                result_message = self._execute_task_flow(task_input)

                # 显示结果
                if result_message:
                    self.user_interaction.show_message(
                        f"\n✅ {result_message}",
                        InteractionType.SUCCESS
                    )

            except KeyboardInterrupt:
                self.user_interaction.show_message(
                    "\n任务被中断",
                    InteractionType.WARNING
                )
                break
            except Exception as e:
                self.user_interaction.show_message(
                    f"发生错误: {e}",
                    InteractionType.ERROR
                )
                if self.config.verbose:
                    import traceback
                    traceback.print_exc()

    def _execute_task_flow(self, user_instruction: str) -> str:
        """
        执行完整的任务流程。

        Args:
            user_instruction: 用户指令

        Returns:
            任务完成消息
        """
        # 创建任务Context
        task_id = self.integration.create_task_context()

        try:
            # 获取用户画像
            user_profile = {}
            if self.profile_manager:
                profile = self.profile_manager.get_profile()
                user_profile = {
                    "language_style": profile.language_style,
                    "common_apps": profile.common_apps,
                    "default_mode": profile.default_mode,
                    "preferences": profile.preferences,
                }

            # 第1步：指令标准化和追问
            if self.config.enable_minimal_ask:
                task_info = self.integration.normalize_and_ask(
                    user_instruction=user_instruction,
                    user_profile=user_profile
                )
            else:
                task_info = {
                    "original_instruction": user_instruction,
                    "key_info": {},
                    "constraints": [],
                }

            # 第2步：生成计划并预览
            if self.config.enable_plan_preview:
                plan = self.integration.generate_and_preview_plan(
                    task_info=task_info,
                    user_profile=user_profile
                )

                if not plan:
                    return "计划被拒绝，任务取消"

                # 记录计划信息
                self.integration.record_execution_observation(
                    task_id,
                    "plan",
                    plan
                )
            else:
                plan = None

            # 第3步：执行任务
            self.user_interaction.show_message(
                "\n📋 第3步：执行任务...",
                InteractionType.INFO
            )

            # 调用PhoneTaskExecutor执行真实任务
            execution_result = self._execute_with_phone_agent(plan, task_id)

            if not execution_result:
                return "任务执行失败"

            self.user_interaction.show_message(
                "✅ 任务执行完成",
                InteractionType.SUCCESS
            )

            # 第4步：分析偏好并更新
            if self.config.enable_preference_update and self.profile_manager:
                preference_update = self.integration.analyze_and_update_preferences(
                    task_id=task_id,
                    user_profile=user_profile,
                    execution_history=[]
                )

                if preference_update:
                    self.integration.preference_agent.apply_preference_update(
                        preference_update=preference_update,
                        profile_manager=self.profile_manager
                    )

            return "任务流程完成"

        finally:
            # 清理Context
            if self.config.cleanup_context_after_task:
                self.integration.cleanup_task_context(task_id)

    def _execute_with_phone_agent(self, plan: Optional[dict[str, Any]], task_id: str) -> bool:
        """
        使用PhoneAgent执行真实任务。

        Args:
            plan: 执行计划
            task_id: 任务ID

        Returns:
            是否执行成功
        """
        if plan is None:
            return True

        # 从plan中提取指令
        # 优先级：instruction > 组合步骤 > task_description
        instruction = plan.get("instruction")

        if not instruction:
            # 尝试从steps组合指令
            app = plan.get("app", "")
            steps = plan.get("steps", [])

            if app and steps:
                # 构建指令：打开APP并执行步骤
                instruction = f"打开{app}应用，然后执行以下步骤：" + "；".join(steps[:3])
            elif plan.get("task_type"):
                # 最后尝试用task_type作为指令
                instruction = plan.get("task_type", "")

        if not instruction:
            self.user_interaction.show_message(
                "⚠️ 计划中缺少执行指令",
                InteractionType.WARNING
            )
            return False

        try:
            # 调用PhoneTaskExecutor执行任务
            result = self.phone_executor.execute_task(
                task_type="phone_automation",
                task_params={"instruction": instruction},
                context={}
            )

            # 记录执行结果
            self.integration.record_execution_observation(
                task_id,
                "execution_status",
                "completed" if result.success else "failed"
            )

            self.integration.record_execution_observation(
                task_id,
                "execution_result",
                result.message
            )

            if result.success:
                self.user_interaction.show_message(
                    f"✅ 任务执行成功: {result.message}",
                    InteractionType.SUCCESS
                )
            else:
                self.user_interaction.show_message(
                    f"❌ 任务执行失败: {result.message}",
                    InteractionType.ERROR
                )

            return result.success

        except Exception as e:
            self.user_interaction.show_message(
                f"❌ 执行任务时出错: {str(e)}",
                InteractionType.ERROR
            )

            self.integration.record_execution_observation(
                task_id,
                "execution_error",
                str(e)
            )

            if self.config.verbose:
                import traceback
                traceback.print_exc()

            return False

    def _run_onboarding(self) -> None:
        """运行首次引导流程"""
        self.user_interaction.show_message(
            "首次使用引导",
            InteractionType.INFO
        )

        self.user_interaction.show_message(
            """
本系统可以帮助您自动完成各种任务：
- 任务规划和分解
- 智能调度和执行
- 风险控制和确认
- 敏感操作需要您的确认
            """,
            InteractionType.INFO
        )

        # 检查设备
        if self.device_capability:
            devices = self.device_capability.list_available_devices()
            if devices:
                self.user_interaction.show_message(
                    f"检测到 {len(devices)} 个设备",
                    InteractionType.SUCCESS
                )
            else:
                self.user_interaction.show_message(
                    "未检测到设备，部分功能可能不可用",
                    InteractionType.WARNING
                )

        # 初始化用户画像
        if self.profile_manager:
            self.user_interaction.show_message(
                "开始创建个人画像，这将帮助我更好地为您服务...",
                InteractionType.INFO
            )
            self._init_user_profile()
            
            # 场景偏好已集成到画像初始化中


        self.user_interaction.show_message(
            "引导完成！现在可以开始使用了。",
            InteractionType.SUCCESS
        )

    def _init_user_profile(self) -> None:
        """初始化用户画像"""
        profile_init_agent = ProfileInitAgent(
            user_input=self.user_input,
            user_interaction=self.user_interaction,
            model_client=self.model_client,
            model_name=self.config.model_name,
            language=self.config.language,
        )

        profile_data = profile_init_agent.run()

        if profile_data and self.profile_manager:
            from .interfaces import UserProfile
            profile = UserProfile(
                language_style=profile_data.get("language_style", "casual"),
                common_apps=profile_data.get("common_apps", []),
                default_mode=profile_data.get("default_mode", "balanced"),
                preferences=profile_data.get("preferences", {}),
            )
            self.profile_manager.update_profile(profile)
            self.user_interaction.show_message(
                "用户画像已保存",
                InteractionType.SUCCESS
            )

