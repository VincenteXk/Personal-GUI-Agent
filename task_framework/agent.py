"""任务调度Agent - 采用"感知-思考-行动"循环架构。

参照 phone_agent/agent.py 的设计，使用大模型驱动的决策循环，
而不是预定义的工作流节点。

专注于：
- 用户交互和任务理解
- 系统调度和任务管理
- 动态路径规划
- 状态转移决策
"""

import json
import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from .config import TaskAgentConfig
from .context import TaskContext, TaskInfo, TaskState
from .actions import SchedulerActionHandler, parse_scheduler_action
from .prompts import get_scheduler_system_prompt, get_messages
from .interfaces import (
    UserInputInterface,
    UserInteractionInterface,
    DeviceCapabilityInterface,
    ProfileManagerInterface,
    TaskExecutorInterface,
    InteractionType,
)

# 如果有model client，可以导入
# from phone_agent.model import ModelClient, ModelConfig


@dataclass
class StepResult:
    """单步执行结果。"""

    success: bool
    finished: bool
    action: Optional[dict[str, Any]]
    thinking: str
    message: Optional[str] = None
    next_state: Optional[TaskState] = None


class TaskAgent:
    """
    任务调度Agent - 采用"感知-思考-行动"循环。

    与 PhoneAgent 的区别：
    - PhoneAgent: 感知屏幕 -> 思考 -> 设备操作
    - TaskAgent: 感知任务状态 -> 思考 -> 调度操作

    TaskAgent 处理的是更高层次的任务调度：
    - 用户交互（询问、确认）
    - 任务分析和规划
    - 调度底层执行器
    - 风险控制和决策
    - 动态路径调整

    Args:
        user_input: 用户输入接口
        user_interaction: 用户交互接口
        device_capability: 设备能力接口（可选）
        profile_manager: 画像管理接口（可选）
        task_executors: 任务执行器列表
        model_client: 大模型客户端（可选，如果None则使用简化决策）
        config: Agent配置

    Example:
        >>> from task_framework import TaskAgent, TaskAgentConfig
        >>> from task_framework.implementations import TerminalUserInput, TerminalUserInteraction
        >>>
        >>> config = TaskAgentConfig(verbose=True)
        >>> agent = TaskAgent(
        ...     user_input=TerminalUserInput(),
        ...     user_interaction=TerminalUserInteraction(),
        ...     config=config
        ... )
        >>> agent.run()
    """

    def __init__(
        self,
        user_input: UserInputInterface,
        user_interaction: UserInteractionInterface,
        device_capability: Optional[DeviceCapabilityInterface] = None,
        profile_manager: Optional[ProfileManagerInterface] = None,
        task_executors: Optional[list[TaskExecutorInterface]] = None,
        model_client: Optional[Any] = None,  # ModelClient
        config: Optional[TaskAgentConfig] = None,
    ):
        self.user_input = user_input
        self.user_interaction = user_interaction
        self.device_capability = device_capability
        self.profile_manager = profile_manager
        self.task_executors = task_executors or []
        self.model_client = model_client
        self.config = config or TaskAgentConfig()

        # 初始化上下文
        self.context: Optional[TaskContext] = None

        # 初始化操作处理器
        self.action_handler: Optional[SchedulerActionHandler] = None

        # 引导状态
        self._is_onboarded = not self.config.enable_onboarding

        # 获取系统提示词
        if self.config.system_prompt:
            self.system_prompt = self.config.system_prompt
        else:
            self.system_prompt = get_scheduler_system_prompt(self.config.language)

    def run(self) -> None:
        """运行Agent主循环。"""
        # 首次引导
        if not self._is_onboarded:
            self._run_onboarding()
            self._is_onboarded = True

        # 主循环
        self.user_interaction.show_message(
            "欢迎使用任务调度助手！输入 'exit' 或 'quit' 退出。", InteractionType.INFO
        )

        while True:
            try:
                # 重置上下文
                self.context = TaskContext(state=TaskState.IDLE)
                self.context.task_start_time = datetime.now()

                # 初始化操作处理器
                self.action_handler = SchedulerActionHandler(
                    user_input=self.user_input,
                    user_interaction=self.user_interaction,
                    task_executors=self.task_executors,
                    context=self.context,
                )

                # 接收用户输入
                task_input = self._receive_user_input()

                if task_input.lower() in ["exit", "quit", "退出"]:
                    self.user_interaction.show_message("再见！", InteractionType.INFO)
                    break

                if not task_input.strip():
                    continue

                # 执行任务
                result_message = self._execute_task(task_input)

                # 显示结果
                if result_message:
                    self.user_interaction.show_message(
                        f"\n✅ {result_message}", InteractionType.SUCCESS
                    )

            except KeyboardInterrupt:
                self.user_interaction.show_message(
                    "\n任务被中断", InteractionType.WARNING
                )
                break
            except Exception as e:
                self.user_interaction.show_message(
                    f"发生错误: {e}", InteractionType.ERROR
                )
                if self.config.verbose:
                    traceback.print_exc()

    def _execute_task(self, task_input: str) -> str:
        """
        执行完整的任务流程 - 使用感知-思考-行动循环。

        Args:
            task_input: 用户输入的任务描述

        Returns:
            任务完成消息
        """
        # 初始化任务信息
        self.context.task_info = TaskInfo(original_input=task_input)
        self.context.state = TaskState.RECEIVING_INPUT

        if self.config.verbose:
            self.user_interaction.show_message(
                f"\n📝 收到任务: {task_input}", InteractionType.INFO
            )

        # 第一步：带任务描述
        result = self._execute_step(user_prompt=task_input, is_first=True)

        if result.finished:
            return result.message or "任务完成"

        # 循环执行直到完成或达到最大步骤
        while self.context.current_step < self.config.max_steps:
            result = self._execute_step(is_first=False)

            if result.finished:
                return result.message or "任务完成"

        return f"达到最大步骤数 ({self.config.max_steps})，任务未完成"

    def _execute_step(
        self, user_prompt: Optional[str] = None, is_first: bool = False
    ) -> StepResult:
        """
        执行单步"感知-思考-行动"循环。

        感知: 收集当前任务状态、执行历史、交互历史
        思考: 大模型分析当前状态，决定下一步操作
        行动: 执行调度操作（用户交互、任务委托、状态更新等）

        Args:
            user_prompt: 用户输入（仅第一步需要）
            is_first: 是否是第一步

        Returns:
            StepResult 执行结果
        """
        self.context.next_step()

        # === 感知阶段 ===
        # 收集当前状态信息
        perception = self._perceive_current_state()

        # === 思考阶段 ===
        # 构建消息上下文
        if is_first:
            # 添加系统提示词
            self.context.add_conversation_message("system", self.system_prompt)

            # 添加用户任务描述 + 当前状态
            user_message = f"{user_prompt}\n\n{perception}"
            self.context.add_conversation_message("user", user_message)
        else:
            # 添加当前状态感知
            self.context.add_conversation_message("user", perception)

        # 请求大模型决策
        try:
            msgs = get_messages(self.config.language)

            if self.config.verbose:
                print("\n" + "=" * 50)
                print(f"💭 {msgs['thinking']} (步骤 {self.context.current_step}):")
                print("-" * 50)

            response = self._request_model_decision()

            if self.config.verbose:
                print(f"\n思考: {response['thinking']}")
                print("-" * 50)
                print(f"🎯 {msgs['action']}:")
                print(response["action"])
                print("=" * 50 + "\n")

        except Exception as e:
            if self.config.verbose:
                traceback.print_exc()
            return StepResult(
                success=False,
                finished=True,
                action=None,
                thinking="",
                message=f"模型决策失败: {e}",
            )

        # 解析操作
        try:
            action = parse_scheduler_action(response["action"])
        except ValueError as e:
            if self.config.verbose:
                print(f"⚠️ 解析操作失败: {e}")
            # 尝试作为完成消息处理
            action = {"_metadata": "finish", "message": response["action"]}

        # 添加助手响应到上下文
        self.context.add_conversation_message(
            "assistant",
            f"<think>{response['thinking']}</think><answer>{response['action']}</answer>",
        )

        # === 行动阶段 ===
        # 执行操作
        try:
            action_result = self.action_handler.execute(action)
        except Exception as e:
            if self.config.verbose:
                traceback.print_exc()
            action_result = self.action_handler.execute(
                {"_metadata": "finish", "message": f"操作执行错误: {e}"}
            )

        # 更新状态
        if action_result.next_state:
            self.context.state = action_result.next_state

        # 检查是否完成
        finished = (
            action.get("_metadata") == "finish"
            or action_result.should_finish
            or self.context.state == TaskState.COMPLETED
        )

        if finished and self.config.verbose:
            msgs = get_messages(self.config.language)
            print("\n" + "🎉 " + "=" * 48)
            print(f"✅ {msgs['task_completed']}: {action_result.message}")
            print("=" * 50 + "\n")

        return StepResult(
            success=action_result.success,
            finished=finished,
            action=action,
            thinking=response["thinking"],
            message=action_result.message,
            next_state=action_result.next_state,
        )

    def _perceive_current_state(self) -> str:
        """
        感知当前任务状态。

        收集：
        - 当前状态
        - 任务信息
        - 执行历史
        - 交互历史
        - 其他上下文信息

        Returns:
            格式化的状态信息字符串
        """
        context_summary = self.context.get_context_summary()

        perception = f"""** 当前状态感知 **

状态: {context_summary['current_state']}
步骤: {context_summary['current_step']}
重试次数: {context_summary['retry_count']}/{self.context.max_retries}

任务信息:
- 原始输入: {context_summary['task_info']['original_input'] if context_summary['task_info'] else '无'}
- 任务类型: {context_summary['task_info']['task_type'] if context_summary['task_info'] else '未确定'}
- 关键信息: {json.dumps(context_summary['task_info']['key_info'], ensure_ascii=False) if context_summary['task_info'] else '{}'}

最近执行历史:
{context_summary['recent_execution']}

上次操作结果: {context_summary['last_action_result'] or '无'}
"""

        return perception

    def _request_model_decision(self) -> dict[str, str]:
        """
        请求大模型做决策。

        Returns:
            包含 'thinking' 和 'action' 的字典
        """
        if self.model_client is None:
            # 如果没有模型客户端，使用简化的决策逻辑
            return self._fallback_decision()

        # 使用大模型进行决策
        response = self.model_client.request(self.context.conversation_history)

        # 解析响应（假设返回的response有thinking和action属性）
        # 这里需要根据实际的ModelClient接口调整
        if hasattr(response, "thinking") and hasattr(response, "action"):
            return {"thinking": response.thinking, "action": response.action}
        else:
            # 尝试解析字符串响应
            return self._parse_model_response(str(response))

    def _parse_model_response(self, response_text: str) -> dict[str, str]:
        """解析模型响应文本。"""
        import re

        # 尝试提取 <think>...</think> 和 <answer>...</answer>
        think_match = re.search(r"<think>(.*?)</think>", response_text, re.DOTALL)
        answer_match = re.search(r"<answer>(.*?)</answer>", response_text, re.DOTALL)

        thinking = think_match.group(1).strip() if think_match else ""
        action = answer_match.group(1).strip() if answer_match else response_text

        return {"thinking": thinking, "action": action}

    def _fallback_decision(self) -> dict[str, str]:
        """
        简化的决策逻辑（当没有大模型时）。

        这是一个基本的状态机实现，用于演示和测试。
        """
        state = self.context.state
        step = self.context.current_step

        if step == 1:
            # 第一步：分析任务
            return {
                "thinking": "收到用户任务，先分析任务类型和关键信息",
                "action": 'schedule_do(action="AnalyzeTask", analysis={"task_type": "general"})',
            }
        elif state == TaskState.RECEIVING_INPUT:
            # 分析完成后，检查是否需要更多信息
            return {
                "thinking": "任务分析完成，检查是否需要补充信息",
                "action": 'schedule_do(action="UpdateState", state="PLANNING")',
            }
        elif state == TaskState.PLANNING:
            # 生成计划
            return {
                "thinking": "生成执行计划",
                "action": 'schedule_do(action="GeneratePlan", plan={"steps": ["准备", "执行", "完成"]})',
            }
        elif state == TaskState.EXECUTING:
            # 执行任务
            return {
                "thinking": "任务执行中，检查是否完成",
                "action": 'schedule_finish(message="任务已完成")',
            }
        else:
            # 默认：展示信息并完成
            return {
                "thinking": "当前状态无法继续，结束任务",
                "action": 'schedule_finish(message="任务流程结束")',
            }

    def _receive_user_input(self) -> str:
        """接收用户输入。"""
        if self.config.enable_voice_input and self.user_input.is_voice_available():
            # 语音输入逻辑
            pass

        # 文本输入
        return self.user_input.get_input("\n💬 请输入任务描述")

    def _run_onboarding(self) -> None:
        """运行首次引导流程。"""
        self.user_interaction.show_message("=== 首次使用引导 ===", InteractionType.INFO)

        # 能力说明
        self.user_interaction.show_message(
            """
本系统可以帮助您自动完成各种任务：
- ✅ 任务规划和分解
- ✅ 智能调度和执行
- ✅ 风险控制和确认
- ⚠️ 敏感操作需要您的确认
            """,
            InteractionType.INFO,
        )

        # 设备检查
        if self.device_capability:
            devices = self.device_capability.list_available_devices()
            if devices:
                self.user_interaction.show_message(
                    f"✓ 检测到 {len(devices)} 个设备", InteractionType.SUCCESS
                )
            else:
                self.user_interaction.show_message(
                    "⚠ 未检测到设备，部分功能可能不可用", InteractionType.WARNING
                )

        # 偏好设置
        if self.profile_manager:
            auto_update = self.user_interaction.get_confirmation(
                "是否允许系统记住您的偏好？", default=False
            )
            self.config.auto_update_profile = auto_update

        self.user_interaction.show_message(
            "引导完成！现在可以开始使用了。", InteractionType.SUCCESS
        )

    def reset(self) -> None:
        """重置Agent状态。"""
        if self.context:
            self.context.reset_for_new_task()

    @property
    def current_context(self) -> Optional[TaskContext]:
        """获取当前上下文。"""
        return self.context
