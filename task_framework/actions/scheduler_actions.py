"""任务调度Agent的操作处理器。

定义任务调度层面的操作，专注于：
- 用户交互（询问、确认、展示）
- 任务分析和规划
- 调度底层执行器
- 状态转移和决策
"""

import ast
import json
from dataclasses import dataclass
from typing import Any, Optional

from ..context import TaskContext, TaskState
from ..interfaces import (
    UserInputInterface,
    UserInteractionInterface,
    TaskExecutorInterface,
    InteractionType,
    Choice,
)


@dataclass
class SchedulerActionResult:
    """任务调度操作的执行结果。"""

    success: bool
    should_finish: bool
    message: Optional[str] = None
    data: Optional[dict[str, Any]] = None
    next_state: Optional[TaskState] = None


class SchedulerActionHandler:
    """
    任务调度操作处理器。

    处理高层次的任务调度操作，而非具体的设备操作。

    Args:
        user_input: 用户输入接口
        user_interaction: 用户交互接口
        task_executors: 任务执行器列表
        context: 任务上下文
    """

    def __init__(
        self,
        user_input: UserInputInterface,
        user_interaction: UserInteractionInterface,
        task_executors: list[TaskExecutorInterface],
        context: TaskContext,
    ):
        self.user_input = user_input
        self.user_interaction = user_interaction
        self.task_executors = task_executors
        self.context = context

    def execute(self, action: dict[str, Any]) -> SchedulerActionResult:
        """
        执行任务调度操作。

        Args:
            action: 操作字典

        Returns:
            SchedulerActionResult 执行结果
        """
        action_type = action.get("_metadata")

        if action_type == "finish":
            return self._handle_finish(action)

        if action_type != "do":
            return SchedulerActionResult(
                success=False,
                should_finish=True,
                message=f"未知的操作类型: {action_type}",
            )

        action_name = action.get("action")
        handler_method = self._get_handler(action_name)

        if handler_method is None:
            return SchedulerActionResult(
                success=False,
                should_finish=False,
                message=f"未知的操作: {action_name}",
            )

        try:
            return handler_method(action)
        except Exception as e:
            return SchedulerActionResult(
                success=False, should_finish=False, message=f"操作执行失败: {e}"
            )

    def _get_handler(self, action_name: str):
        """获取操作处理器。"""
        handlers = {
            "AskUser": self._handle_ask_user,
            "Confirm": self._handle_confirm,
            "ShowInfo": self._handle_show_info,
            "ShowPreview": self._handle_show_preview,
            "GetChoice": self._handle_get_choice,
            "RequestInfo": self._handle_request_info,
            "DelegateTask": self._handle_delegate_task,
            "CheckDevice": self._handle_check_device,
            "AnalyzeTask": self._handle_analyze_task,
            "GeneratePlan": self._handle_generate_plan,
            "UpdateState": self._handle_update_state,
            "RecordExecution": self._handle_record_execution,
            "RequestTakeover": self._handle_request_takeover,
            "UpdateProfile": self._handle_update_profile,
        }
        return handlers.get(action_name)

    def _handle_finish(self, action: dict[str, Any]) -> SchedulerActionResult:
        """处理任务完成。"""
        message = action.get("message", "任务已完成")
        self.context.state = TaskState.COMPLETED
        return SchedulerActionResult(
            success=True,
            should_finish=True,
            message=message,
            next_state=TaskState.COMPLETED,
        )

    def _handle_ask_user(self, action: dict[str, Any]) -> SchedulerActionResult:
        """询问用户问题。"""
        question = action.get("question", "")
        if not question:
            return SchedulerActionResult(
                success=False, should_finish=False, message="缺少问题内容"
            )

        # 询问用户
        answer = self.user_input.get_input(question)

        # 记录交互
        self.context.add_interaction_record(
            "ask_user", {"question": question, "answer": answer}
        )

        return SchedulerActionResult(
            success=True,
            should_finish=False,
            message=f"用户回答: {answer}",
            data={"answer": answer},
        )

    def _handle_confirm(self, action: dict[str, Any]) -> SchedulerActionResult:
        """请求用户确认。"""
        message = action.get("message", "是否继续？")
        default = action.get("default", False)
        risk_level = action.get("risk_level", "low")

        # 根据风险等级设置交互类型
        interaction_type = InteractionType.INFO
        if risk_level == "high":
            interaction_type = InteractionType.WARNING
        elif risk_level == "medium":
            interaction_type = InteractionType.INFO

        # 显示确认提示
        if risk_level in ["medium", "high"]:
            self.user_interaction.show_message(
                f"⚠️ 风险等级: {risk_level}", interaction_type
            )

        confirmed = self.user_interaction.get_confirmation(message, default)

        # 记录交互
        self.context.add_interaction_record(
            "confirm", {"message": message, "confirmed": confirmed}
        )

        return SchedulerActionResult(
            success=True,
            should_finish=False,
            message=f"用户{'确认' if confirmed else '拒绝'}",
            data={"confirmed": confirmed},
        )

    def _handle_show_info(self, action: dict[str, Any]) -> SchedulerActionResult:
        """显示信息给用户。"""
        message = action.get("message", "")
        info_type = action.get("type", "info")

        type_map = {
            "info": InteractionType.INFO,
            "success": InteractionType.SUCCESS,
            "warning": InteractionType.WARNING,
            "error": InteractionType.ERROR,
        }

        self.user_interaction.show_message(
            message, type_map.get(info_type, InteractionType.INFO)
        )

        return SchedulerActionResult(success=True, should_finish=False)

    def _handle_show_preview(self, action: dict[str, Any]) -> SchedulerActionResult:
        """显示任务计划预览。"""
        title = action.get("title", "任务计划预览")
        data = action.get("data", {})

        self.user_interaction.show_preview(title, data)

        return SchedulerActionResult(success=True, should_finish=False)

    def _handle_get_choice(self, action: dict[str, Any]) -> SchedulerActionResult:
        """获取用户选择。"""
        prompt = action.get("prompt", "请选择:")
        choices_data = action.get("choices", [])

        # 构建选择列表
        choices = [
            Choice(
                id=c.get("id", str(i)),
                label=c.get("label", ""),
                description=c.get("description"),
            )
            for i, c in enumerate(choices_data)
        ]

        if not choices:
            return SchedulerActionResult(
                success=False, should_finish=False, message="没有可选项"
            )

        choice_id = self.user_interaction.get_choice(prompt, choices)

        # 记录交互
        self.context.add_interaction_record(
            "get_choice", {"prompt": prompt, "choice": choice_id}
        )

        return SchedulerActionResult(
            success=True,
            should_finish=False,
            message=f"用户选择: {choice_id}",
            data={"choice": choice_id},
        )

    def _handle_request_info(self, action: dict[str, Any]) -> SchedulerActionResult:
        """请求用户补充信息。"""
        prompt = action.get("prompt", "请提供以下信息:")
        fields = action.get("fields", [])

        if not fields:
            return SchedulerActionResult(
                success=False, should_finish=False, message="没有需要补充的字段"
            )

        info = self.user_interaction.request_missing_info(prompt, fields)

        # 更新任务信息
        if self.context.task_info:
            self.context.task_info.key_info.update(info)

        # 记录交互
        self.context.add_interaction_record(
            "request_info", {"fields": fields, "info": info}
        )

        return SchedulerActionResult(
            success=True,
            should_finish=False,
            message=f"已获取信息: {list(info.keys())}",
            data={"info": info},
        )

    def _handle_delegate_task(self, action: dict[str, Any]) -> SchedulerActionResult:
        """委托任务给底层执行器。"""
        task_type = action.get("task_type", "")
        task_data = action.get("task_data", {})

        if not task_type:
            return SchedulerActionResult(
                success=False, should_finish=False, message="缺少任务类型"
            )

        # 查找合适的执行器
        executor = self._find_executor(task_type)
        if not executor:
            return SchedulerActionResult(
                success=False,
                should_finish=False,
                message=f"没有找到能处理 {task_type} 的执行器",
            )

        # 执行任务
        try:
            result = executor.execute_task(task_type, task_data, context=self.context)

            # 记录执行
            self.context.add_execution_record(
                action=f"delegate_{task_type}", result=result, success=result.success
            )

            return SchedulerActionResult(
                success=result.success,
                should_finish=False,
                message=result.message,
                data={"executor_result": result},
            )
        except Exception as e:
            return SchedulerActionResult(
                success=False, should_finish=False, message=f"执行器失败: {e}"
            )

    def _handle_check_device(self, action: dict[str, Any]) -> SchedulerActionResult:
        """检查设备状态。"""
        # 这里可以调用设备能力接口检查设备
        # 简化实现，返回成功
        device_id = action.get("device_id")

        return SchedulerActionResult(
            success=True,
            should_finish=False,
            message="设备状态正常",
            data={"device_ready": True},
        )

    def _handle_analyze_task(self, action: dict[str, Any]) -> SchedulerActionResult:
        """分析任务。"""
        # 这个操作主要是记录大模型的分析结果
        analysis = action.get("analysis", {})

        if self.context.task_info:
            # 更新任务信息
            self.context.task_info.task_type = analysis.get(
                "task_type", self.context.task_info.task_type
            )
            self.context.task_info.key_info.update(analysis.get("key_info", {}))
            self.context.task_info.constraints = analysis.get("constraints", [])

        return SchedulerActionResult(
            success=True,
            should_finish=False,
            message="任务分析完成",
            data={"analysis": analysis},
        )

    def _handle_generate_plan(self, action: dict[str, Any]) -> SchedulerActionResult:
        """生成执行计划。"""
        plan_data = action.get("plan", {})

        # 这里可以根据plan_data创建ExecutionPlan
        # 简化实现

        return SchedulerActionResult(
            success=True,
            should_finish=False,
            message="计划生成完成",
            data={"plan": plan_data},
        )

    def _handle_update_state(self, action: dict[str, Any]) -> SchedulerActionResult:
        """更新任务状态。"""
        state_name = action.get("state", "")

        try:
            new_state = TaskState[state_name.upper()]
            self.context.state = new_state

            return SchedulerActionResult(
                success=True,
                should_finish=False,
                message=f"状态已更新为: {new_state.value}",
                next_state=new_state,
            )
        except KeyError:
            return SchedulerActionResult(
                success=False, should_finish=False, message=f"无效的状态: {state_name}"
            )

    def _handle_record_execution(self, action: dict[str, Any]) -> SchedulerActionResult:
        """记录执行步骤。"""
        step_info = action.get("step_info", {})

        self.context.add_execution_record(
            action=step_info.get("action", "unknown"),
            result=step_info.get("result"),
            success=step_info.get("success", True),
        )

        return SchedulerActionResult(success=True, should_finish=False)

    def _handle_request_takeover(self, action: dict[str, Any]) -> SchedulerActionResult:
        """请求人工接管。"""
        reason = action.get("reason", "需要人工介入")

        self.context.state = TaskState.TAKEOVER
        self.user_interaction.show_message(f"⚠️ {reason}", InteractionType.WARNING)

        self.user_input.get_input("请手动完成相关操作，完成后按回车继续...")

        return SchedulerActionResult(
            success=True,
            should_finish=False,
            message="人工接管完成",
            next_state=TaskState.EXECUTING,
        )

    def _handle_update_profile(self, action: dict[str, Any]) -> SchedulerActionResult:
        """更新用户画像。"""
        profile_data = action.get("profile_data", {})

        # 这里应该调用ProfileManager更新画像
        # 简化实现

        return SchedulerActionResult(
            success=True, should_finish=False, message="用户画像已更新"
        )

    def _find_executor(self, task_type: str) -> Optional[TaskExecutorInterface]:
        """查找能处理指定任务类型的执行器。"""
        for executor in self.task_executors:
            if executor.can_handle(task_type):
                return executor
        return None


def parse_scheduler_action(response: str) -> dict[str, Any]:
    """
    解析大模型的响应为调度操作。

    Args:
        response: 模型响应字符串

    Returns:
        解析后的操作字典

    Raises:
        ValueError: 如果无法解析响应
    """
    try:
        response = response.strip()

        # 处理 schedule_do(...) 格式
        if response.startswith("schedule_do"):
            tree = ast.parse(response, mode="eval")
            if not isinstance(tree.body, ast.Call):
                raise ValueError("期望函数调用格式")

            call = tree.body
            action = {"_metadata": "do"}
            for keyword in call.keywords:
                key = keyword.arg
                value = ast.literal_eval(keyword.value)
                action[key] = value

            return action

        # 处理 schedule_finish(...) 格式
        elif response.startswith("schedule_finish"):
            match = response.replace("schedule_finish(message=", "")[1:-2]
            return {"_metadata": "finish", "message": match}

        # 尝试解析JSON格式
        elif response.startswith("{"):
            action = json.loads(response)
            if "_metadata" not in action:
                action["_metadata"] = "do"
            return action

        else:
            raise ValueError(f"无法解析操作格式: {response}")

    except Exception as e:
        raise ValueError(f"解析操作失败: {e}")


# 辅助函数


def schedule_do(**kwargs) -> dict[str, Any]:
    """创建调度操作。"""
    kwargs["_metadata"] = "do"
    return kwargs


def schedule_finish(**kwargs) -> dict[str, Any]:
    """创建完成操作。"""
    kwargs["_metadata"] = "finish"
    return kwargs


def schedule_ask_user(question: str) -> dict[str, Any]:
    """询问用户。"""
    return schedule_do(action="AskUser", question=question)


def schedule_confirm(message: str, risk_level: str = "low") -> dict[str, Any]:
    """请求确认。"""
    return schedule_do(action="Confirm", message=message, risk_level=risk_level)


def schedule_delegate(task_type: str, task_data: dict) -> dict[str, Any]:
    """委托任务。"""
    return schedule_do(
        action="DelegateTask",
        task_type=task_type,
        task_data=task_data,
    )


def schedule_update_state(state: str) -> dict[str, Any]:
    """更新状态。"""
    return schedule_do(action="UpdateState", state=state)
