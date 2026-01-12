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
from .system_prompts import get_scheduler_system_prompt, get_messages
from openai import OpenAI
from openai.types.chat.chat_completion import ChatCompletion
from .interfaces import (
    UserInputInterface,
    UserInteractionInterface,
    DeviceCapabilityInterface,
    ProfileManagerInterface,
    TaskExecutorInterface,
    InteractionType,
)

# 如果有model client，可以导入


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
        model_client: Optional[Any] = None,  # OpenAI client
        config: Optional[TaskAgentConfig] = None,
    ):
        self.user_input = user_input
        self.user_interaction = user_interaction
        self.device_capability = device_capability
        self.profile_manager = profile_manager
        self.task_executors = task_executors or []
        self.config = config or TaskAgentConfig()

        # 只在提供了配置时创建 model_client
        if model_client is not None:
            self.model_client: OpenAI = model_client
        elif self.config.model_base_url and self.config.model_api_key:
            self.model_client: OpenAI = OpenAI(
                base_url=self.config.model_base_url,
                api_key=self.config.model_api_key,
            )
            print(
                f"base_url:{self.config.model_base_url}",
            )
            print(f"api_key:{self.config.model_api_key}")
            print(f"model_name:{self.config.model_name}")

        else:
            raise ValueError("model_client is not set")

        # 初始化上下文
        self.context: Optional[TaskContext] = None

        # 初始化操作处理器
        self.action_handler: Optional[SchedulerActionHandler] = None

        # 引导状态
        self._is_onboarded = not self.config.enable_onboarding

        # 构建系统提示词（包含执行器能力）
        self.system_prompt = self._build_system_prompt()

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
                    profile_manager=self.profile_manager,
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

    def _build_system_prompt(self) -> str:
        """构建系统提示词，包含执行器能力信息。"""
        # 获取基础提示词
        if self.config.system_prompt:
            base_prompt = self.config.system_prompt
        else:
            base_prompt = get_scheduler_system_prompt(self.config.language)

        # 如果没有执行器，返回基础提示词
        if not self.task_executors:
            return base_prompt

        # 构建执行器能力说明
        executors_section = self._build_executors_capability_section()

        # 组合提示词
        return f"""{base_prompt}

{executors_section}
"""

    def _build_executors_capability_section(self) -> str:
        """构建执行器能力说明部分，供系统提示词使用。"""
        lines = [
            "## 可用执行器",
            "使用 DelegateTask 时需指定 task_type 和 task_data 参数。",
            "",
        ]

        for executor in self.task_executors:
            capabilities = executor.get_capabilities()

            for cap in capabilities:
                # 简化格式：task_type: 名称 - 描述
                lines.append(f"- {cap.task_type}: {cap.name} - {cap.description}")

                # 简化参数说明（单行，仅显示参数名和必需性）
                if cap.parameters:
                    required_params = [p.name for p in cap.parameters if p.required]
                    optional_params = [p.name for p in cap.parameters if not p.required]

                    param_info = []
                    if required_params:
                        param_info.append(f"必需: {', '.join(required_params)}")
                    if optional_params:
                        param_info.append(f"可选: {', '.join(optional_params)}")

                    if param_info:
                        lines.append(f"  参数: {'; '.join(param_info)}")

                # 仅保留一个示例（最简单的那个）
                if cap.examples:
                    first_example = cap.examples[0]
                    task_data_str = json.dumps(
                        first_example.get("task_data", {}),
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    lines.append(
                        f'  示例: schedule_do(action="DelegateTask", task_type="{cap.task_type}", task_data={task_data_str})'
                    )

                # 添加限制说明
                if cap.limitations:
                    lines.append(f"  限制: {'; '.join(cap.limitations)}")

        return "\n".join(lines)

    def _perceive_current_state(self) -> str:
        """
        感知当前任务状态。

        收集：
        - 当前状态
        - 任务信息
        - 执行历史
        - 交互历史
        - 可用执行器状态
        - 其他上下文信息

        Returns:
            格式化的状态信息字符串
        """
        context_summary = self.context.get_context_summary()

        # 获取执行器状态摘要（简化版，用于每步感知）
        executors_status = self._get_executors_status_summary()

        # 简化状态感知信息
        task_info = context_summary["task_info"]
        perception_parts = [
            f"状态: {context_summary['current_state']} | 步骤: {context_summary['current_step']}",
            f"{executors_status}",
        ]

        # 仅在有任务信息时显示
        if task_info:
            task_input = task_info.get("original_input", "无")
            task_type = task_info.get("task_type", "未确定")
            perception_parts.append(f"任务: {task_input} (类型: {task_type})")

        # 仅在有执行历史时显示
        if (
            context_summary["recent_execution"]
            and context_summary["recent_execution"] != "暂无执行历史"
        ):
            perception_parts.append(f"历史: {context_summary['recent_execution']}")

        # 仅在有上次结果时显示
        if context_summary["last_action_result"]:
            perception_parts.append(
                f"上次结果: {context_summary['last_action_result']}"
            )

        return "\n".join(perception_parts)

    def _get_executors_status_summary(self) -> str:
        """获取执行器状态摘要（简化版，用于每步感知）。"""
        if not self.task_executors:
            return "可用执行器: 无"

        # 收集所有能力的 task_type
        all_task_types = []
        for executor in self.task_executors:
            caps = executor.get_capabilities()
            all_task_types.extend([cap.task_type for cap in caps])

        return f"可用执行器: {', '.join(all_task_types)}"

    def _request_model_decision(self) -> dict[str, str]:
        """
        请求大模型做决策。

        Returns:
            包含 'thinking' 和 'action' 的字典
        """
        if self.model_client is None:
            # 如果没有模型客户端，使用简化的决策逻辑
            return self._fallback_decision()

        # print("conversation_history:", self.context.conversation_history)
        # 使用已构建的对话历史进行决策
        response = self.model_client.chat.completions.create(
            messages=self.context.conversation_history,
            model=self.config.model_name,
            max_completion_tokens=2048,
            temperature=0.3,
            top_p=0.95,
            stream=False,
            stop=None,
            frequency_penalty=0,
            presence_penalty=0,
        )

        # 解析 OpenAI 格式的响应
        # 响应格式: response.choices[0].message.content

        # 解析 <think>...</think> 和 <answer>...</answer> 标签
        return self._parse_model_response(response.choices[0].message)

    def _parse_model_response(self, message) -> dict[str, str]:
        """解析模型响应文本。"""
        import re

        content = message.content
        # 首先获取action
        answer_match = re.search(r"<answer>(.*?)</answer>", content, re.DOTALL)
        action = answer_match.group(1).strip() if answer_match else message.content
        # 然后获取reasoning_content
        reasoning_content = message.reasoning_content

        # 首先尝试直接获取reasoning_content
        if reasoning_content:
            thinking = reasoning_content
        else:
            # 尝试提取 <think>...</think> 和 <answer>...</answer>
            think_match = re.search(r"<think>(.*?)</think>", content, re.DOTALL)

            thinking = think_match.group(1).strip() if think_match else ""

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
        return self.user_input.get_input("\n请输入任务描述")

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